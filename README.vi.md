<div align="center">

<img src="assets/kei.png" alt="Tendou Kei chỉnh kính và phán xét cái repo này" width="160" height="160" />

# keys-keys 🗝️🗝️

**Bot AI tự host: vừa trò chuyện, vừa vận hành Minecraft server**

*Her server. Your problem.*

Thật ra là her problem, your server. Chia quyền nuôi server hơi lỗi. 😭

![Version](https://img.shields.io/badge/version-3.2.0--rc.4-EFA5A5?style=flat-square)
![Architecture](https://img.shields.io/badge/architecture-Supernova-aca9e8?style=flat-square)
[![MIT](https://img.shields.io/badge/license-MIT-efa5a5?style=flat-square)](LICENSE)

[English](README.md) · [Tiếng Việt](README.vi.md) · [Cài đặt](docs/QUICKSTART.md) · [Changelog](CHANGELOG.md)

</div>

## Project này là gì?

**keys-keys là bot AI tự host, vừa trò chuyện vừa làm copilot cho Minecraft server.**
M có thể nói chuyện với ẻm trong DM Discord, channel hoặc ngay trong game. Người được
assign còn có thể giao việc server bằng chat: xem TPS/RAM, tìm nguyên nhân lag, đọc/sửa
config, quản lý plugin và chạy lệnh. Có tool thật, có kiểm tra kết quả.

Bot Python giữ phần hội thoại, memory và agent. Nó nối với Panel, SSH hoặc plugin
Minecraft tùy thứ m có sẵn. Một bot phục vụ được nhiều người và nhiều server được
phân quyền. M tự cấp Discord token, endpoint model và persona; muốn thử chat trước
thì chưa cần nối server ngay.

## Vì sao làm project này?

Vì “vào Minecraft chơi tí” rất dễ biến thành mở panel, SSH, lục ba cái log, sửa config
rồi đọc trang release plugin. Có người bảo “server lag” là m tự nhiên có thêm nghề.
Không lương, nhưng được tag tên liên tục. 🥀

Bọn t muốn một nhân vật **vừa ngồi tám cùng nhóm, vừa xử lý việc server khi được nhờ**,
ngay trong cuộc trò chuyện đó. Chat thường thì nói chuyện tự nhiên. Giao việc thì phải
đi xem, làm và đưa kết quả có bằng chứng, thay vì hứa hỗ trợ rồi nằm im.

Đó là lý do **Supernova** tách lượt chat khỏi agent làm việc, đồng thời giữ memory,
tiến độ và quyền server cùng một chỗ. “Adaptive” là chọn cách xử lý hợp với yêu cầu;
“hybrid” là tận dụng kết nối sẵn có của server. Mở source để người khác cũng tự host
được với server, model và nhân vật của họ. Bản thử nghiệm ban đầu dùng Tendou Kei.
Người ta cho ẻm một buổi chiều yên bình; bọn t cho ẻm một Minecraft server. 😭

> **3.2.0-rc.4 đang là release candidate.** Nghiệm thu gồm social tự nhiên và memory bền,
> plugin/connector hoạt động trên server thật, và người mới cài được theo hướng dẫn.
> Xem [biên bản triển khai](IMPLEMENTATION.md) và [bảng tính năng](FEATURE_MATRIX.md).

### Sao lại tên keys-keys?

Tên ẻm là **Kei**. Bọn t cứ gọi thành **keys** để ragebait, xong đem luôn tên sai lên
GitHub. Thiếu tỉnh táo nhưng rất nhất quán. 🥀 Character/avatar thử nghiệm là **Tendou Kei**;
persona của bản tự host do m viết. Đây là fan project; quyền nhân vật và ảnh thuộc chủ sở hữu.

### Bắt đầu ở đây

**`/setup`** để bắt đầu, **`/settings`** để chỉnh lại. Tính cách, privacy, memory,
profile quan hệ, link tài khoản và server được assign nằm ở đó.
[Discord + Web UI tùy chọn](docs/SETTINGS.md) · [File local không cần SSH](docs/LOCAL_ACCESS.md)
· [Cài plugin Minecraft](docs/BRIDGE_INSTALL.md).

### Nó làm được gì?

| Trò chuyện | Minecraft copilot |
|---|---|
| Nhận đúng người qua ID, display name và nickname | Đọc TPS/MSPT, RAM Java, player, log và plugin |
| Chọn trả lời, nói ngắn, react hoặc im | Xem → lên kế hoạch → làm → kiểm chứng → điều chỉnh |
| Memory theo người/nhóm, kỷ niệm giữ đoạn gốc | Task bền vững, bằng chứng, tiến độ gọn |
| Chủ động nhắn khi opt-in, có giờ yên lặng | Backup/readback config, stage/cài plugin, phân tích profiler |
| Nối Discord/Minecraft sau khi xác thực | Assign đúng người/server, xác nhận bước nguy hiểm |
| Đọc ảnh và tìm nguồn trên web | Dùng Panel, Wings, SSH hoặc plugin bridge sẵn có |

**Supernova** là tên kiến trúc. Phần social lấy cảm hứng từ checklist Aurora đã chốt;
repo không import hay phụ thuộc một codebase Aurora khác.

Chat thường đi đường nhẹ, nhờ việc mới mở worker. Mức thân thiết hướng dẫn cách nói;
quyền thao tác vẫn theo assignment. Spam “keys keys” 67 lần không mở khóa SSH đâu 🦭

### Cài đỡ khổ

Cần Docker Compose, Discord bot token và endpoint model tương thích OpenAI có native
tool calling. Tạo bot ở [Discord Developer Portal](https://discord.com/developers/applications),
bật **Message Content Intent**, invite với `bot` + `applications.commands`, rồi cấp quyền
xem/gửi tin, đọc lịch sử, embed và reaction trong channel m chọn.

```sh
git clone https://github.com/TonyBucket/keys-keys.git
cd keys-keys
docker compose run --build --rm keys-keys setup
docker compose run --rm keys-keys doctor
docker compose up -d
```

Wizard hỏi ngôn ngữ, timezone, token, provider và persona, rồi cho chọn `chat`, Panel,
SSH hoặc plugin bridge. Chưa có server thì chọn `chat`; muốn thêm sau vẫn được. Panel
có danh sách để chọn, SSH có dò thư mục phổ biến; không bắt đi săn UUID qua ba tab.

Việt Nam dùng **Asia/Ho_Chi_Minh**, wizard cho đổi. Model mặc định là
`ag/gemini-3.8-flash-medium` qua 9Router; có thể chọn model khác và kiểm bằng `doctor`.
URL provider phải truy cập được từ container. Localhost trong container là chính nó,
đừng bắt Kei tìm 9Router trong phòng mình rồi đổ tại em nó.

Chưa biết Discord user ID thì để trống owner, lấy mã riêng trong terminal rồi `/setup`
để claim. Token, config, persona và memory nằm riêng trong `data/`, giữ qua lần cập nhật.
Các file prompt/persona/env/test public vẫn trống; wizard tạo **file local của m**.

[Hướng dẫn từng bước](docs/QUICKSTART.md) · [Chọn connector](docs/CONNECTORS.md) ·
[Cài plugin](docs/MINECRAFT.md) · [Nâng từ 2.x](docs/UPGRADING.md)

### Mặc định đáng biết

- Tự xen vào public tắt mặc định; admin bật `free` hoặc whitelist channel.
- Trigger mặc định `kei`, có thể đổi. Mention/reply trực tiếp vẫn dùng được.
- DM chủ động cần opt-in, tối đa ba lần/ngày, cách nhau bốn giờ, có giờ yên lặng.
- Chat thô giữ 90 ngày; episode quan trọng giữ trích đoạn hữu ích tới khi quên.
- `discreet` cho gợi nhắc ít nhạy cảm giữa các ngữ cảnh; không quote DM ra public.
- Người thường chat được. Copilot cần assign đúng server; bước nguy hiểm cần xác nhận.
- Plugin không tự bật lại server đã tắt. Stage JAR xong vẫn cần kiểm plugin thực sự được bật.

### Mấy lệnh dùng hằng ngày

| Lệnh | Làm gì |
|---|---|
| `/server connect`, `/server list`, `/server grant` | Nối Panel riêng tư, xem server, cấp quyền |
| `/link`, `/unlink` | Nối hoặc gỡ danh tính Minecraft |
| `/social dm`, `/social timezone` | Chỉnh mức chủ động và timezone |
| `/privacy`, `/memory show`, `/memory forget` | Xem và quản lý memory |
| `/persona auto/soft/spicy` | Chọn giọng cũ, đậm vị hoặc linh hoạt |
| `/debug off/minimal/advanced` | Chỉnh độ chi tiết tiến độ |
| `/kei <tin nhắn>` trong game | Nói chuyện riêng với Kei |

Ví dụ: “Check TPS với RAM Java server này”; “Đọc anti-xray hiện tại”; “Tìm nguyên nhân
lag, chưa sửa gì”; “Stage plugin tương thích rồi báo lại”; “Nhớ vì sao keys keys thành trò đùa”.

`minimal` hiện objective/checklist trong embed hồng nhạt; `advanced` thêm codeblock
lệnh/log thật. Card được edit gọn. Persona cũ có thể giữ ở `soft`; giao việc không cần dỗ.

### Tài liệu và giới hạn

[Cài đặt](docs/QUICKSTART.md) · [Cấu hình](docs/CONFIGURATION.md) ·
[Kết nối](docs/CONNECTORS.md) · [Minecraft](docs/MINECRAFT.md) ·
[Social/memory/privacy](docs/SOCIAL.md) · [Cập nhật/khôi phục](docs/UPGRADING.md) ·
[Gỡ lỗi](docs/TROUBLESHOOTING.md) · [Changelog](CHANGELOG.md)

Mỗi connector có giới hạn. Plugin-only không bật lại server đã tắt; đăng nhập Panel có
thể cần browser tùy chọn hoặc session đã xác thực. Không hot reload plugin. Một bot token,
một consumer; đừng để hai chị em cùng trả lời một tin rồi hỏi sao nó lắm mồm.

### License và avatar

Code: [MIT](LICENSE). Character/avatar: Tendou Kei, dùng cho fan experiment.
Tên file ảnh được cung cấp ghi credit Manic-san; xem [ghi chú asset](assets/README.md).
MIT áp dụng cho code; quyền nhân vật và artwork vẫn thuộc chủ sở hữu tương ứng.
