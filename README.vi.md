# keys-keys (Project Supernova)

[![Release Candidate](https://img.shields.io/badge/bản_thử-v4.6.0--rc.2-orange)](https://github.com/SEAL-frontier/Project-Supernova/releases) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> **Lưu ý**: Bản `v4.6.0-rc.2` là bản pre-release tự host (release candidate), chưa phải bản release đóng gói chính thức và không cam kết giống hệt 100% bản bot riêng đang chạy trong server nội bộ.

`keys-keys` là con bot Discord kiêm phụ tá quản lý server Minecraft dựng trên kiến trúc Supernova. M tự chạy trên máy hoặc VPS của m, tự cắm API key LLM vào. Vừa để bạn bè trong server tám chuyện nhảm, vừa hỗ trợ soi log, check port, bấm lệnh Pterodactyl hay SSH mà không biến server Discord thành cái group thông báo cứng nhắc.

[English README](README.md) | [Hướng dẫn cài nhanh](docs/QUICKSTART.md) | [Nhật ký thay đổi](CHANGELOG.md)

<p align="center">
  <img src="assets/kei.png" alt="Tendou Kei fan tribute" width="280" />
</p>

*Cảm hứng nhân vật: Tendou Kei (Blue Archive). Đây là dự án fan-made mã nguồn mở độc lập phát hành theo giấy phép MIT; không liên quan hay được bảo trợ bởi Nexon, Yostar hay đội ngũ phát triển Blue Archive.*

---

## Làm ra con bot này làm gì?

Vì vào Minecraft chơi tí rất dễ thành mở panel, SSH, lục ba cái log. Có người bảo server lag là m có thêm nghề, không lương.

Thay vì ngồi trực máy liên tục, `keys-keys` gom việc quản lý và nói chuyện lại một chỗ:
- **Tách rõ việc chat và việc chạy lệnh**: Chat thông thường dùng model nhẹ tiết kiệm tiền (`ag/gemini-3.8-flash-low`), khi nào cần bới log, chạy task phức tạp thì mới gọi model agent (`ag/gemini-3.8-flash-high`). Thích đổi sang model khác trong config lúc nào cũng được.
- **Rõ ràng quyền hạn**: Các tác vụ thông thường đã cấp quyền sẽ tự chạy, nhưng thao tác nguy hiểm bắt buộc người yêu cầu phải bấm xác nhận. Thân với bot đến mấy thì vào server Discord cũng không tự có quyền SSH máy chủ.
- **Kẹp tính toán an toàn**: Có bộ tính toán riêng, tự sinh ảnh công thức toán dạng PNG trả thẳng vào Discord chứ không đoán mò linh tinh. Bot không hỗ trợ xử lý file âm thanh hay video gốc.
- **Dashboard tự host**: Có sẵn giao diện web tối giản đăng nhập qua Discord OAuth cho admin vào chỉnh đồ.

## Điểm mới trên bản v4.6.0-rc.2

- **Chuyển ngữ cảnh worker an toàn**: Chỉ nạp lại tham chiếu ngữ cảnh gần nhất của cùng một người dùng trong cùng phạm vi (tối đa 6 giờ) sang worker mới; dữ liệu lưu trữ chỉ giữ ID/mã băm chứ không copy transcript thô, tự dừng nếu dính lệnh forget hoặc huỷ tác vụ.
- **Giới hạn mạch chat DM**: Mạch chat DM giữ riêng cho từng người dùng; không tự nối ngữ cảnh từ kênh chung sang DM và không xuất dữ liệu hội thoại thô giữa các phạm vi.
- **Dọn dòng chạy tiến trình**: Khi thực hiện lệnh mới trong chuỗi task, bot chỉ xóa dòng text output tạm của lệnh trước đó; toàn bộ card, bill kết quả và tóm tắt cuối vẫn giữ nguyên.
- **Tóm tắt kết quả chuẩn xác**: Card kết quả hiển thị đúng phần tóm tắt thực tế đã lưu, tuyệt đối không tự đánh dấu hoàn thành các bước chưa được kiểm tra.
- **Phản hồi đúng gốc yêu cầu**: Báo kết quả task bám đúng tin nhắn gốc trong cùng kênh bằng cơ chế reply (`replied_user=True`, `parse=[]`) ở đoạn đầu tiên và không ping lặp lại ở các đoạn sau.

---

## Chuẩn bị trước khi chạy

- Python `>= 3.11`
- Một con Discord Bot đã bật **Message Content Intent** trong trang Developer Portal
- Một endpoint API tương thích chuẩn `/v1` của OpenAI có hỗ trợ function calling
- Discord OAuth (chỉ cần nếu m định bật dashboard web)

> Các file mẫu `.env.example`, prompt hệ thống và persona mặc định được để trống. Cấu hình có sẵn các giá trị mặc định để chạy ngay, và lệnh setup sẽ tạo file `data/persona.md` cục bộ dựa trên nội dung bạn nhập chứ bot không tự nhận diện tính cách.

---

## Cách cài đặt

```bash
# 1. Kéo mã nguồn về máy
git clone https://github.com/SEAL-frontier/Project-Supernova.git
cd Project-Supernova

# 2. Tạo môi trường ảo venv
python -m venv .venv
# Trên Linux/macOS:
source .venv/bin/activate
# Trên Windows PowerShell:
# .venv\Scripts\Activate.ps1

# 3. Cài đặt các gói phụ thuộc
python -m pip install -e ".[dev]"

# 4. Chạy trình thiết lập ban đầu
keys-keys setup --config data/config.yaml

# 5. Thêm server quản lý (nhập thông tin trực tiếp)
keys-keys server add --kind panel --config data/config.yaml

# 6. Kiểm tra cấu hình không tốn tiền API
keys-keys doctor --config data/config.yaml --offline

# 7. Khởi động bot
keys-keys run --config data/config.yaml
```

Nếu gõ `keys-keys doctor` mà không có cờ `--offline`, bot sẽ gọi thử một lượt test kết nối tới endpoint LLM và sẽ tốn token thật của m.

### Chạy qua Docker

File Compose đã để sẵn trong repo:

```bash
docker compose run --build --rm keys-keys setup
docker compose run --rm keys-keys doctor
docker compose up -d
```
*Lưu ý: File Docker Compose chỉ mới được kiểm tra cấu trúc file; việc build và chạy container thực tế chưa được kiểm thử toàn diện trên bản thử nghiệm này.*

---

## Các lệnh Discord Slash

Bản public đang có sẵn các cụm lệnh sau:

- `/setup` - Thiết lập bot lần đầu.
- `/tasks`
- `/settings` - Chỉnh cấu hình bot trong server.
- `/server connect`, `/server list`, `/server grant` - Quản lý kết nối server Minecraft và phân quyền.
- `/social dm`, `/social timezone` - Bật/tắt nhắn tin chủ động và chỉnh múi giờ.
- `/privacy`, `/memory show`, `/memory forget` - Xem và yêu cầu bot xoá dữ liệu nhớ tạm của bản thân.
- `/link`, `/unlink` - Liên kết tài khoản người chơi.
- `/persona`, `/debug` - Xem thông tin chẩn đoán kỹ thuật.

---

## Quyền riêng tư & Cấu hình mặc định

- **Tự nghe ngóng (Ambient)**: Mặc định tắt. Khi bật, chế độ lọc kênh có thể tùy chỉnh.
- **Chủ động nhắn tin riêng (Proactive DM)**: Mặc định tắt, người dùng phải tự bật. Khi kích hoạt, mốc cơ bản (mặc định tối đa 3 tin/ngày và cách nhau ít nhất 4 tiếng) sẽ tự điều chỉnh theo mức độ thân thiết và ngữ cảnh. Khung giờ yên tĩnh có thể tự cấu hình (mặc định 22:00 đến 08:00 theo múi giờ `Asia/Ho_Chi_Minh`).
- **Thời gian lưu log**: Dữ liệu chat thô hết hạn sau 90 ngày theo mặc định, còn ký ức ngữ cảnh chọn lọc được lưu lại cho đến khi m dùng `/memory forget`.

---

## Giới hạn và Kiểm thử

### Giới hạn bản Public & Tính năng tạm hoãn

- **Không tự nối mạch khác phạm vi**: Ngữ cảnh chỉ hoạt động trong cùng người dùng và cùng phạm vi; chưa hỗ trợ chuyển ngữ cảnh từ kênh chung sang DM hay trích xuất từ vựng chéo kênh.


Kiểm thử public chạy bằng mock dữ liệu cục bộ và xuất file ảnh tính toán nội bộ, không phụ thuộc vào Discord thật hay server Minecraft thật:

```bash
python -m pytest tests -q --tb=short
```

Các sự cố từ nhà cung cấp LLM (như lỗi HTTP 400, nghẽn quota, hoặc trả về mã HTTP 200 nhưng payload không hợp lệ) không thể tự khắc phục qua vòng retry nội bộ của bot. Trình chẩn đoán sẽ ghi nhận log an toàn mà không in lộ secret token.

---

## Bản quyền

Dự án phát hành theo Giấy phép MIT - xem chi tiết tại file [LICENSE](LICENSE). Phát triển bởi NeuralSeal & TonyBucket.
