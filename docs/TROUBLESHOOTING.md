# Troubleshooting / Nó lại làm sao nữa

Start with `keys-keys doctor`. Share the check name and redacted error, not credential values.

| Symptom | What to do |
|---|---|
| No config / blank persona | Run `setup`; edit an existing config with `setup --edit` |
| Discord token fails | Check Developer Portal token; never paste it publicly |
| Bot online, ignores text | Enable Message Content Intent, check channel permissions, tag/reply/use configured trigger |
| Does not randomly join public chat | Correct by default; enable participation controls in `/settings` deliberately |
| Provider URL fails only in Docker | `localhost` is the container; use a reachable host/address |
| Provider HTTP works but tool check fails | Select a model/adapter with actual native tool calling |
| Vision rejected | Model/adapter may not support images; use JPEG/PNG/WebP within limits and doctor `--vision` |
| Panel returns 401/403 | Wrong key type, expired session or account lacks permission; not a Wings token |
| Cloudflare blocks the API client | Use an approved API-access hostname or reachable internal Panel endpoint; gateway denial does not establish whether credentials work |
| Panel login needs JS | Install optional browser support or supply an authenticated session |
| 2FA/captcha | Complete authentication and provide a valid session; do not disable protection |
| SSH unknown/changed key | Verify host and fingerprint; do not blindly replace known_hosts |
| No server files/console capability | Add a connector that supplies it; SSH account alone does not identify a volume |
| Bridge paired but offline | Check reachable endpoint, published port, matching server ID/token and normal plugin startup |
| Minecraft can chat but cannot operate | Login/AuthMe, link account, then verify assignment on that server |
| Task needs verification | Inspect the requested postcondition; do not repeat the mutation blindly |
| Uncertain after disconnect | Reconcile actual server state before retry |
| Two replies per message | Stop the duplicate consumer; one token should have one active runtime |

Progress cards describe actual work, not private reasoning. Minimal shows the objective and
checklist; advanced adds compact real commands/logs. Use the Off progress option in `/settings` if you just want the result.
