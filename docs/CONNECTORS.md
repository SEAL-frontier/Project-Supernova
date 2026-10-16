# Connections / Kết nối

## Pick what you have

| Connection | Minimum input | What it supplies |
|---|---|---|
| Panel API | URL + **Client** API key | Discover/select server, resources, console, power, files |
| Panel account | URL + account/password or authenticated session | The same endpoints, limited by the account |
| Wings | Existing daemon URL/token + UUID | Compatibility with 2.x installations |
| SSH | Host + account + key/password | Host diagnostics; volume discovery; file/shell access |
| Bridge | Plugin JAR + generated pairing config | In-game chat, live JVM/TPS/players, console and files |
| Local | Explicit accessible server folder, optional registered process actions | Scoped file access without SSH; process control only where actually available |

Kei chooses by capability, not by flipping a coin. Bridge metrics describe the Minecraft
JVM; they are not the entire host's RAM. Plugin-only cannot start a server that is offline.
No connector means no claim that a capability exists.

Wizard sẽ tự liệt kê server Panel và dò volume SSH. Nếu có nhiều ứng viên thì chọn một;
không cần mò UUID hay UID:GID từ đầu. SSH fingerprint phải được đối chiếu; changed key
không được tự chấp nhận. Existing profiles remain usable.

## Panel

```sh
keys-keys server add --kind panel
```

Prefer a Client API key; a Wings daemon token is not that key. Keys only expose the
servers and actions granted to their account. Session login keeps cookies outside Git.

For JavaScript login, install the optional browser support:

```sh
python -m pip install '.[panel-login]'
playwright install chromium
```

Docker alternative:

```sh
docker build -t keys-keys:3.2.0-rc.4 .
docker build -f Dockerfile.browser -t keys-keys:3.2.0-rc.4-browser .
docker run --rm -it -v "$PWD/data:/app/data" keys-keys:3.2.0-rc.4-browser server add --kind panel
```

2FA/captcha is an authentication blocker, not an invitation to disable it. A verified
Playwright storage-state file can be supplied via the `session` option of the wizard.
Keep it private. The browser is for login; operational work returns to typed endpoints.

## SSH

```sh
keys-keys server add --kind ssh
```

Use a key file accessible inside the runtime or a password. New host keys require
fingerprint confirmation. For diagnostics/file operations requiring sudo, use a suitable
account; a key-only account needs passwordless sudo for those operations.

Volume discovery is bounded to common server directories. If the host uses a custom
layout, enter that directory. General SSH access does not magically create a Minecraft
console endpoint; use the bridge or Panel for reliable console access.

## Local files without SSH

```sh
keys-keys server add --kind local
```

Enter the absolute server directory visible from the bot and start read-only. Inside
a container this is the mount destination, not the host path. Windows can use an
ordinary absolute folder path; no custom EXE is required. Live Minecraft commands
and TPS need the bridge or Panel. See [local access](LOCAL_ACCESS.md) for permission,
container and registered-launcher examples.

## Missing or uncertain results

`doctor` performs reads, not test bans or restarts. It labels checks it did not perform.
If a mutation loses its connection after dispatch, the task must inspect the actual state
before any retry. Changing connector is not permission to execute the same command twice.
