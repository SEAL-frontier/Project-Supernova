from __future__ import annotations
import base64, hashlib, io, json, os, pathlib, re, shlex, time, zipfile
import httpx, paramiko, yaml
from ..v2.tools import ServerTools, effect_of, emit_progress, console_read
from ..v2.verification import console_receipt
from .config import normalize_profile
from .panel import Panel
from .local import LocalAccess


def diagnostic_receipt(command, output):
    """Recognize a complete fresh TPS report, without treating arbitrary logs as success."""
    if command.strip().lstrip("/").casefold() not in ("spark tps", "tps"):
        return None
    text = re.sub(r"§[0-9a-fk-or]|\x1b\[[0-9;]*m", "", output, flags=re.I)
    lines = [
        re.sub(r"\[[^\]\n]*\]\s*", "", line).strip().lstrip(": ") for line in text.splitlines()
    ]
    for index, line in enumerate(lines):
        if not re.search(r"\bTPS (?:from )?last\b", line, re.I) or ":" not in line:
            continue
        values_line = line.rsplit(":", 1)[-1].strip()
        if not values_line and index + 1 < len(lines):
            values_line = lines[index + 1]
        values = [float(v) for v in re.findall(r"\d+(?:\.\d+)?", values_line)]
        if not 3 <= len(values) <= 6 or not all(0 <= v <= 20.1 for v in values):
            continue
        data = {
            "tps": values,
            "scope": "Fresh server-reported TPS samples, not continuous monitoring",
        }
        for pos, item in enumerate(lines):
            if item.startswith("Tick durations") and pos + 1 < len(lines):
                series = []
                for group in lines[pos + 1].split(";"):
                    numbers = [float(v) for v in re.findall(r"\d+(?:\.\d+)?", group)]
                    if len(numbers) == 4:
                        series.append(
                            dict(zip(("min_ms", "median_ms", "p95_ms", "max_ms"), numbers))
                        )
                if series:
                    data["tick_durations"] = series
        return {
            "kind": "console_diagnostic_readback",
            "scope": "Fresh complete TPS report",
            "data": data,
        }
    return None


