# Install the Minecraft bridge / Cho Kei vào Minecraft

The Discord bot is the brain. This small Paper/Leaf plugin is her Minecraft hand:
in-game chat, account linking, scoped commands, TPS/MSPT, JVM memory and file access.
The plugin does not run a language model or require SSH.

Bot là não, plugin là tay. Có tay rồi mới đọc TPS thật, nói chuyện trong game và
chạy lệnh trên server; nàng không cần tự SSH vòng quanh cái máy 🦭

## Get the JAR

Use `keys-keys-bridge-3.1.0-rc.1.jar`, the **shaded** distributable. Do not install
the `original-...jar` Maven intermediate. Requires Paper/Leaf 1.21.11 and Java 21+
for this build. Other Minecraft versions are not established by this release's tests.

Build it yourself from the repo if no release asset is available:

```sh
cd bridge
mvn -B package
```

The result is `bridge/target/keys-keys-bridge-3.1.0-rc.1.jar` from the repo root.
Maven and JDK 21 are build dependencies; players do not need either to chat with Kei.

## Pair it in five steps

1. On the bot machine, run `keys-keys server add --kind bridge`. Use the existing
   server ID if that server already has a Panel or SSH connection.
2. Enter an endpoint the **Minecraft server can reach**, such as
   `ws://BOT_LAN_IP:8767/v1/bridge` on a trusted LAN. A remote deployment should use
   a TLS reverse proxy and `wss://`. `localhost` only works when both processes
   actually share that network namespace.
3. Stop Minecraft normally. Copy the JAR to `plugins/KeysKeysBridge.jar`.
4. Copy the generated private file from
   `data/bridge-configs/SERVER_ID/config.yml` into
   `plugins/KeysKeysBridge/config.yml`. Keep that token private; no model/provider
   keys belong in the Minecraft plugin config.
5. Start Minecraft normally and run `/keibridge` as an operator. Look for
   `KEYS_BRIDGE_CONNECTED protocol=1` and use the bot's diagnostics to verify a live
   connection. A JAR sitting in `plugins/` does not prove connection.

Tóm gọn: tạo pairing, dừng server, bỏ JAR + config vào đúng chỗ, bật lại, check
`/keibridge`. Không `/reload`, PlugMan hay hot reload.

## In-game use

```text
/kei chào Kei
/kei link YOUR_ONE_TIME_LINK_CODE
/kei kiểm tra TPS và RAM Java
/kei debug minimal
```

Regular players can talk. Link codes associate the current Minecraft UUID with
Discord. Server ownership/explicit grants determine copilot rights. In offline-mode,
an unauthenticated UUID never proves identity; AuthMe sessions are checked where
available. DiscordSRV account links can help resolve identity but do not grant rights.

RAM reported by the plugin is **JVM heap**, not the whole machine's RAM. A plugin
cannot start a stopped Minecraft server; pair Panel or a registered local/SSH
power connector if that is needed.

## Current evidence

The operator's existing server was audited directly: a `3.0.0-rc.1` JAR was installed,
its matching build existed on the build host, connection logs were present and live
TPS/MSPT RPC receipts were recorded. The prior problem was the missing convenient
download/instructions, not an absent implementation. This release supplies the new
versioned artifact separately; the old protocol-1 plugin remains compatible.

The new artifact is integration-tested in an isolated Leaf instance. Do not infer
that every player's authentication setup or every Paper fork is covered; see the
release evidence for the exact tests.
