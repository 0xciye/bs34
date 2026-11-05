# Phạm vi phân tích hàm gameplay

auth: Yêu cầu người dùng: tìm hàm áp dụng skin nhân vật/dao/súng ngay trong trận, không phải kho đồ.
in_scope: Tiến trình BloodStrike.exe PID 18244 tại thư mục cài đặt đã chỉ định; các code object Python đã nạp cho gameplay và các helper render.
network_profile: local-only.

Đọc metadata và bytecode qua Frida; giải mã ngoại tuyến. Không gọi hàm đổi skin, không sửa trạng thái nhân vật/vũ khí, không gọi RPC máy chủ. Không giả định quyền sở hữu hoặc khả năng áp dụng mọi skin.
