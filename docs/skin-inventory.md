# Skin Inventory

Đã sửa source trong `C:\Users\CiyE\Desktop\bs cheat\bs-cheat`, không build hoặc chạy phần mềm.

- Thêm tab Inventory sau Characters, Knives và Guns.
- Apply lưu tên, loại, nhóm và ID skin vào `%LOCALAPPDATA%\CiyE\BloodStrike\skin_inventory.bin`. Nếu không có LOCALAPPDATA, dùng thư mục IPC hiện tại. File được ghi tạm rồi thay thế nguyên tử.
- Chỉ giữ skin đang equip cho mỗi nhân vật/nhóm vũ khí, không lưu history. Bấm tên skin hoặc Apply ở Characters, Knives, Guns sẽ thay lựa chọn cùng slot và lưu ngay. Khi đọc file cũ, bỏ các dòng history không active.
- Inventory dùng chung ô tìm kiếm, chỉ có Remove. Xem được dữ liệu đã lưu kể cả lúc catalog chưa tải. Remove ngừng tự áp dụng lựa chọn đó; không hoàn tác ngay model đang hiển thị trong trận.
- Giữ công tắc Auto apply saved skins. Khi bật, runtime đọc Inventory, chờ đúng combat avatar và trang bị tương thích rồi đưa yêu cầu vào hàng đợi. Đổi trận, qua sảnh, vào phòng tập, đổi hero hoặc tạo thêm weapon case sẽ làm mới hàng đợi. Nếu nhiều nhóm dao cùng tương thích, lựa chọn gần nhất được ưu tiên.
- File tồn tại nhưng rỗng sẽ không lấy lại các ID cũ trong cfg. File hỏng được báo lỗi và giữ nguyên, không ghi đè bằng mặc định. Chuyển ba lựa chọn cũ sang Inventory khi chưa có file và catalog đã tải.

## Kiểm tra

40 kiểm thử offline đạt cho mỗi bản runtime chính và dist. Bao gồm đọc lại sau khi khởi tạo reader mới, lịch sử/active slot, nhiều súng và nhân vật qua hàng đợi, chờ trang bị, chuyển trận → sảnh → training mô phỏng, đổi space với avatar tái sử dụng, xung đột dao, tệp rỗng/hỏng và bật lại auto apply.

Kiểm tra AST xác nhận runtime chỉ thay ba hàm Inventory mới và `_drive_saved_skins`; các phần không liên quan giữ nguyên. C++ chỉ đổi phần UI skin và thêm helper lưu/đọc Inventory. Detector UI không báo vấn đề.

Chưa biên dịch C++, render giao diện hoặc xác nhận hành vi trong game thực tế. Kiểm thử transition dùng đối tượng giả lập, không phải bằng chứng phòng tập đã chạy thành công. Các hạn chế áp dụng skin trước đó vẫn còn: cần resource/model sẵn có, đúng hero và lớp melee tương thích; Artifact không hỗ trợ bằng một ID đơn lẻ.

Không tạo/ghi file Inventory thật của người dùng trong lúc sửa source. Không thay đổi loader, driver hoặc luồng khác. Công cụ update_runtime.py cũ có thể tái tạo runtime từ .bak và ghi đè các thay đổi nếu được chạy thủ công.

Tệp đã sửa: src/overlay.cpp, pyexec/bs_runtime.py, dist/pyexec/bs_runtime.py, tests/test_skin_flow.py; cập nhật DESIGN.md ở thư mục dự án ngoài.

Backup: skin_inventory_before.zip. Diff: skin_inventory_changes.diff. Manifest và schema: skin_inventory_manifest.json.

## Catalog dao và cấp súng (2026-11-05)

Đối chiếu danh sách 52 dao: 48 dao thường đã qua bộ lọc, bổ sung 4 Artifact subtype 210 (Fireborn, Nexus, Pivot, RAZE). Nhóm Artifacts hiển thị tham khảo; chưa cho Apply vì runtime cần cấu hình blade/handle/core/effect.

Súng dùng nhóm gốc trong lobby_item_upgrade_data, chỉ hiển thị cấp cao nhất hợp lệ và vĩnh viễn của từng skin. Không gộp theo tên; giữ các ánh xạ template cũ để đọc lựa chọn đã lưu. Hai bản runtime dùng cùng quy tắc.

Kiểm tra lần này: 45 ca offline cho mỗi bản runtime; đối chiếu catalog dao với dữ liệu cục bộ đủ 52/52 (template giả lập cho kiểm tra lọc). Chưa build EXE hoặc kiểm tra trong game.
