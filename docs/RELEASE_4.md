# Supernova 4.0 release candidate

The 4.0.0-rc.2 correction separates casual work stories from requested reports,
keeps personal call names when linking accounts and supplies learned verified
procedures to worker planning. [The feedback audit](REQUIREMENTS_AUDIT_4.md)
lists 35 reconstructed checkpoints and their remaining limits; this is not a
claim that all 35 are fully accepted.

Kei connects conversation, durable social memory and authorized Minecraft work. Version 4 focuses on keeping those parts coherent: remembering a shared joke, knowing who a reply belongs to, and doing the assigned work even when the character is annoyed.

## Start here

You can also install the Python wheel attached to the GitHub release: `python -m pip install keys_keys-4.0.0rc2-py3-none-any.whl`. The bridge JAR keeps its own version; it is the existing tested artifact, not a new gameplay acceptance claim.

Run `keys-keys setup` once on the bot host. Keep the generated credentials and private persona on that host. Use `/setup` for the personal introduction, or sign into the configured dashboard with Discord. `/settings` remains available for recovery and quick changes.

In **Your space → Chat your way**, choose your timezone, add personal call names separated by commas, and write optional custom instructions. These add preferences; they do not replace the system prompt or grant server rights. You can also express boundaries naturally in conversation.

In **Minecraft → Add a Minecraft server**, choose a connection:

- **Pterodactyl / Pelican:** enter the panel URL and your Client API key, read the actual server list, select the server and connect.
- **SSH / SFTP:** enter the host, port, account and Minecraft folder. Use a password or upload a private key. Compare the displayed host fingerprint with the server operator before saving. A changed trusted fingerprint is rejected. This does not grant Root mode automatically.
- **Paper / Leaf plugin:** enter the bot's reachable `wss://…/v1/bridge` endpoint and download the generated private `config.yml`. Place it with the existing bridge JAR. The Minecraft plugin connects **out**; it does not require a separate inbound Minecraft port. The bot listener/reverse proxy must already be configured and reachable.
- **Local folder:** bot operator only. Select a directory the bot process can actually read. Containers need a scoped bind mount; being on the same physical host is not enough. Process start/stop requires separately registered actions. See `docs/LOCAL_DEPLOYMENT.md` where available.

Use **Test connection** after saving. An SSH folder check proves SSH/files access; a live bridge check proves the connection, not every plugin command or gameplay permission. Connection credentials stay on the bot host. The one-time plugin config download contains its own pairing token; treat it as a credential.

## Chat, search and memory

Public ambient engagement stays off. A name, mention, reply or bounded continuation can invite a response; it does not subscribe every person in the channel. Personal call names are per person. Plain conversation sends normally, while interleaved public replies and task reports retain their request reference.

Searching uses a small status that becomes the answer. A source count means pages were actually fetched successfully, not merely listed by a search engine. Stable everyday conversation needs no search. Technical claims about current versions or unknown plugin behavior need evidence or an explicit admission of uncertainty.

Relationship arrows express small or large changes, separately from ranks. State is global per linked person; original private excerpts remain private. Meaningful episodes keep original dialogue. History recall can expand a topic and retrieve original neighboring messages; this release does not require a separate vector database. Explicit forgetting invalidates summaries, occasions, aliases and other derived sources.

Proactive contact requires permission and respects mute, quiet instructions and unanswered messages. Observed activity/presence are hints, not diagnoses or proof of availability. Private birthdays/anniversaries are internal social occasions, separate from assigned tasks. The main bot owner can inspect these for diagnostics. Automatic public status uses public evidence or established character tastes, never private DM stories.

## Tiếng Việt

Đăng nhập Discord, vào **Your space** để chỉnh cách trò chuyện, múi giờ và tên riêng m dùng gọi Kei. Muốn thêm server thì vào **Minecraft**, chọn cách kết nối rồi bấm kiểm tra. Panel tương thích cả Pterodactyl lẫn Pelican; SSH cần đối chiếu fingerprint; plugin chủ động nối ra bot nên không bắt mở thêm cổng ở server Minecraft. Local folder chỉ dùng được nếu bot nhìn thấy thư mục thật, kể cả khi chạy trong container.

Mũi tên quan hệ đổi ngay khi có tương tác đủ ý nghĩa; ↑↑ / ↓↓ là biến động lớn chứ không mặc định lên/xuống rank. Chuyện riêng không tự mang ra public. Tình cảm phát triển trong hội thoại, không có nút bấm nhận người yêu. Việc được giao vẫn phải làm theo quyền đã cấp.

## Acceptance

Keep the `-rc` version until natural social behavior with durable memory, actual Minecraft plugin/copilot execution, and a fresh user's complete setup are all accepted. The operator has paused Minecraft execution acceptance for this round. Simulated tests, a successful read-only connection and isolated provider calls do not replace those three gates.
