# Sửa lag runtime sau build

Ngày 2026-11-05. Theo yêu cầu người dùng, phân tích phiên BloodStrike PID 17520 và sửa đường cập nhật skin gây lag. Giữ các thay đổi tính năng hiện có trong working tree; không khôi phục toàn bộ bản stable và không commit tự động.

## Nguyên nhân và bản sửa

Log runtime ghi nhận tick 300–460 ms ở khối apply/skin, trong khi gather entity khoảng 1–2 ms. Đo riêng các helper tự nhiên trong 5 giây xác nhận `_skin_selection` chiếm 4,469 giây, `_drive_saved_skins` chiếm 4,476 giây. Template đã xóa/không tồn tại trong Inventory không được cache kết quả thất bại, nên quét toàn bộ catalog lặp lại. Inventory cũng tra template cho vũ khí không được trang bị.

- Cache cả kết quả không tìm thấy trong `_skin_selection`; hủy cache khi catalog thay đối tượng hoặc số lượng phần tử. Giữ map ưu tiên cấp upgrade do `_index_item_templates` dựng và gắn revision tương ứng.
- Lọc theo slot súng/dao đang được trang bị trước khi tra template Inventory.
- Bỏ throttle 330 ms mới thêm ở `_drive_saved_skins`: sau khi sửa nguyên nhân, đường kiểm tra đã rẻ và vẫn cần nhận đổi trang bị, đổi phòng, Apply và bật lại auto ngay lập tức. Thời gian thực thi apply task vẫn được giới hạn như trước.
- Sửa biến `t_aim` không tồn tại trong thống kê cuối tick thành khoảng thời gian track đã được tính. Trước sửa log có NameError lặp lại.

Đã thay năm helper trong module runtime đang chạy, giữ thuộc tính cache và cập nhật source tại đường dẫn runtime đang sử dụng. Không khởi động lại toàn bộ runtime, không đổi cấu hình người dùng.

## Kết quả đo

| Chỉ số callback runtime | Trước | Sau |
|---|---:|---:|
| Thời gian đo | 5,006 s | 5,003 s |
| Số callback hoàn thành | 60 | 1.186 |
| Trung bình mỗi callback | 76,65 ms | 1,94 ms |
| Callback chậm nhất | 364,54 ms | 3,82 ms |
| Tổng thời gian tra template | 4,469 s / 179 lượt | 0,072 s / 4.748 lượt |
| Skin driver chậm nhất | 362,60 ms | 0,79 ms |

Đây là thời gian CPU/wall của callback Python dưới profiler nhẹ, không phải phép đo FPS/render GPU. Hai lượt đo trên cùng tiến trình; không bảo đảm mọi bản đồ và số lượng người chơi có cùng kết quả.

## Evidence → Finding → Path

- E-before: `before.json`, đo các helper bằng wrapper chỉ ghi thời gian và trả nguyên kết quả/ngoại lệ.
- E-after: `after.json`, cùng nhóm helper và cửa sổ 5 giây sau sửa.
- E-patch: `patch.json`, danh sách helper thay và hash source.
- Cả hai lượt xác nhận restored=true, mọi sys.monitoring tool ID trống, pending_recoil_probe=false. Wrapper đo đã được gỡ và Frida detach.
- F-001: `_skin_selection` là điểm nghẽn được xác nhận bằng E-before; E-after xác nhận đường nóng giảm xuống dưới 1 ms ở skin driver.
- Path: `_on_story_tick` → `_drive_saved_skins` → `_skin_inventory_targets` → `_skin_selection` → quét catalog khi template không được cache.

`python -m unittest discover -s tests`: 145 passed. Các kiểm thử bổ sung xác nhận missing template chỉ quét một lần, cache bị vô hiệu khi catalog tăng, không tra template vũ khí chưa trang bị, và tick nhanh hoàn thành mà không gặp lỗi thống kê. Các kiểm thử có sẵn về đổi trang bị/chuyển phòng/Apply/auto bật tắt cũng qua.
