<div align="center">

<img src="assets/kei.png" alt="Tendou Kei, chỉnh kính và phán xét cái repo này" width="160" height="160" />

# keys-keys 🗝️🗝️

**An open-source Adaptive Hybrid Minecraft Server Copilot**

*Her server. Your problem.*

Thực ra là her problem, your server. Bọn t chia quyền nuôi server hơi lỗi. 😭

![Version](https://img.shields.io/badge/version-4.6.1-EFA5A5?style=flat-square)
![Architecture](https://img.shields.io/badge/architecture-Supernova-aca9e8?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab?style=flat-square)
[![MIT](https://img.shields.io/badge/license-MIT-efa5a5?style=flat-square)](LICENSE)

[English](README.md) · [Tiếng Việt](README.vi.md) · [Setup](docs/QUICKSTART.md) · [Changelog](CHANGELOG.md)

</div>

## Project này là gì?

**keys-keys là AI companion tự host trên Discord kiêm copilot cho Minecraft server.**
M có thể trò chuyện với ẻm qua DM, channel Discord hoặc qua bridge Minecraft tùy chọn.
Admin được assign có thể nhờ ẻm soi TPS/RAM, điều tra lag, đọc config, quản lý plugin
và chạy lệnh server. Trò chuyện dùng model chat riêng; làm việc server chạy loop tool
riêng biệt, có lưu tiến độ và bằng chứng thực thi hẳn hoi.

M tự chuẩn bị Discord token, endpoint model tương thích OpenAI và persona. Bot chạy
trên máy m hoặc VPS. Cứ bắt đầu bằng chat chay trước, khi nào cần thì nối Panel, SSH,
thư mục server local hoặc Minecraft bridge. Một bot gánh được nhiều người và phân quyền
từng server riêng biệt.

## Vì sao có project này?

Vì câu “vào game quẩy tí” kiểu gì cũng thành bật panel, mở SSH, lục ba cái file log,
soi config với lướt trang release của plugin. Ai đó kêu “server lag” một phát là m có
ngay job thứ hai. Không lương, dĩ nhiên rồi. 🥀

Bọn t muốn một nhân vật **vừa ngồi tám cùng nhóm, vừa xắn tay làm việc server khi được nhờ**,
ngay trong một mạch chat. Tám nhảm thì phải ra tám nhảm. Nhờ vả việc server thì phải biết
điều tra, chạy thao tác đúng quyền và trả về kết quả tử tế—chứ không phải hứa giúp cho sang
rồi nằm im re.

**Supernova** tách riêng hai nhánh đó nhưng vẫn giữ liền mạch danh tính, memory và quyền
hạn server. “Adaptive” là tự chọn kiểu xử lý phù hợp; “hybrid” là tận dụng đúng các kết
nối server đang thực có. Mở mã nguồn là để m tự vác về chạy với server, model và nhân vật
của riêng m. Bọn t lỡ đưa cho Tendou Kei một cái Minecraft server thay vì một buổi chiều
yên bình. Chắc điều này giải thích được vài thứ. 😭

> **Bản 4.6.1 là bản phát hành chính thức (stable public release), không phải candidate.** Tự host chạy thế nào còn tùy vào model, quyền connector và cấu hình của m. Repo này không copy nguyên xi bản host nội bộ hay quy định cộng đồng riêng của ai cả. Chi tiết thay đổi xem ở [CHANGELOG](CHANGELOG.md).

### Sao lại tên keys-keys?

Tên ẻm là **Kei**. Có đứa cứ thích gọi trêu thành **keys** cho ẻm cáu. Giờ thì cái typo đó
thành tên cả cái repo luôn. Cách đặt tên chấm hỏi thật sự, nhưng độ nhây thì mười điểm. 🥀

Nhân vật/avatar thử nghiệm là **Tendou Kei**. Persona là do m tự viết; mấy file persona
mẫu đi kèm cố tình để trống. Đây là fan project, không phải sản phẩm chính thức của Blue Archive.

## Nó làm được gì

| Trò chuyện | Minecraft copilot |
|---|---|
| Nhận diện tên, nickname, ngữ cảnh lịch sử phân vùng và quan hệ | Soi TPS/MSPT, JVM memory, player, log và plugin |
| Trả lời, đáp ngắn, thả reaction hoặc im lặng | Soi → lên kế hoạch → làm → kiểm chứng → tinh chỉnh |
| Memory chọn lọc và giữ trích đoạn gốc, không nhai lại mọi câu chào mãi mãi | Task bền vững, hành động được lưu và tiến độ cô đọng |
| DM chủ động (phải opt-in) kèm khung giờ yên lặng tùy chỉnh | Backup/đọc lại config, stage plugin và phân tích profiler |
| Liên kết tài khoản Discord/Minecraft đã xác thực | Phân quyền server theo từng người và bắt xác nhận bước nguy hiểm |
| Đọc ảnh, tra cứu web kèm nguồn và công cụ tính toán giới hạn | Tương thích Panel/Wings, SSH, file local hoặc tính năng bridge |

Những lựa chọn trò chuyện gần đây có thể theo cùng một người yêu cầu sang worker thay vì
bắt nó đi mò mẫm cái “template” m vừa nhắc tới. Quá trình bàn giao này có giới hạn và được
kiểm tra nguồn chặt chẽ; nó không tự cấp thêm quyền phá server đâu. Card task sẽ hiển thị
kết quả đã lưu, và việc bắt đầu một lệnh mới sẽ xóa output trực tiếp của lệnh trước—chứ
không xóa bằng chứng việc đó đã từng được thực thi.

Phần toán học nằm trọn bên nhánh chat. Một công cụ tính toán có giới hạn sẽ lo phần ra số,
và bộ render công thức local có thể gửi file PNG thật chèn giữa các tin nhắn text. Đây không
phải model vẽ ảnh, không phải sandbox chạy code đa năng, và cũng chẳng chứng minh là cái
Minecraft bridge gửi được ảnh đâu nhé.

```text
Discord / Minecraft
        ↓
danh tính + ngữ cảnh được phép + memory liên quan
        ↓
hội thoại ─── trả lời / reaction / im lặng
        ↓ chỉ khi có yêu cầu việc server
copilot ─── soi → lên kế hoạch → làm → kiểm chứng
        ↓
connector đã cấu hình + bằng chứng thực thi được lưu
```

Mức độ quan hệ chỉ đổi cách ẻm nói chuyện, tuyệt đối không đổi server nào ẻm được đụng vào.
Không có chuyện cày độ thân mật để bypass quyền SSH đâu. Khôn như m quê t đầy. 🦭

### Nhờ ẻm chuyển lời

Cứ dùng chat bình thường để nhắn một ý chọn lọc, gửi kèm link hoặc trích dẫn ảnh/file muốn chuyển cho đúng người, nhờ ẻm hỏi giùm rồi mang câu trả lời về, hoặc tự gửi báo cáo/nhắc nhở qua DM.
Mention, user ID, username hoặc server nickname có sẵn đều dùng để chỉ định người nhận
được; tên mà mơ hồ thì ẻm sẽ hỏi lại cho rõ chứ không có chuyện DM bừa bãi.

M có thể hẹn giờ, đợi một task chạy xong, hoặc chờ lần tới người đó chủ động nói chuyện
với Kei. Đây không phải công cụ rình người ta online. Tin chưa gửi có thể sửa hoặc hủy;
người nhận có quyền hoãn lại hoặc từ chối. Lời đáp mặc định gửi về riêng tư, và việc chọn
nơi gửi không bao giờ làm lộ lịch sử chat riêng tư không liên quan. Không có trò đẻ card
ticket hay thông báo giao hàng ép buộc đâu.

## Bắt đầu ở đây

**Hai lối vào trên Discord. Không bày một đống slash command rác mắt.**

- **`/settings`** mở bảng điều khiển riêng tư: setup, persona, memory/privacy, profile quan hệ,
  liên kết tài khoản, lịch trình, tùy chọn hiển thị tiến độ và kết nối Minecraft.
- **`/server`** mở menu kết nối Minecraft. Soi các server được assign/hiển thị và dùng các nút
  quản lý liên quan; các nút bấm chỉ nhận lệnh từ đúng người đã mở menu.

Cứ dùng câu từ tự nhiên để hỏi han và giao việc. M không cần phải học thuộc mấy họ lệnh cũ
như `/social`, `/memory`, `/link`, `/debug` hay `/server connect` nữa; các nút chỉnh của
chúng nằm gọn trong menu rồi. Lệnh bridge tùy chọn `/kei <tin nhắn>` trong Minecraft là giao
diện khác nhé.

Ví dụ:

> “Cho xem config anti-xray hiện tại cái.”
>
> “Tìm xem vì sao TPS tụt đi. Đừng sửa gì vội đấy.”
>
> “Stage plugin này trước đi, khoan hẵng restart.”
>
> “Nhớ giùm vụ vì sao keys keys thành trò đùa nha.”

[Discord + Web UI](docs/SETTINGS.md) · [Lịch trình](docs/SCHEDULED_TASKS.md) ·
[File local không cần SSH](docs/LOCAL_ACCESS.md) · [Cài đặt bridge](docs/BRIDGE_INSTALL.md)

## Cho ẻm online

Cần Python **3.11+**, một Discord application/token đã bật **Message Content Intent**,
và một endpoint model hỗ trợ native function calling. Với Discord, cấp quyền vào đúng
channel cần dùng và các quyền gửi tin, đọc lịch sử, nhúng link, đính kèm file và thả reaction.
Quyền của connector được cấu hình riêng; role trên Discord không phải là thông tin đăng nhập server.

```sh
git clone https://github.com/SEAL-frontier/Project-Supernova.git
cd Project-Supernova
python -m venv .venv

# Linux / macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1

python -m pip install -e ".[dev]"
keys-keys setup --config data/config.yaml
keys-keys doctor --config data/config.yaml --offline
keys-keys run --config data/config.yaml
```

Wizard sẽ hỏi ngôn ngữ, timezone, token, provider và persona, rồi cho m chọn chỉ chat thôi
hoặc cấu hình luôn connector server. Ở Việt Nam thì chọn **Asia/Ho_Chi_Minh**.
Chạy `doctor` online—không kèm `--offline`—sẽ ping tới các dịch vụ đã cấu hình và có thể tốn
token model. Bản check offline chỉ kiểm tra cài đặt cục bộ chứ không chứng minh kết nối mạng thông suốt.

Base URL của provider là đường dẫn **`/v1`** của endpoint, không phải trang web đăng nhập.
Model ID cho chat và agent chỉnh riêng được. Mặc định kèm theo dùng Gemini Flash Low cho chat
và Flash High cho việc; m có thể gán cả hai vai trò vào cùng một model phù hợp. Tính năng hỗ trợ
ra quyết định tắt mặc định. Đây là các mặc định tự host, không đảm bảo provider nào cũng nuốt chung
một schema hay model ID.

Secret, persona sinh ra, config và memory nằm gọn trong thư mục `data/` của m.
Nhớ giữ kín và backup trước khi update. File `.env.example` public và mấy file persona mẫu cố tình
để trống; chúng không phải nhân vật hay thông tin đăng nhập có sẵn để đi copy từ máy người khác.

### Thích dùng Docker hơn?

Repo có sẵn đồ nghề Docker Compose:

```sh
docker compose run --build --rm keys-keys setup
docker compose run --rm keys-keys doctor
docker compose up -d
```

URL provider phải truy cập được **từ bên trong container**. `localhost` đứng trong container
là chính cái container đó, chứ không phải dịch vụ model chạy ngoài máy host đâu. File Compose
được cấp sẵn; việc build/chạy container được nghiệm thu tách biệt với test Python offline.

[Quick start đầy đủ](docs/QUICKSTART.md) · [Chọn connector](docs/CONNECTORS.md) ·
[Cấu hình](docs/CONFIGURATION.md) · [Nâng cấp và khôi phục](docs/UPGRADING.md)

## Mặc định đáng biết

- Tự hóng chuyện public tắt mặc định; được gọi đích danh hoặc cho phép tiếp lời khác với việc ngồi nghe trộm cả channel.
- Tên gọi mặc định là `kei`. Mention/reply và các tên cấu hình thêm đều nhận.
- DM chủ động phải opt-in. Cài đặt hàng ngày và khoảng cách giờ là kiểm soát theo ngữ cảnh, không ép bot phải nặn ra tin nhắn; giờ yên lặng và việc người kia chưa trả lời vẫn được tôn trọng.
- Chat thô giữ mặc định 90 ngày. Các episode được chọn có hạn lưu riêng; cài đặt privacy có thể xóa nguồn tương ứng.
- `strict` giữ memory tách bạch theo vùng; `discreet` có thể mang theo gợi ý an toàn được phép. Không chế độ nào đem chat riêng tư thô đi bêu rếu chỗ khác.
- Việc server đòi hỏi phân quyền/năng lực thực tế. Chế độ Observe không thể sửa server; lệnh được duyệt chạy bình thường, bước nguy hiểm bắt buộc xác nhận.
- Plugin Minecraft không thể tự bật một server đang tắt. File JAR nằm trong staging chưa phải plugin đã chạy. Lệnh được nhận không đồng nghĩa kết quả đã được kiểm chứng.

## Web dashboard

Giao diện web tùy chọn là dashboard có xác thực với khung đăng nhập Discord OAuth tối giản—không
phải trang web giới thiệu hào nhoáng của dự án. Nhớ cấu hình OAuth trước rồi hẵng mong đăng nhập
được. Nút bấm hiện trên web không thay thế được bước check quyền dưới backend đâu.

## Phát triển và giới hạn

```sh
python -m pytest tests -q
python -m pip wheel . --no-deps --wheel-dir dist
```

Test public dùng mock giả lập ranh giới Discord/model, data tạm và file PNG local thật.
Chúng không phải nghiệm thu trên Minecraft sống, không test notification client Discord hay Docker.
Bot chưa có tính năng hiểu video/audio trực tiếp. Xử lý lỗi local không thể tự sửa hết mọi lỗi
HTTP upstream, kiểm duyệt từ provider hay quả HTTP 200 rỗng tuếch không có text.

Cài đặt gặp lỗi thì cứ nghía qua [Troubleshooting](docs/TROUBLESHOOTING.md) trước. Xem
[Social/memory/privacy](docs/SOCIAL.md) và [Minecraft](docs/MINECRAFT.md) để biết chi tiết hành
vi và connector. Muốn mở issue hay PR thì nhớ kèm các bước tái hiện ngắn gọn, và nhớ xóa sạch token,
persona, chat nhạy cảm lẫn IP server khỏi log trước khi quăng lên.

## License và avatar

Code: [MIT](LICENSE), phát triển bởi **TonyBucket / NeuralSeal**. Nhân vật/avatar:
Tendou Kei, fan project phi chính thức. Tên file art đi kèm ghi công Manic-san; xem
[ghi chú asset](assets/README.md). License của code không cấp phép lại cho nhân vật hay hình vẽ,
và project này không liên kết với bên nắm giữ bản quyền gốc.
