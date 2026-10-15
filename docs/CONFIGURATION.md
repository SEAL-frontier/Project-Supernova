# Configuration / Cấu hình

Prefer `keys-keys setup`. This reference is for automation and custom deployments.
The checked-in persona/env/test placeholders intentionally contain nothing.

New private files:

```text
data/config.yaml          global settings, server profiles, secret references
data/secrets.json         credential values; restricted local permissions
data/persona.md           your persona
data/kei.db               memory, relationships, grants, jobs and audit
data/panel-sessions/      authenticated Panel sessions
data/bridge-configs/      generated plugin pairing files
```

Existing `kei.yaml`, `.env`, `known_hosts` and persona paths are supported. A `KEI_CONFIG`
environment variable or `--config` option selects a nondefault config. New files in `data/`
are ignored by Git. Do not move secrets into README examples to make them look complete.

Relevant non-secret settings:

```yaml
timezone: Asia/Ho_Chi_Minh
social:
  triggers: [kei]
  ambient:
    enabled: false
    mode: whitelist        # free or whitelist when enabled
    channels: []
  reply_cooldown: 120
  dm_daily_limit: 3
  dm_interval_hours: 4
  quiet_start: 22
  quiet_end: 8
memory:
  retention_days: 90
  cross_context: discreet  # strict is also available
  incremental_hours: 6
  daily_hour: 4
bridge:
  enabled: false
  host: 0.0.0.0
  port: 8767
```

Wizard answer keys for a private unattended JSON file: `language`, `timezone`,
`discord_token`, `provider_base`, `provider_key`, `provider_model`, `owner_id`,
`persona_file`, `persona`, `connection`. `connection` is `chat`, `panel`, `ssh`, `bridge` or `local`.

Panel answers: `panel_url`, `panel_auth` (`key`, `password`, `session`), `panel_key`,
`panel_username`, `panel_password`, `session_file`, `server_index` (1-based), `server_id`.
SSH answers: `ssh_host`, `ssh_port`, `ssh_user`, `ssh_auth`, `ssh_key`, `ssh_password`,
`trust_host_key`, `ssh_volume` or `volume_index`, `minecraft_version`, `server_name`, `server_id`.
Bridge answers: `server_name`, `server_id`, `bridge_port`, `bridge_url`.
Local answers: `local_root` (an absolute path visible to the bot), `local_writable`
(`no` by default; `yes` to allow file edits), `server_name`, `server_id`.

```sh
keys-keys server add --kind local
```

A shared physical host does not imply shared container paths or processes. The local
wizard checks the directory the bot can actually read. Process actions require explicit
operator registration; a mounted folder alone does not supply live TPS or console.
See [local access](LOCAL_ACCESS.md) for Linux, Windows and bind mounts.

Only include fields the selected path asks for. Credential values belong in a private
answer file, never a checked-in example. Interactive prompts hide terminal secrets.
