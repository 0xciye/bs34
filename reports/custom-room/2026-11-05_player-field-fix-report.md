# Sửa nhận dạng người chơi và HP tối đa

Ngày: 2026-11-05. Phạm vi: runtime của dự án và phiên BloodStrike PID 17800 theo yêu cầu sửa và kiểm tra custom room/trận thật. Không đổi cấu hình, giao thức IPC, aim hoặc cơ chế nạp DLL.

## Thay đổi

- `_is_combat`: chấp nhận remote có `IsCombatAvatar=True` và lớp/cha bắt đầu bằng `CombatAvatar`; vẫn loại xe và vật thể kỹ năng trước khi xét cờ avatar. Không nhận đối tượng chỉ có HP, team hoặc cờ combat chung.
- `_max_hp`: ưu tiên `cur_maxhp`, giữ fallback hiện có. Snapshot custom cho thấy 225 khác template `maxhp=125`.
- `_local`: khi không có liên kết controlled-avatar rõ ràng, dùng chính `genv.player` nếu đây là combat avatar, trước fallback `genv.avatar`. Mục đích là không lấy self ID/team từ avatar cũ khi chuyển chế độ.
- Bổ sung hồi quy cho remote avatar, team, kỹ năng giả avatar, HP hiện tại và local avatar cũ.

Đã thay đúng ba helper trong runtime đang chạy, không gọi lại startup; cập nhật source runtime tương ứng.

## Kiểm tra và giới hạn

| Kiểm tra | Kết quả | Bằng chứng |
|---|---|---|
| Toàn bộ Python unittest | 143 passed | `python -m unittest discover -s tests` |
| Chạy helper mới trên hai snapshot custom cũ | 7 lượt avatar được nhận; đọc đúng cur_maxhp | fix-snapshot-regression.json |
| Áp dụng helper vào game đang chạy | Thành công trên module m_view_pipeline | fix-lobby-1.json; tên file là nhãn dự kiến, nội dung thực tế là ShootingRange |
| Khu tập bắn trực tiếp | 7 combat avatar, self + 6 bot; xác định 6 đối phương | fix-live-2.json, GameLogicShootingRange |
| Custom room trực tiếp sau sửa | Chờ người dùng vào phòng và spawn | Chưa có bằng chứng sau sửa trong chế độ này |
| Trận thường/rank trực tiếp sau sửa | Chờ người dùng vào trận và spawn | Không dùng kết quả tập bắn thay thế trận thật |

Tái chạy:

```powershell
python -m unittest discover -s tests
python tools/probe_custom_room.py --pid 17800 --output reports/custom-room/check-next.json --runtime-source pyexec/bs_runtime.py
```

Thêm `--apply-fix` nếu cần cập nhật ba helper trong module đã nạp. Probe kiểm tra chữ ký Python bridge, dùng namespace riêng để đánh giá helper và detach sau chụp. Không tự khởi động toàn bộ runtime.

## Evidence → Finding → Path

- E-fix-source: `pyexec/bs_runtime.py` và `tests/test_esp_filters.py`; lệnh unittest phía trên tái hiện hồi quy.
- E-fix-custom: `fix-snapshot-regression.json`, đối chiếu hai snapshot gốc ở báo cáo trước. Đây là kiểm tra trên dữ liệu đã ghi, không phải live custom sau sửa.
- E-fix-live: `fix-lobby-1.json` xác nhận helper đã nạp vào game; `fix-live-2.json` xác nhận phiên tập bắn.
- F-remote: đã xác nhận helper mới nhận CombatAvatarSquadFight từ snapshot, trong khi bộ lọc trước bỏ sót.
- F-hp: đã xác nhận helper mới chọn HP tối đa hiện tại 225 thay cho 125 ở trường hợp đã ghi.
- Path: `genv.space.combat_avatars` → `_is_combat` → `_query_visible_entities`; entity → `_max_hp` → `_serialize_frame_data`; `genv.player` → `_local` → self/team filter.

Kết luận hiện tại: mã và payload đã sửa; kiểm thử hồi quy, dữ liệu custom đã ghi và phiên tập bắn trực tiếp đạt. Chưa xác nhận hành vi/render trong custom room và trận thường/rank sau sửa.