class HybridTools(ServerTools):
    """One capability registry; existing typed tools never choose random transports."""

    def __init__(self, profile, secrets, bridge=None):
        self.p = normalize_profile(profile)
        self.cs = self.p["connectors"]
        self.secret_store = secrets
        self.bridge = bridge
        ssh = self.cs.get("ssh", {})
        for source, target in [
            ("host", "host"),
            ("user", "ssh_user"),
            ("volume", "volume"),
            ("file_owner", "file_owner"),
            ("known_hosts", "known_hosts"),
        ]:
            if ssh.get(source):
                self.p[target] = ssh[source]
        self.p.setdefault("minecraft_version", "unknown")
        self.secrets = [
            v
            for c in self.cs.values()
            for k, v in (
                (key, secrets.get(val))
                for key, val in c.items()
                if key in ("token", "password", "key_password", "root_password")
            )
            if v
        ]
        self.panel = Panel(self.cs["panel"], secrets) if "panel" in self.cs else None
        self.local = LocalAccess(self.cs["local"]) if self.cs.get("local") else None

    def connected_bridge(self, cap=None):
        return bool(
            self.bridge
            and self.bridge.online(self.p["id"])
            and (not cap or cap in self.bridge.capabilities(self.p["id"]))
        )

    def capabilities(self):
        caps = {"plugin_search", "fetch_url", "web_search"}
        if self.cs.get("panel") or self.cs.get("wings"):
            caps.update(("status", "console", "power"))
        if self.cs.get("panel"):
            caps.update(("files", "plugins", "plugin_install", "profiler", "logs"))
        if self.cs.get("ssh"):
            caps.update(("host", "remote_shell"))
        if self.cs.get("ssh", {}).get("volume"):
            caps.update(("files", "plugins", "plugin_install", "logs", "profiler"))
            if self.p.get("uuid"):
                caps.update(("console", "power"))
        if self.connected_bridge():
            caps.update(self.bridge.capabilities(self.p["id"]))
        if self.local:
            caps.update(self.local.capabilities())
        if "console" in caps:
            caps.update(("players", "tps", "health", "profiler"))
        return sorted(caps)

    def _need(self, cap):
        if cap not in self.capabilities():
            raise ValueError(
                "Server chưa có capability "
                + cap
                + ". Có: "
                + ", ".join(self.capabilities())
                + ". Chạy /server hoặc keys-keys server add để thêm kết nối."
            )

    def execute(self, name, args, mode="change", confirmed=False):
        self._need(args["kind"] if name == "inspect" else name)
        result = super().execute(name, args, mode, confirmed)
        result.update(target=self.p["id"], observed_at=time.time(), tool=name)
        return result

    def client(self):
        p = self.cs.get("ssh")
        if not p:
            raise ValueError("Không có SSH cho server này")
        c = paramiko.SSHClient()
        known = p.get("known_hosts")
        if known:
            c.load_host_keys(known)
        else:
            c.load_system_host_keys()
        c.set_missing_host_key_policy(paramiko.RejectPolicy())
        c.connect(
            p["host"],
            port=int(p.get("port", 22)),
            username=p["user"],
            password=self.secret_store.get(p.get("password")) or None,
            key_filename=p.get("key_file"),
            passphrase=self.secret_store.get(p.get("key_password")) or None,
            allow_agent=bool(p.get("agent", False)),
            look_for_keys=bool(p.get("agent", False)),
            timeout=12,
        )
        return c

    def shell(self, command, timeout=60, sudo=True):
        c = self.client()
        from .execution import prepare_ssh
        try:
            emit_progress("command", "SSH $ " + command)
            command,password,pty=prepare_ssh(self.cs['ssh'],self.secret_store,command,sudo)
            kwargs={'timeout':timeout}
            if pty:kwargs['get_pty']=True
            i,o,e=c.exec_command(command,**kwargs)
            if password:
                i.write(password+'\n');i.flush()
            i.channel.shutdown_write()
            channel = o.channel
            out = bytearray()
            err = bytearray()
            deadline = time.monotonic() + timeout
            while True:
                if channel.recv_ready():
                    chunk = channel.recv(32768)
                    out.extend(chunk)
                    out = out[-100000:]
                    emit_progress("log", chunk.decode("utf-8", "replace"))
                if channel.recv_stderr_ready():
                    err.extend(channel.recv_stderr(32768))
                    err = err[-10000:]
                if (
                    channel.exit_status_ready()
                    and not channel.recv_ready()
                    and not channel.recv_stderr_ready()
                ):
                    break
                if time.monotonic() > deadline:
                    channel.close()
                    raise TimeoutError("SSH outcome may be uncertain; read back before retry")
                time.sleep(0.02)
            return {
                "stdout": out.decode("utf-8", "replace"),
                "stderr": err.decode("utf-8", "replace"),
                "exit_code": channel.recv_exit_status(),
            }
        finally:
            c.close()

    def execute(self,name,args,mode='change',confirmed=False):
        if name=='find_server_files':
            return {'source':name,'server':self.p['name'],'observed_at':time.time(),**self.do_find_server_files(**args)}
        return super().execute(name,args,mode,confirmed)

    def do_find_server_files(self,pattern,limit=20):
        import fnmatch
        if not isinstance(pattern,str) or not 1<=len(pattern)<=180 or '/' in pattern or '\\' in pattern or '\x00' in pattern:raise ValueError('Tìm bằng tên tệp hoặc glob, không phải đường dẫn.')
        limit=max(1,min(100,int(limit)))
        if self.cs.get('ssh',{}).get('volume'):
            root=self.p['volume'];result=self.shell('find '+shlex.quote(root)+' -maxdepth 6 -type f -iname '+shlex.quote(pattern)+' -print | head -n '+str(limit+1))
            if result.get('exit_code') or result.get('stderr'):return {**result,'matches':[],'complete':False}
            matches=[line[len(root.rstrip('/'))+1:] for line in result['stdout'].splitlines() if line.startswith(root.rstrip('/')+'/')]
            return {'matches':matches[:limit],'complete':len(matches)<=limit,'scope':'server volume; maximum depth 6','verified':True}
        if self.panel:
            queue=[('',0)];matches=[];count=0
            while queue and count<80 and len(matches)<=limit:
                path,depth=queue.pop(0);count+=1
                entries=self.panel.server('GET','/files/list',params={'directory':'/'+path}).get('data',[])
                for entry in entries:
                    row=entry.get('attributes',entry);name=row.get('name','');child=(path+'/'+name).strip('/')
                    if not name or '/' in name or name in ('.','..'):continue
                    if row.get('is_file',False):
                        if fnmatch.fnmatchcase(name.casefold(),pattern.casefold()):matches.append(child)
                    elif depth<5:queue.append((child,depth+1))
            return {'matches':matches[:limit],'complete':not queue and len(matches)<=limit,'directories_checked':count,'verified':True}
        return {'matches':[],'complete':False,'error':'No file-search transport available; ask for an uploaded file or an exact path.'}

    def do_remote_shell(self,command,effect,cwd=None):
        if cwd is not None:
            if not isinstance(cwd,str) or not pathlib.PurePosixPath(cwd).is_absolute() or '\x00' in cwd:raise ValueError('Thư mục làm việc cần là đường dẫn tuyệt đối trên host.')
            prefix='cd '+shlex.quote(cwd)+' && '
            directory=cwd
        else:
            directory=self.p.get('volume','/')
            if effect=='read':
                # A host user can inspect its own OS identity without being able to enter
                # a root-owned Minecraft volume. Never silently relocate a mutation.
                prefix='if test -d '+shlex.quote(directory)+' && test -x '+shlex.quote(directory)+'; then cd '+shlex.quote(directory)+' || exit 76; fi; '
            else:prefix='cd '+shlex.quote(directory)+' && '
        return {**self.shell(prefix+command,timeout=180),'working_directory':cwd or ('server volume if accessible, otherwise SSH home (read only)' if effect=='read' else directory)}

    def api(self, method, suffix, body=None):
        if self.panel:
            translated = {"/commands": "/command"}.get(suffix, suffix)
            if suffix == "/power":body={"signal":body["action"]}
            if suffix == "/commands":
                body = {"command": body["commands"][0]}
            if not suffix:
                resources = self.panel.server("GET", "/resources")
                attrs = resources.get("attributes", resources)
                server = self.panel.server("GET", "")
                meta = server.get("attributes", server)
                return {
                    "state": attrs.get("current_state"),
                    "resources": attrs.get("resources", {}),
                    "configuration": {
                        "build": {"memory_limit": meta.get("limits", {}).get("memory", 0)}
                    },
                }
            return self.panel.server(method, translated, body)
        p = self.cs.get("wings")
        if not p:
            raise ValueError("Không có Panel/Wings")
        r = httpx.request(
            method,
            p["url"].rstrip("/") + "/api/servers/" + p["uuid"] + suffix,
            json=body,
            headers={"Authorization": "Bearer " + self.secret_store.get(p["token"])},
            timeout=25,
        )
        r.raise_for_status()
        return r.json() if r.content else {"accepted": True}

    def do_inspect(self, kind, lines=100):
        if self.connected_bridge(kind):
            r = self.bridge.rpc_sync(
                self.p["id"], "inspect", {"kind": kind, "lines": min(int(lines), 200)}
            )
            if isinstance(r.get("data"), dict) and r["data"].get("minecraft_version"):
                self.p["minecraft_version"] = r["data"]["minecraft_version"]
            return r
        if kind == "status" and not (self.panel or "wings" in self.cs):
            if self.local:
                return self.local.inspect(kind, lines)
            if self.cs.get("ssh"):
                r = self.shell("pgrep -af java | head -n 5; free -b; uptime")
                return {
                    **r,
                    "data": {
                        "state": "unknown",
                        "note": "Host evidence only; process existence is not server readiness",
                    },
                    "verified": False,
                }
        if kind == "host":
            if self.local:
                return self.local.inspect(kind, lines)
            if self.p.get("volume") and self.p.get("uuid"):
                return super().do_inspect(kind, lines)
            return self.shell(
                "free -b; df -B1; uptime; ps -eo pid,comm,rss,pcpu --sort=-rss | head -n 12"
            )
        if kind == "status":
            raw = self.api("GET", "")
            return {
                "verified": True,
                "data": {
                    "state": raw.get("state"),
                    "resources": raw.get("resources", raw.get("utilization", {})),
                    "limits": raw.get("configuration", {}).get("build", {}),
                },
            }
        if kind == "logs":
            if self.local:
                return self.local.inspect(kind, lines)
            if self.cs.get("ssh", {}).get("volume"):
                return self.shell(
                    "tail -n "
                    + str(max(1, min(int(lines), 400)))
                    + " "
                    + shlex.quote(self.absolute("logs/latest.log"))
                )
            return self.do_files("read", "logs/latest.log")
        if kind == "plugins":
            if self.local:
                return self.local.inspect(kind, lines)
            if self.cs.get("ssh", {}).get("volume"):
                return self.shell(
                    "find "
                    + shlex.quote(self.absolute("plugins"))
                    + " -maxdepth 1 -type f -name '*.jar' -printf '%f\\n'"
                )
            return self.do_files("list", "plugins")
        return self.do_console(
            {"players": "list", "tps": "spark tps", "health": "spark health show --memory"}[kind]
        )

    def _logs(self):
        if self.connected_bridge("logs"):
            return self.bridge.rpc_sync(
                self.p["id"], "inspect", {"kind": "logs", "lines": 100}
            ).get("stdout", "")
        if self.local:
            return self.local.logs()["stdout"]
        if self.cs.get("ssh", {}).get("volume"):
            return self.shell("tail -n 100 " + shlex.quote(self.absolute("logs/latest.log")))[
                "stdout"
            ]
        if self.panel:
            return str(self.panel.read("logs/latest.log"))[-18000:]
        return ""

    def do_console(self, command):
        if "\n" in command or "\r" in command:
            raise ValueError("One command per action")
        if self.connected_bridge("console"):
            return self.bridge.rpc_sync(
                self.p["id"],
                "console",
                {"command": command},
                "read" if console_read(command) else "change",
            )
        if not (self.panel or "wings" in self.cs):
            if not self.p.get("volume") or not self.p.get("uuid"):
                raise ValueError("Console needs bridge, Panel/Wings, or SSH with container UUID")
            cmd = shlex.quote(command.strip().lstrip("/"))
            before = self._logs()
            r = self.shell(
                "docker exec "
                + shlex.quote(self.p["uuid"])
                + " sh -c "
                + shlex.quote(
                    'test -p /tmp/console-input && printf "%s\\n" ' + cmd + " > /tmp/console-input"
                )
            )
            if r["exit_code"]:
                return {
                    **r,
                    "error": "SSH console FIFO unavailable; configure bridge or Panel",
                    "verified": False,
                }
        else:
            before = self._logs()
            self.api("POST", "/commands", {"commands": [command.strip().lstrip("/")]})
        time.sleep(2)
        after = self._logs()
        output = (
            after[len(before) :]
            if after.startswith(before)
            else "\n".join(x for x in after.splitlines() if x not in before.splitlines())
        )
        receipt = console_receipt(command, output) or diagnostic_receipt(command, output)
        return {
            "accepted": True,
            "console_output": output,
            "verified": bool(receipt),
            "verification": receipt,
            "data": receipt.get("data", {}) if receipt else {},
            "note": "Fresh log evidence only. Acceptance is not completion.",
        }

    def startup_marker(self):
        try:
            if self.cs.get('ssh',{}).get('volume'):
                pattern=r'Done \([0-9.]+s\)'
                result=self.shell('grep -E '+shlex.quote(pattern)+' '+shlex.quote(self.absolute('logs/latest.log'))+' | tail -n 1')
                text=result.get('stdout','')
            elif self.panel:text=str(self.panel.read('logs/latest.log'))
            else:return super().startup_marker()
            matches=[line for line in text.splitlines() if re.search(r'Done \([\d.]+s\)',line)]
            return matches[-1] if matches else ''
        except Exception:return ''

    def do_power(self, action):
        if self.panel or "wings" in self.cs:
            return super().do_power(action)
        if self.local:
            return self.local.power(action)
        if self.cs.get("ssh") and self.p.get("uuid"):
            verb = {"start": "start", "stop": "stop", "restart": "restart", "kill": "kill"}[action]
            result = self.shell("docker " + verb + " " + shlex.quote(self.p["uuid"]), timeout=180)
            if result["exit_code"]:
                return result
            for _ in range(90):
                status = self.shell(
                    "docker inspect --format "
                    + shlex.quote("{{.State.Running}}")
                    + " "
                    + shlex.quote(self.p["uuid"])
                )["stdout"].strip()
                good = (
                    status == "false"
                    if action in ("stop", "kill")
                    else status == "true" and bool(re.search(r"Done \([\d.]+s\)", self._logs()))
                )
                if good:
                    return {
                        "verified": True,
                        "verification": {
                            "kind": "power_readback",
                            "scope": "container and server startup",
                        },
                        "state": status,
                    }
                time.sleep(2)
            return {
                "verified": False,
                "note": "Power dispatched; readiness not confirmed. Do not retry blindly.",
            }
        raise ValueError(
            "Plugin-only cannot start an offline server. Add Panel or SSH power capability."
        )

    def _path(self, path):
        p = pathlib.PurePosixPath(path)
        if p.is_absolute() or ".." in p.parts or not str(path):
            raise ValueError("Path must stay inside the selected server")
        return str(p)

    def _mkdir_panel(self, path):
        current = ""
        for part in pathlib.PurePosixPath(path).parts:
            if part in (".", ""):
                continue
            out = self.panel.server("GET", "/files/list", params={"directory": "/" + current})
            names = [r.get("attributes", r).get("name") for r in out.get("data", [])]
            if part not in names:
                self.panel.server(
                    "POST", "/files/create-folder", {"root": "/" + current, "name": part}
                )
            current = (current + "/" + part).strip("/")

    def do_files(self, action, path, content=None, backup_path=None):
        path = self._path(path)
        if action == "write" and content is not None and path.endswith((".yml", ".yaml")):
            yaml.safe_load(content)
        if self.connected_bridge("files"):
            return self.bridge.rpc_sync(
                self.p["id"],
                "files",
                {"action": action, "path": path, "content": content, "backup_path": backup_path},
                "read" if action in ("read", "list") else "change",
                timeout=60,
            )
        if self.local:
            return self.local.files(action, path, content, backup_path)
        if self.cs.get("ssh", {}).get("volume"):
            return super().do_files(action, path, content, backup_path)
        if not self.panel:
            raise ValueError("Files need Panel, SSH volume or bridge")
        if action == "read":
            return {"stdout": str(self.panel.read(path))[:100000], "verified": True}
        if action == "list":
            rows = self.panel.server("GET", "/files/list", params={"directory": "/" + path}).get(
                "data", []
            )
            return {
                "stdout": "\n".join(str(r.get("attributes", r).get("name", "")) for r in rows),
                "data": rows,
                "verified": True,
            }
        if action == "restore":
            if not backup_path or not backup_path.startswith(".kei-backups/"):
                raise ValueError("Use a Kei backup")
            content = self.panel.read(self._path(backup_path))
            action = "write"
        if action not in ("write", "remove"):
            raise ValueError("Unknown files action")
        backup = ".kei-backups/" + str(int(time.time() * 1000)) + "/" + path
        folder = str(pathlib.PurePosixPath(path).parent)
        self._mkdir_panel(folder)
        listing = self.panel.server("GET", "/files/list", params={"directory": "/" + folder}).get(
            "data", []
        )
        names = [r.get("attributes", r).get("name") for r in listing]
        old = self.panel.read(path) if pathlib.PurePosixPath(path).name in names else None
        if old is not None:
            self._mkdir_panel(str(pathlib.PurePosixPath(backup).parent))
            self.panel.write(backup, str(old))
        if action == "remove":
            if old is None:
                raise ValueError("File not found")
            self.panel.server(
                "POST",
                "/files/delete",
                {
                    "root": "/" + str(pathlib.PurePosixPath(path).parent),
                    "files": [pathlib.PurePosixPath(path).name],
                },
            )
            names = self.do_files("list", str(pathlib.PurePosixPath(path).parent))[
                "stdout"
            ].splitlines()
            return {
                "verified": pathlib.PurePosixPath(path).name not in names,
                "backup_path": backup,
            }
        if content is None:
            raise ValueError("Write needs content")
        if path.endswith((".yml", ".yaml")):
            yaml.safe_load(content)
        self._mkdir_panel(str(pathlib.PurePosixPath(path).parent))
        self.panel.write(path, content)
        verified = self.panel.read(path) == content
        return {
            "verified": verified,
            "backup_path": backup if old is not None else None,
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
        }

    def read_binary(self, path, cap=64 * 1024 * 1024):
        path = self._path(path)
        if self.local and not self.connected_bridge("files"):
            return self.local.binary(path, cap)
        if self.cs.get("ssh", {}).get("volume"):
            c = self.client()
            try:
                from .execution import prepare_ssh
                command="head -c "+str(cap+1)+" "+shlex.quote(self.absolute(path))
                command,password,pty=prepare_ssh(self.cs['ssh'],self.secret_store,command)
                if pty:raise PermissionError('Binary read qua su/PTY không bảo toàn dữ liệu; cấu hình sudo hoặc dùng Panel/SFTP.')
                i,o,e=c.exec_command(command,timeout=45)
                if password:i.write(password+'\n');i.flush()
                i.channel.shutdown_write()
                raw = o.read()
                error = e.read().decode("utf-8", "replace")
                if o.channel.recv_exit_status():
                    raise OSError(error[:1000])
                if len(raw) > cap:
                    raise ValueError("Binary file exceeds analysis limit")
                return raw
            finally:
                c.close()
        if self.connected_bridge("files"):
            result = self.bridge.rpc_sync(self.p["id"], "files", {"action": "binary", "path": path})
            raw = base64.b64decode(result["base64"])
        elif self.panel:
            out = self.panel.server("GET", "/files/download", params={"file": "/" + path})
            url = out.get("attributes", out)["url"]
            with httpx.stream("GET", url, timeout=60) as response:
                response.raise_for_status()
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > cap:
                        raise ValueError("Binary file exceeds analysis limit")
        else:
            raise ValueError("Binary files unavailable")
        if len(raw) > cap:
            raise ValueError("Binary file exceeds analysis limit")
        return bytes(raw)

    def do_plugin_install(self, url, filename, sha256=None, stage_only=False):
        if self.cs.get("ssh", {}).get("volume") and not self.local:
            return super().do_plugin_install(url, filename, sha256, stage_only)
        if (
            "/" in filename
            or "\\" in filename
            or not filename.endswith(".jar")
            or not url.startswith("https://")
        ):
            raise ValueError("HTTPS URL and plain .jar filename required")
        raw = bytearray()
        with httpx.stream("GET", url, follow_redirects=True, timeout=60) as r:
            r.raise_for_status()
            for chunk in r.iter_bytes():
                raw.extend(chunk)
                if len(raw) > 64 * 1024 * 1024:
                    raise ValueError("Plugin exceeds 64 MiB")
        digest = hashlib.sha256(raw).hexdigest()
        if sha256 and digest.lower() != sha256.lower():
            raise ValueError("Checksum mismatch")
        jar = zipfile.ZipFile(io.BytesIO(raw))
        descriptor = None
        for name in ("paper-plugin.yml", "plugin.yml"):
            if name in jar.namelist():
                descriptor = yaml.safe_load(jar.read(name))
                break
        if not isinstance(descriptor, dict) or not descriptor.get("name"):
            raise ValueError("Invalid plugin descriptor")
        plugins = self.do_inspect("plugins")["stdout"]
        missing = [
            d for d in descriptor.get("depend", []) if d.casefold() not in plugins.casefold()
        ]
        if missing and not stage_only:
            raise ValueError("Missing dependencies: " + ", ".join(missing))
        api = str(descriptor.get("api-version", ""))
        if api and tuple(map(int, api.split("."))) > tuple(
            map(int, self.p["minecraft_version"].split("."))
        ):
            raise ValueError("Plugin API exceeds Minecraft version")
        relative = (".kei-staging/" if stage_only else "plugins/") + filename
        if self.connected_bridge("files"):
            result = self.bridge.rpc_sync(
                self.p["id"],
                "files",
                {
                    "action": "write_binary",
                    "path": relative,
                    "base64": base64.b64encode(raw).decode(),
                },
                "change",
                timeout=90,
            )
        elif self.local:
            result = self.local.write_binary(relative, bytes(raw))
        elif self.panel:
            folder = str(pathlib.PurePosixPath(relative).parent)
            self._mkdir_panel(folder)
            # Preserve an existing JAR through the Panel copy API before replacement.
            listing = self.do_files("list", folder)["stdout"].splitlines()
            if filename in listing:
                previous = self.read_binary(relative)
                backup = ".kei-backups/" + str(int(time.time() * 1000)) + "/" + folder
                self._mkdir_panel(backup)
                self.panel.upload(backup, previous, filename)
            self.panel.upload(folder, bytes(raw), filename)
            result = {"verified": hashlib.sha256(self.read_binary(relative)).hexdigest() == digest}
        else:
            raise ValueError("No installation connector")
        return {
            **result,
            "path": relative,
            "descriptor": descriptor,
            "sha256": digest,
            "note": "Installed/staged file only; verify enabled after a proper restart.",
        }
