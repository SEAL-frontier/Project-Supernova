"""Explicit local capabilities, scoped to the filesystem actually visible to this process.

This adapter never reaches through a container boundary or exposes a general local shell.
Process actions are operator-registered argv lists, executed without a shell.
"""

from __future__ import annotations

import ctypes
import hashlib
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import platform
import shutil
import stat
import subprocess
import tempfile
import time
import uuid

from ..v2.tools import emit_progress


class LocalAccess:
    def __init__(self, config):
        self.config = dict(config)
        raw = self.config.get("root", "")
        if not raw or not Path(raw).is_absolute():
            raise ValueError("Local root must be an explicit absolute path visible inside the bot")
        self.root = Path(raw).resolve()
        self.writable = self.config.get("writable", False) is True
        self.process = self.config.get("process", {})

    def path(self, relative):
        raw = str(relative)
        # A Windows drive/UNC path is unsafe even when the bot happens to run on Linux.
        if (
            not raw
            or PureWindowsPath(raw).drive
            or PureWindowsPath(raw).is_absolute()
            or PurePosixPath(raw).is_absolute()
            or ".." in raw.replace("\\", "/").split("/")
        ):
            raise ValueError("Path must stay inside the selected local server")
        target = self.root.joinpath(*raw.replace("\\", "/").split("/")).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError("Symlink or path escapes the selected local server")
        return target

    def detect(self):
        readable = self.root.is_dir() and os.access(self.root, os.R_OK | os.X_OK)
        writable = readable and self.writable and os.access(self.root, os.W_OK | os.X_OK)
        actions = self.process.get("actions", {})
        registered = [
            k
            for k, v in actions.items()
            if k in ("start", "stop", "restart", "kill")
            and isinstance(v, list)
            and v
            and all(isinstance(a, str) and a for a in v)
        ]
        return {
            "os": platform.system(),
            "root_visible": readable,
            "files_readable": readable,
            "files_writable": writable,
            "write_enabled": self.writable,
            "registered_actions": registered,
            "process_probe_configured": bool(
                self.process.get("pid_file") and self.process.get("identity")
            ),
            "container_detected": Path("/.dockerenv").exists()
            or Path("/run/.containerenv").exists(),
            "scope": "Only paths and processes visible with the bot's current OS permissions",
        }

    def capabilities(self):
        state = self.detect()
        caps = {"status"}
        if state["root_visible"]:
            caps.update(("files", "logs", "plugins", "host"))
        if state["files_writable"]:
            caps.add("plugin_install")
        if state["process_probe_configured"] and state["registered_actions"]:
            caps.add("power")
        return caps

    def _write_allowed(self):
        if not self.detect()["files_writable"]:
            raise PermissionError(
                "Local connection is read-only or the bot cannot write this directory"
            )

    def binary(self, relative, cap=64 * 1024 * 1024):
        path = self.path(relative)
        with path.open("rb") as f:
            raw = f.read(cap + 1)
        if len(raw) > cap:
            raise ValueError("File exceeds analysis limit")
        return raw

    def _backup(self, path):
        if not path.exists():
            return None
        if not path.is_file():
            raise ValueError("Only regular server files may be changed")
        relative = path.relative_to(self.root)
        backup = self.path(
            ".kei-backups/"
            + str(time.time_ns())
            + "-"
            + uuid.uuid4().hex[:6]
            + "/"
            + relative.as_posix()
        )
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)
        return backup.relative_to(self.root).as_posix()

    def write_binary(self, relative, raw):
        self._write_allowed()
        if len(raw) > 64 * 1024 * 1024:
            raise ValueError("Write exceeds 64 MiB")
        path = self.path(relative)
        backup = self._backup(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix=".kei-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(raw)
                f.flush()
                os.fsync(f.fileno())
            if path.exists():
                os.chmod(temp, stat.S_IMODE(path.stat().st_mode))
            # Re-resolve after backup/temp creation to catch changed parent symlinks.
            if self.path(relative) != path:
                raise ValueError("Server path changed during write; reconcile before retry")
            os.replace(temp, path)
            digest = hashlib.sha256(raw).hexdigest()
            return {
                "verified": hashlib.sha256(self.binary(relative)).hexdigest() == digest,
                "sha256": digest,
                "backup_path": backup,
                "scope": "local file readback",
            }
        finally:
            if os.path.exists(temp):
                os.unlink(temp)

    def files(self, action, relative, content=None, backup_path=None):
        emit_progress("command", "Local files " + action + " " + relative)
        path = self.path(relative)
        if action == "list":
            return {"verified": True, "stdout": "\n".join(sorted(p.name for p in path.iterdir()))}
        if action == "read":
            with path.open("rb") as f:
                raw = f.read(100001)
            return {
                "verified": True,
                "stdout": raw[:100000].decode("utf-8", "replace"),
                "truncated": len(raw) > 100000,
            }
        if action == "restore":
            if not backup_path or not str(backup_path).replace("\\", "/").startswith(
                ".kei-backups/"
            ):
                raise ValueError("Select an existing Kei backup")
            result = self.write_binary(relative, self.binary(backup_path))
            return {**result, "restored_from": backup_path}
        if action == "write":
            if content is None:
                raise ValueError("Write needs content")
            return self.write_binary(relative, content.encode("utf-8"))
        if action == "remove":
            self._write_allowed()
            if not path.is_file():
                raise ValueError("File not found or not a regular file")
            backup = self._backup(path)
            path.unlink()
            return {
                "verified": not path.exists(),
                "backup_path": backup,
                "scope": "local file absence",
            }
        raise ValueError("Unsupported local file action")

    def logs(self, lines=100):
        path = self.path("logs/latest.log")
        with path.open("rb") as f:
            f.seek(max(0, path.stat().st_size - 120000))
            text = f.read(120000).decode("utf-8", "replace")
        return {
            "verified": True,
            "stdout": "\n".join(text.splitlines()[-max(1, min(int(lines), 400)) :]),
        }

    def process_state(self):
        if not self.process.get("pid_file") or not self.process.get("identity"):
            return {"state": "unknown", "verified": False, "reason": "No registered process probe"}
        try:
            pid = int(self.path(self.process["pid_file"]).read_text().strip())
            if pid < 1:
                raise ValueError("invalid PID")
        except (OSError, ValueError):
            return {
                "state": "offline",
                "verified": True,
                "scope": "registered PID file absent/invalid",
            }
        identity = str(self.process["identity"])
        try:
            if os.name == "nt":
                kernel = ctypes.WinDLL("kernel32", use_last_error=True)
                kernel.OpenProcess.restype = ctypes.c_void_p
                handle = kernel.OpenProcess(0x1000, False, pid)
                if not handle:
                    error = ctypes.get_last_error()
                    if error == 87:
                        return {"state": "offline", "verified": True, "pid": pid}
                    return {
                        "state": "unknown",
                        "verified": False,
                        "reason": "Process not accessible",
                    }
                try:
                    size = ctypes.c_ulong(32768)
                    name = ctypes.create_unicode_buffer(size.value)
                    if not kernel.QueryFullProcessImageNameW(
                        ctypes.c_void_p(handle), 0, name, ctypes.byref(size)
                    ):
                        raise OSError("Cannot inspect registered process")
                    command = name.value
                finally:
                    kernel.CloseHandle(ctypes.c_void_p(handle))
            elif Path("/proc").is_dir():
                command = (
                    Path("/proc", str(pid), "cmdline")
                    .read_bytes()
                    .replace(b"\0", b" ")
                    .decode("utf-8", "replace")
                )
            else:
                result = subprocess.run(
                    ["ps", "-p", str(pid), "-o", "command="],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                command = result.stdout.strip()
            if not command:
                return {"state": "offline", "verified": True, "pid": pid}
            if identity.casefold() not in command.casefold():
                return {
                    "state": "unknown",
                    "verified": False,
                    "pid": pid,
                    "reason": "PID identity mismatch; no action taken",
                }
            return {
                "state": "running",
                "verified": True,
                "pid": pid,
                "scope": "registered process identity; this does not prove Minecraft readiness",
            }
        except FileNotFoundError:
            return {"state": "offline", "verified": True, "pid": pid}
        except (OSError, subprocess.SubprocessError):
            return {
                "state": "unknown",
                "verified": False,
                "pid": pid,
                "reason": "Process permission/namespace boundary",
            }

    def inspect(self, kind, lines=100):
        if kind == "logs":
            return self.logs(lines)
        if kind == "plugins":
            root = self.path("plugins")
            names = sorted(p.name for p in root.glob("*.jar")) if root.is_dir() else []
            return {
                "verified": True,
                "stdout": "\n".join(names),
                "note": "JAR files visible; enablement requires bridge/console evidence",
            }
        if kind == "host":
            usage = shutil.disk_usage(self.root)
            return {
                "verified": True,
                "data": {"disk_bytes": usage._asdict(), "capabilities": self.detect()},
                "scope": "Visible filesystem; no inference about another container/host's RAM",
            }
        if kind == "status":
            state = self.process_state()
            return {"verified": state.pop("verified"), "data": {**state, "local": self.detect()}}
        raise ValueError("Local files alone cannot read live TPS/players; add Panel or bridge")

    def power(self, action):
        state = self.process_state()
        if state["state"] == "unknown":
            raise PermissionError(
                "Registered process cannot be identified; use bridge/Panel or repair local setup"
            )
        args = self.process.get("actions", {}).get(action)
        if (
            not isinstance(args, list)
            or not args
            or not all(isinstance(a, str) and a for a in args)
        ):
            raise PermissionError("This process action has not been registered by the operator")
        # Never report a stale startup line as evidence of this start/restart.
        log = self.path("logs/latest.log")
        before = (log.stat().st_ino, log.stat().st_size) if log.exists() else None
        emit_progress("command", "Local registered process action: " + action)
        try:
            result = subprocess.run(
                args,
                cwd=self.root,
                shell=False,
                capture_output=True,
                timeout=min(180, int(self.process.get("action_timeout", 30))),
            )
        except subprocess.TimeoutExpired:
            return {
                "accepted": True,
                "verified": False,
                "note": "Registered action timed out; inspect state before retrying",
            }
        if result.returncode:
            return {
                "verified": False,
                "exit_code": result.returncode,
                "stderr": result.stderr.decode("utf-8", "replace")[-3000:],
            }
        deadline = time.monotonic() + min(180, int(self.process.get("ready_timeout", 30)))
        while time.monotonic() < deadline:
            after = self.process_state()
            good = after["verified"] and after["state"] == (
                "offline" if action in ("stop", "kill") else "running"
            )
            if good and action in ("start", "restart"):
                current = (log.stat().st_ino, log.stat().st_size) if log.exists() else None
                fresh = ""
                if current:
                    offset = (
                        before[1]
                        if before and current[0] == before[0] and current[1] >= before[1]
                        else 0
                    )
                    with log.open("rb") as f:
                        f.seek(max(offset, current[1] - 120000))
                        fresh = f.read(120000).decode("utf-8", "replace")
                good = "Done (" in fresh
            if good:
                return {
                    "verified": True,
                    "state": after["state"],
                    "verification": {
                        "kind": "local_process_readback",
                        "scope": (
                            "registered PID and fresh startup log"
                            if action in ("start", "restart")
                            else "registered PID absent"
                        ),
                    },
                }
            time.sleep(0.25)
        return {
            "accepted": True,
            "verified": False,
            "note": "Action dispatched; expected process/readiness state not observed",
        }
