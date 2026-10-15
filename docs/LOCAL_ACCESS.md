# Minecraft on your own machine / Minecraft ở máy của m

Kei can read and change an explicitly shared server folder without SSH. Live TPS,
players and Minecraft commands still need the Paper bridge or Panel. A folder
containing `server.jar` is not proof that a server is running.

Kei đọc/sửa được thư mục server đã cấp quyền, không bắt buộc SSH. Muốn TPS thật,
player online hay chạy lệnh Minecraft thì thêm plugin bridge hoặc Panel. Đừng cho
nàng đoán TPS bằng cách nhìn cái file JAR 😭

## Same machine, same permissions

Add a connection to the server in your private `kei.yaml`. Start read-only:

```yaml
servers:
  - id: survival
    name: Survival
    minecraft_version: '1.21.11'
    owners: ['YOUR_DISCORD_ID']
    guilds: ['YOUR_GUILD_ID']
    aliases: [smp]
    connectors:
      local:
        root: /srv/minecraft/survival
        writable: false
assignments:
  YOUR_DISCORD_ID: [survival]
guild_defaults:
  YOUR_GUILD_ID: survival
```

On Windows, use an absolute path such as `'D:\Minecraft\Survival'`. Kei runs with
the same account permissions as the Python process. Set `writable: true` only for
a folder she is meant to edit. Writes preserve an existing file in `.kei-backups`
and verify the new content by reading it back. Removing a file also keeps a backup.
Existing world/database protection and action approvals still apply.

Windows dùng đường dẫn tuyệt đối, ví dụ `'D:\Minecraft\Survival'`. Bot chỉ có
quyền của account chạy Python. Bật `writable: true` nếu muốn sửa file; bản cũ giữ
trong `.kei-backups`, bản mới được đọc lại để kiểm tra.

## Containers and different machines

The path is **inside Kei's container**, not the host path. For example, mount only
the selected server folder into Kei:

```yaml
volumes:
  - /srv/minecraft/survival:/minecraft/survival:ro
```

Then use `root: /minecraft/survival` and `writable: false`. Use a read/write bind
mount plus matching UID/GID if file edits are intended. A read-only mount remains
read-only regardless of the YAML flag; errors say which capability is unavailable.

Bot và Minecraft ở hai container chung máy vẫn là hai thế giới riêng. Chỉ mount
thư mục server cần dùng. Không cần Docker socket, privileged mode hay quyền cả host.
Container không nhìn thấy host PID thì phần process sẽ báo unknown; đừng “fix” bằng
cách mở tung isolation. Dùng bridge để chat/lệnh, Panel để power, hoặc SSH đã có.

Linux bot + Windows Minecraft, Windows bot + Linux Minecraft, or separate physical
machines: use the bridge/Panel/SSH across that boundary. Local paths do not magically
cross the network. No custom Windows EXE is required: Python, Java and your existing
server launcher are enough.

## Optional registered process actions

Most people should use Panel for start/stop and the bridge for live commands.
For a directly managed local server, the operator can register fixed launcher
commands. These are argv lists, **not shell command strings**:

```yaml
local:
  root: /srv/minecraft/survival
  writable: true
  process:
    pid_file: server.pid
    identity: java
    ready_timeout: 120
    actions:
      start: [python3, manage_server.py, start]
      stop: [python3, manage_server.py, stop]
      restart: [python3, manage_server.py, restart]
```

Your own launcher writes the real Java PID into `server.pid`; its command must
contain `identity`. Windows can match the process executable path/name. The
launcher returns after dispatch, rather than waiting for Minecraft to exit.
Only registered actions run, with `shell=False`, inside the selected server root.
Missing or inaccessible PID evidence cannot authorize touching another process.
Start/restart requires the matching process **and a fresh `Done (...)` startup
line**; an old startup line is not accepted. A timeout is reported as uncertain,
so inspect the process/log before retrying.

## General SSH shell is a separate host privilege

Server ownership, delegated administration and copilot permission authorize the
selected server's typed file/console operations. They do **not** grant a general
shell on the machine hosting it. An SSH command's working directory is not a
sandbox, especially when the connection uses root or sudo.

Only the bot's global `owner_id` can use general `remote_shell` by default. The
operator can explicitly authorize another Discord identity in that server's
private configuration:

```yaml
servers:
  - id: survival
    host_admins: ['YOUR_TRUSTED_HOST_ADMIN_DISCORD_ID']
    # Keep the server's existing connectors and other fields here.
```

`host_admins` is an **operator-edited config field**, not a Discord/Web setting.
A registered Panel profile, relationship rank or server owner cannot grant it.
The user must still have the ordinary server assignment; it is checked again
before dispatch. Verification readbacks cannot bypass this host-shell gate.
Leave the list empty for ordinary delegated server admins. Host-wide disk and
process investigations remain available to the global operator or explicit host
admins; server file and console tools remain available under normal scoped rights.

Quyền quản trị một server không phải quyền root của cả host. Chỉ operator sửa
`host_admins` trong config riêng; `/settings` và Web UI không tự cấp quyền này.

## Choosing the right server

IDs and names/aliases are matched exactly. Guild defaults are checked against
permissions. If more than one eligible server exists and no default/selection is
set, Kei asks which one. A relationship rank never grants server access.

Nếu có nhiều server, đặt `guild_defaults` hoặc chọn server trong `/settings`.
Gọi tên/ID cụ thể cũng được. Mơ hồ thì hỏi lại, không bốc đại một server để restart.

## Verification limits

Actual Windows filesystem/process probes and Linux container filesystem/process
probes are recorded in the release evidence. Native Linux host Python dependencies
were unavailable in the staging host, so that execution path was not tested outside
the container. Support is portable, but every Windows/Linux/
container combination has not been tested against a real Minecraft process.
Use the connection diagnostics to check the permissions of your own deployment.
