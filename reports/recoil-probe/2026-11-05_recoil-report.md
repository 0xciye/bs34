# BloodStrike: các hàm recoil đã xác minh qua Frida

Ngày: 2026-11-05. Phạm vi theo yêu cầu người dùng: attach BloodStrike PID 868, tìm hàm recoil và quan sát lượt gọi; không thay đổi recoil, cấu hình hay runtime gameplay. Không chỉnh sửa bản stable hoặc tự commit kết quả khảo sát này.

## Kết quả

Frida attach thành công. Probe kiểm tra ba chữ ký Python bridge trước khi thực thi. Quét 2.610 module gclient/gshare đang nạp, thu được 93 code object liên quan recoil/roll shake/kickback hoặc hàm gọi chúng. Phiên hiện tại là PlayerCombatAvatarShootingRange, camera placer FpsPlacer. Trace 20 giây dùng sys.monitoring.PY_START cho các code object đã chọn, không thay thế thân hàm, không sửa giá trị trả về hay tham số. Đã tắt toàn bộ local event và giải phóng monitoring tool ID trước khi detach.

### Chuỗi recoil chính

Các tên dưới đây nằm trong `gclient.framework.camera.fps_state_fsm`. Số dòng lấy từ code object đang chạy, không lấy từ bản decompile cũ trên đĩa.

| Hàm | Dòng runtime | Vai trò theo bytecode | Lượt gọi trong trace |
|---|---:|---|---:|
| StateRecoil.OnRecoilEnter(self, shoot_idx=0) | 535 | Lấy pattern + random, thiết lập yaw/pitch và gọi RecoilUp | 62 |
| StateRecoil.RecoilUp(self) | 587 | Gọi cameraEasing.RotateEasing với RecoilYawRange/RecoilPitchRange/RecoilUpTime | 62 |
| StateRecoil.RecoilFall(self) | 598 | Pha fall sau callback up, dùng RecoilFallPct | 61 |
| StateRecoil.RecoilStatic(self) | 615 | Khoảng dừng theo RecoilStaticTime trước pha down | 61 |
| StateRecoil.RecoilDown(self) | 627 | Pha hồi, có nhánh chu kỳ và RecoilRecover | 61 |
| StateRecoil.OnRecoilExit(self) | 644 | Kết thúc trạng thái recoil | 61 |

Đường chuyển pha được đối chiếu từ bytecode của callback: OnRecoilUpCallback → RecoilFall, OnRecoilFallCallback → RecoilStatic, OnRecoilStaticCallback → RecoilDown. OnRecoilDownCallback chuyển FSM về Static. Số lượt có thể lệch vì trace bắt đầu/kết thúc giữa chu kỳ; không coi 62 lượt hàm là phép đo chính xác số đạn đã bắn.

### Pattern và random của vũ khí

Module: `gclient.gameplay.logic_base.equips.weapon_case`.

| Hàm | Dòng | Vai trò | Lượt gọi |
|---|---:|---|---:|
| WeaponCase._UseSpecRecoilData(self) | 3607 | Chọn nhánh dữ liệu spec | 2 |
| WeaponCase._GetRecoilDataByShootIdx(recoil_data, cycle_idx, shoot_idx) | 3624 | Lấy mẫu theo chỉ số phát và chu kỳ | 2 |
| WeaponCase.GetRealRecoilData(self, is_real_ads, shoot_idx=0) | 3635 | Pattern thực, có phân biệt ADS và chỉnh theo talent | 62 |
| WeaponCase.GetRealRecoilRandomData(self, is_real_ads, shoot_idx=0) | 3655 | Biên random yaw/pitch, có nhánh ADS/spec | 62 |
| WeaponCase.GetRealPersistRecoilDownTimeMax(self, shoot_idx) | 3673 | Giới hạn thời gian hồi kéo dài | 0 |

GetRealRecoilData sử dụng cache `_GetShootAttr`/`_UpdateShootAttr`, đọc RecoilData hoặc RecoilDataAds và các biến thể spec, nhân hệ số yaw/pitch, rồi gọi `owner.DealRecoilDataByTalent`. Hàm talent tại `gclient.gameplay.logic_base.entities.combatavatarmembers.cimp_talent.PlayerCombatAvatarMember.DealRecoilDataByTalent`, dòng 22, cũng được gọi 62 lần. Vì cache, số lượt đọc pattern gốc không nhất thiết bằng số lượt GetRealRecoilData.

### Hồi tâm và rung camera

