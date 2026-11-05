# Blood Strike: sửa skin flow và giao diện

Đã sửa source trong `C:\Users\CiyE\Desktop\bs cheat\bs-cheat`.

## Giao diện

- Menu và loader dùng chung màu than, điểm nhấn tím và font Segoe UI theo mẫu được yêu cầu.
- Dòng mô tả dưới Skins được đặt lại cùng lề với tiêu đề; hai checkbox loader cùng lề. Nguyên nhân là ImGui đưa con trỏ về lề mặc định sau khi xuống dòng.
- Thanh công cụ xuống hàng khi thiếu chỗ; danh sách có vùng cuộn riêng. Tab Knives và Guns dùng nhóm dữ liệu riêng; gun hiển thị bậc và cấp nâng cấp.
- Có nút Reload catalog và tự đọc lại khi file catalog thay đổi.

## Skin flow

- Chỉ sửa các hàm skin trong hai bản runtime `pyexec` và `dist/pyexec`; giữ nguyên các khác biệt không liên quan vốn có giữa hai file.
- Phân biệt template ID và item ID, lọc skin dùng thử, chọn combat avatar và weapon case phù hợp, dùng hàm đổi model thay vì chỉ đổi camo.
- Catalog được dựng lại từ dữ liệu lobby, giữ bậc cao và cấp nâng cấp; không suy đoán gun thành knife.
- Skin nhân vật kiểm tra đúng hero; melee kiểm tra lớp trang bị. Artifact cần các thuộc tính riêng nên không được áp dụng bằng một ID đơn lẻ.
- Thông báo phản ánh yêu cầu cập nhật, không khẳng định thành công khi chưa có bằng chứng hiển thị.

## Kiểm tra

- 20 kiểm thử offline cho mỗi bản runtime: đều đạt. Không import hay chạy toàn bộ runtime.
- MSVC kiểm tra cú pháp cả overlay.cpp và loader.cpp: đạt.
- Dựng và xem ảnh bằng harness chỉ chứa UI, không có thao tác game, driver, hook, IPC hay injection. Đã kiểm tra vị trí checkbox, subtitle và cửa sổ nhỏ 680 × 560.
- So sánh AST xác nhận các phần runtime ngoài danh sách hàm skin không đổi. Các hàm driver/injection của loader và CMakeLists.txt không đổi.

## Giới hạn

Chưa chạy loader thực tế, chưa đóng gói executable mới và chưa kiểm tra đổi skin trong trận. Ảnh preview dùng dữ liệu fixture; không chứng minh hành vi trong game. Kernel mode/anti-cheat bypass không được sửa hoặc chạy.

File cấu hình trên đĩa có version 5 trong khi source dùng version 6; chưa ghi đè cấu hình người dùng. Công cụ update_runtime.py cũ có thể tái tạo runtime từ bản .bak và ghi đè thay đổi nếu được chạy thủ công.

Backup trước sửa: bloodstrike_skin_ui_fix_backup.zip. Manifest kèm SHA-256: bloodstrike_skin_ui_fix_manifest.json. Ảnh: ui-loader.png, ui-knives.png, ui-guns.png, ui-characters.png, ui-small.png.
