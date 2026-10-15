# Minecraft bridge / Plugin Minecraft

The plugin is the hand. Python is the brain. Neither should sit on the tick thread
waiting for a model to finish its sentence.

## Install

1. Download `keys-keys-bridge-3.0.0-rc.1.jar` from this release, or build `bridge/` with Maven and Java 21.
2. Put the JAR into the server's `plugins/` directory.
3. Run `keys-keys server add --kind bridge` on the bot host. For an existing server, enter its existing ID.
4. Copy the generated `data/bridge-configs/SERVER/config.yml` to `plugins/KeysKeysBridge/config.yml`.
5. Restart Minecraft normally. Do not hot reload the plugin.
6. `keibridge` in the Minecraft console reports connection state. `/server list` in Discord reports bot capabilities.

Target: Paper API 1.21.11, including the Leaf deployment used for acceptance. Other versions
and Folia are not implied by that target; verify compatibility before deployment.

## Network

The plugin opens an outbound WebSocket to the bot, for example
`ws://BOT_LAN_ADDRESS:8767/v1/bridge`. The address must be reachable from the Minecraft host.
Compose publishes port 8767 by default. For internet deployment put the endpoint behind
your HTTPS reverse proxy and use `wss://`.

In a Pelican Python slot, bind to its allocated TCP port and use that port in the plugin
endpoint. A pairing file is not proof of connection; the handshake is.

Pairing tokens are private and bound to one registered server. No model/API/SSH credential
is placed in the plugin.

## Talk and link

```text
kei ơi, cái này là sao?       public Minecraft conversation
/kei nhớ vụ keys keys không  private reply
/kei link CODE              redeem the code from Discord /link
/kei confirm TASK           confirm the exact pending dangerous step
/kei debug minimal          progress settings
/kei privacy strict         keep memories in their source context
/kei persona soft           select the preserved softer persona
/kei dm on                  opt into social DMs after linking Discord
/kei unlink                 remove this server's account link
```

Regular players can chat. Copilot requires an explicit server assignment. Linked players
inherit the assigned Discord account's rights **on that server**, not the whole registry.
Names are labels; UUIDs on different offline-mode servers are not automatically one person.

Online-mode authentication is accepted. On offline-mode servers, the AuthMe hook verifies
login before linking or copilot. If DiscordSRV supplies an existing account link, it can
be reused without copying its database. Without trusted authentication, chat remains
available but operational identity is not established.

The bridge uses request IDs and a receipt journal. After an interrupted mutation it
reports uncertainty and requires readback; it does not replay on reconnect.