- `StateRecoilRecover.OnRecoilRecoverEnter(self, shoot_idx=0)`, dòng 679; `OnRecoilRecoverCallback`, dòng 696; `EnablePersistRecoilRecover(self, enable=True)`, dòng 700; `OnRecoilRecoverExit`, dòng 710. EnablePersistRecoilRecover có 4 lượt gọi; chưa quan sát các hàm enter/callback/exit của trạng thái hồi kéo dài trong lượt trace này.
- `StateRollShake.OnRollShakeEnter`, dòng 764: 62 lượt; `OnRollShakeTick`: 1.173 lượt; `OnRollShakeExit`: 61 lượt. Đây là nhánh rung camera bổ sung, tách khỏi pha up/fall/down.
- `WeaponCase.GetRealRollShakeInfo(self, is_real_ads, shoot_idx=0)`, dòng 3794: 62 lượt; cung cấp thông tin cho nhánh RollShake.
- `gclient.framework.util.assist_aim_util.AssistAimAndShootTracing.RecoilStart/RecoilEnd` và biến thể NoSearching cũng hiện diện trong metadata; việc tồn tại không tự chứng minh đã được gọi trong lượt trace này.

## Giá trị quan sát tại thời điểm chụp

FpsPlacer ở state Static, shoot_idx=20. RecoilEnable=1.0, RecoilPitchRange≈0.014, RecoilYawRange≈-0.00143463, RecoilUpTime=0.04, RecoilFallPct=1.0, RecoilStaticTime=0.0, RecoilDownTime=0.15, RecoilDownPct=1.0, forcePersistRecoilRecover=False. Đây là một snapshot của vũ khí/trạng thái hiện tại, không phải hằng số chung cho mọi súng.

## Evidence → Finding → Path

| ID | Artifact | Quan sát / kết luận |
|---|---|---|
| E-imports | weapon-metadata.json | Danh sách 241 module vũ khí/camera được chọn ở lần quét đầu; tương đương inventory module cho khảo sát Python, không phải phân tích IAT native |
| E-001 | recoil-metadata.json | Metadata, alias, signature, bytecode disassembly của 93 code object và giá trị FpsPlacer |
| E-002 | recoil-metadata.trace.json | Counter, tối đa 256 event đầu và monitoring_removed=true |
| E-003 | recoil-functions.dis.txt | Bản disassembly dễ đọc, xuất từ E-001 |
| F-001 | E-001 + E-002 | Chuỗi recoil và các hàm lấy pattern được xác nhận bằng bytecode và lượt gọi thực tế |
| F-002 | E-001 + E-002 | Nhánh RollShake chạy cùng recoil, nhưng là nhóm hàm riêng |
| F-003 | E-001 | Các hàm hồi kéo dài tồn tại; chưa đủ bằng chứng về điều kiện kích hoạt trong trace hiện tại |

Path: `WeaponCase.GetRealRecoilData/GetRealRecoilRandomData` → `StateRecoil.OnRecoilEnter` → `RecoilUp` → callback → `RecoilFall` → callback → `RecoilStatic` → callback → `RecoilDown`; điểm gọi thực tế chuyển camera là `cameraEasing.RotateEasing`.

Giới hạn: trace đếm theo code object trong toàn bộ interpreter, không phân tách từng instance hay từng vũ khí. Callback decorator có thể chia sẻ code object; không dùng counter wrapper chung OnRecoilUpCallback để kết luận riêng pha up. Các hàm callback gốc được lấy thêm từ closure để kiểm tra riêng. Chỉ giữ 256 event đầu nhưng counter tiếp tục cộng trong toàn bộ cửa sổ trace. Đây là hàm Python; chưa xác định RVA native của RotateEasing. Các hook/runtime khác đã tồn tại trong game không được tắt hoặc sửa bởi probe này.

## Tái hiện

Từ thư mục bs-cheat, thay PID bằng tiến trình game hiện tại, chọn output mới rồi bắn thủ công ở khu tập bắn:

```powershell
python tools/probe_recoil_frida.py --pid 868 --output reports/recoil-probe/check-next.json --trace-seconds 20
```

Không truyền `--trace-seconds` để chỉ chụp metadata. Probe chỉ dùng Frida đã cài sẵn và bridge được kiểm tra chữ ký. Kết quả JSON tập trung nằm tại `recoil-functions.json`; hash artifact ở `sha256.json`. Kiểm tra sau chạy xác nhận 93 label duy nhất, counter dương, disassembly có nội dung và monitoring đã gỡ.
