# BloodStrike: người chơi, team, HP và vị trí trong custom room

Ngày phân tích: 2026-11-05. Phạm vi: phiên BloodStrike PID 17800, theo yêu cầu người dùng. Flavor: null.

Đã chụp hai snapshot trực tiếp qua Python bridge có kiểm tra chữ ký, không thay đổi thuộc tính gameplay hoặc cài hook. Snapshot đầu có 3 combat avatar/11 entity; snapshot sau có 4 combat avatar/16 entity. Đây là xác nhận đường truy cập thuộc tính Python, không phải phát hiện offset native mới của HP/team. Các trường native trong `fields.json` được trích từ SDK có timestamp trùng EXE trên đĩa; chưa kiểm chứng layout bằng đọc đối tượng native.

## Kết quả đã xác nhận

| Dữ liệu | Đường truy cập | Quan sát |
|---|---|---|
| Danh sách chiến đấu | `genv.space.combat_avatars` | dict, 3 rồi 4 phần tử |
| Entity tổng | `genv.space.entities` | dict, gồm cả đối tượng không phải người chơi |
| Người chơi hiện tại | `genv.player` | Chuyển từ PlayerCombatAvatarSquadFight sang ReplayCombatAvatarSquadFight |
| ID | `entity.id` | Chuỗi định danh |
| Team | `entity.combat_team_id` | Chuỗi định danh; `team_id` không tồn tại trên các avatar đã chụp |
| HP | `entity.hp`, backing `entity.server_hp` | Khớp nhau trong cả hai snapshot |
| HP tối đa hiện tại | `entity.cur_maxhp` | Có trường hợp 225 trong khi `maxhp=125` |
| Vị trí | `entity.position`, alias `entity.pos` | Ba tọa độ hữu hạn, hai thuộc tính khớp nhau |
| Giáp | `entity.armor`, backing `entity.server_armor` | Quan sát 0 hoặc 50 |

Snapshot đầu: người chơi hiện tại HP 125/125, giáp 50, vị trí (-171.8693, 39.5878, 136.1762). Một đối phương có HP 189/225. Hai đối phương thuộc `CombatAvatarSquadFight`, có `IsCombatAvatar=True` nhưng `IsPlayerCombatAvatar=False`, `IsRobotCombatAvatar=False`, `IsDummyCombatAvatar=False`.

`bs_runtime.py::_is_combat` hiện chỉ chấp nhận các cờ kiểu người chơi/bot cụ thể, nên các avatar đối phương nói trên bị loại. `_max_hp` chưa thử `cur_maxhp`, nên có thể đọc 125 thay vì 225. Đây là phát hiện để tích hợp tiếp; lần này không sửa runtime hay build loader.

Snapshot sau ghi nhận HP 141 trong khi `cur_maxhp=125`; không áp đặt điều kiện HP luôn nhỏ hơn HP tối đa vì dữ liệu client có thể cập nhật lệch thời điểm. Không suy ra ý nghĩa enum `combat_state` từ giá trị số đơn lẻ. Khi replay xuất hiện, không coi `genv.player` là danh tính người chơi gốc một cách vô điều kiện.

## Offset native có sẵn trong SDK

| Lớp | Trường | Offset |
|---|---|---|
| IGameplay | Player | 88 |
| ClientPlayer | Camera | 3464 |
| ClientPlayer | PrincipleRole | 3544 |
| IEntity | Transform | 88 |
| IEntity | Level | 144 |
| IEntity | World | 152 |

Offset ở bảng này là số thập phân, tương đối với đối tượng native tương ứng. Không cộng trực tiếp vào `id(entity)` của Python wrapper. `Transform` là Matrix4x3; chưa xác minh layout translation, vì vậy không đưa ra offset XYZ suy đoán. Không có offset native HP/team đã kiểm chứng trong lần này.

## Bằng chứng → kết luận → đường truy cập

| ID | Bằng chứng | Kết luận / đường truy cập |
|---|---|---|
| E-001 | snapshot-20261105-1.json | 3 avatar, giá trị HP/team/position và cờ kiểu đối tượng |
| E-002 | snapshot-20261105-2.json | 4 avatar; genv.player đổi sang replay; HP thay đổi |
| E-003 | entities/gclient.gameplay.logic_base.entities.combatavatarmembers.cimp_combat_unit.py:205,220–225 | Khai báo combat_team_id, server_hp và property hp |
| E-004 | entities/gclient.framework.entities.space.py:1207 | Space.enter đưa IsCombatAvatar vào combat_avatars |
| E-005 | entities/gclient.gameplay.logic_base.comps.avatar_scene_node.py:948 | UI game dùng owner.cur_maxhp cho thanh HP |
| E-imports | imports.json | Import PE: bcrypt/CRYPT32 cho crypto; WS2_32/MSWSOCK/WLDAP32 cho mạng; KERNEL32 gồm file/process; ADVAPI32 gồm registry. Chỉ phân loại API có sẵn, không kết luận hành vi được thực thi |
| F-001 | E-001 + E-004 | Đã xác nhận đường genv.space → combat_avatars.values() → combat_team_id/hp/position |
| F-002 | E-001 + E-005 | Đã xác nhận cur_maxhp khác maxhp; ưu tiên cur_maxhp khi tích hợp |
| F-003 | E-001 + runtime _is_combat | Đã xác nhận bộ lọc hiện tại không nhận remote CombatAvatarSquadFight đã chụp |

SHA-256 các artifact JSON nằm trong `sha256.json`. Hai snapshot được kiểm tra count, kiểu team/HP, hp==server_hp, position==pos và tọa độ hữu hạn. Dữ liệu chỉ đại diện entity client đã nhận, không bảo đảm bao phủ toàn bộ người trong phòng hay cả bản đồ.

## Tái hiện

Chạy từ thư mục dự án, thay PID bằng tiến trình hiện tại và chọn tên output mới:

```powershell
python bs-cheat/tools/probe_custom_room.py --pid 17800 --output bs-cheat/reports/custom-room/snapshot-next.json
```

Probe dùng thư viện Frida đã cài sẵn, attach thông thường và detach khi xong; không chạy cmd.py hay bs_runtime.start(). Probe dừng nếu chữ ký Python bridge không khớp. Mỗi snapshot là một lần đọc tuần tự, không phải giao dịch nguyên tử của trạng thái trận đấu.
