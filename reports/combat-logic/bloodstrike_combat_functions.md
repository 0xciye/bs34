# Blood Strike — hàm áp dụng ngoại hình trong trận

Phân tích: 2026-11-04T22:16:38+07:00. Đối tượng: tiến trình BloodStrike.exe PID 18244, Python nhúng 3.14. Phạm vi: [combat_scope.md](combat_scope.md). Flavor: null.

Đã xác định các hàm đổi ngoại hình trong nhánh gameplay và đọc bytecode của chúng trực tiếp từ tiến trình. Skin súng đổi model đi qua WeaponCase.ChangeWeaponGuise; dao đi qua MeleeCase.ChangeWeaponGuise với nhánh riêng cho dao đôi và Artifact. Nhân vật dùng callback thay đổi arm_clothes, đọc cấu hình trang phục rồi reload model và tay. Kết luận về luồng gọi được suy ra từ bytecode và lớp đã nạp; chưa ghi trace thực thi trong một trận và chưa thử áp dụng skin.

## Súng: nhánh đổi model ngoại hình

`WeaponCase.ChangeWeaponGuise(self, guise_id, data_changed=True, need_callback=True, guise_item_id=None, clear_anim=True)`

Vị trí logic: `gclient/gameplay/logic_base/equips/weapon_case.py:4210`. PyFunctionObject `0x2ac3b6e9dd0`; PyCodeObject `0x2ac2bc84ce0`.

- `guise_id` là khóa template, tương ứng `guise.template_id` trong lobby_item_data; `guise_item_id` là ID vật phẩm riêng.
- Cập nhật backup_guise_id khi data_changed, kiểm tra trạng thái model đơn giản và tài nguyên, thoát nếu ID không đổi.
- Cập nhật guise_id trên weapon case/body, làm mới cache/tài nguyên rồi gọi `weapon_body.WeaponBodyIllusion(need_callback)`.
- Làm mới animation cho vũ khí, tay và súng đôi; khi `is_fps_weapon` và `is_in_combat`, cập nhật thông số góc nhìn thứ nhất; cuối luồng làm mới material, bộ đếm hạ gục và các phần liên quan.
- Đây là phương thức của một weapon case, được tái sử dụng ngoài trận. Dấu hiệu quyết định phiên bản trong trận là đối tượng gameplay và các cờ `is_in_combat`, `is_fps_weapon`, `is_tps_weapon`, không chỉ tên hàm.

`WeaponGuiseComponent.WeaponBodyIllusion(self, need_callback)`

Vị trí logic: `gclient/util/gun_skin_util.py:2180`. PyFunctionObject `0x2ac36367690`; PyCodeObject `0x2ac3efd6280`.

Helper này xóa hiệu ứng cũ, khởi tạo guise và gọi InitWeapon để tạo lại các part. Có các nhánh `is_in_combat` / `is_fps_weapon`.

`WeaponCase.ChangeWeaponSkin(self, skin_id, data_changed=True, force_refresh=False)`

Vị trí logic: `gclient/gameplay/logic_base/equips/weapon_case.py:4181`. PyFunctionObject `0x2ac3b6e9d20`; PyCodeObject `0x2ac2bef1ec0`.

Hàm này cập nhật skin_id trên body, charger và các part qua ChangePartSkinRecursively/LoadModelSkin, rồi reset shader material. Đây là nhánh material/camo, khác nhánh đổi model `guise`; không dùng item_id từ danh sách vật phẩm thay trực tiếp vào mọi tham số có chữ skin.

`WeaponCase.ChangeWeaponDecorate(self, skin_id, guise_id, hangings_id, sticker_info)`

Vị trí logic: `gclient/gameplay/logic_base/equips/weapon_case.py:4162`. PyFunctionObject `0x2ac3b6e9c70`; PyCodeObject `0x2ac2beef170`.

Hàm phối hợp gọi ChangeWeaponGuise → ChangeWeaponSkin → ChangeWeaponHangings → ChangeWeaponSticker. Trong nhánh FPS đang cầm và đang trong trận, còn xử lý ADS và RaiseWeapon. Chữ ký không có tham số item_id đơn lẻ.

Nguồn dựng vũ khí trong trận: `AvatarModel.AddWeapon(guid)` đọc `owner.backpack.Get(guid)`, lấy `display_equip_id`, `skin_template_id`, `guise_template_id`, rồi gọi EquipCaseFactory.Create và InitWeapon. Điều này nối luồng render với trang bị trong trận thay vì model ở kho đồ.

## Dao và cận chiến

`MeleeCase.ChangeWeaponGuise(self, guise_id, guise_item_id=None)`

Vị trí logic: `gclient/gameplay/logic_base/equips/melee_case.py:153`. PyFunctionObject `0x2ac395e0880`; PyCodeObject `0x2ac2bea9050`.

Đọc template guise để chọn model, rồi gọi `self.model.ChangePartModel(model_id, self.OnWeaponModelLoad)`. Khi `is_in_combat` hàm trả về sau nhánh model chính; phần cập nhật scabbard phía sau dành cho nhánh ngoài trận. `guise_item_id` có trong chữ ký nhưng bytecode bản này không đọc tham số đó.

`MeleeCase.RefreshModelSkin(self)`

Vị trí logic: `gclient/gameplay/logic_base/equips/melee_case.py:439`. PyFunctionObject `0x2ac395e16f0`; PyCodeObject `0x2ac2bd04390`.

Sau model load, nếu template có gun_skin_part_mat_list thì skin_id được lấy từ guise_id và chuyển sang model.LoadModelSkin. Vì vậy chỉ đổi material không thay thế được bước đổi model.

`DualMeleeCase.ChangeWeaponGuise(self, guise_id, guise_item_id=None)`

Vị trí logic: `gclient/gameplay/logic_base/equips/dual_melee_case.py:169`. PyFunctionObject `0x2ac39547690`; PyCodeObject `0x2ac2bee09b0`.

Dao đôi gọi phương thức lớp cha rồi đổi cả lefthand_melee_model. Cần phân biệt loại case hiện tại; chưa xác minh việc đổi giữa các lớp dao khác nhau chỉ bằng một ID.

`HeirloomCase.ChangeHeirloomAttr(self, blade_attr=None, handle_attr=None, core_attr=None, effect_attr=None, level=None)`

Vị trí logic: `gclient/gameplay/logic_base/equips/heirloom_case.py:1184`. PyFunctionObject `0x2ac39577cc0`; PyCodeObject `0x2ac39522700`.

Artifact dùng thuộc tính blade/handle/core/effect và level; hàm gọi _SetHeirloomAttrs rồi RefreshWeaponAppearanceAttrs. Không có cơ sở coi một item_id của Artifact là đầu vào thay thế cho các thuộc tính này.

`HeirloomCase.RefreshGuiseAppearance(self)`

Vị trí logic: `gclient/gameplay/logic_base/equips/heirloom_case.py:1256`. PyFunctionObject `0x2ac39560040`; PyCodeObject `0x2ac368cf0f0`.

Helper làm mới HeirloomAppearance khi các part đã load, sau đó RefreshModelSkin. Nhánh RefreshModelSkin lấy skin_dict từ GetSkinDictByAttrs rồi gọi weapon_body.LoadModelSkin.

## Nhân vật

`PlayerCombatAvatarMember._on_set_arm_clothes(self, old)`

Vị trí logic: `gclient/gameplay/logic_base/entities/combatavatarmembers/cimp_model.py:469`. PyFunctionObject `0x2ac33e41430`; PyCodeObject `0x2ac33cef1b0`.

Callback tính lại `hero_skin_proto = GetHeroSkinProto()`, gọi ShowModel(), rồi phát ON_PLAYER_COMBAT_ARM_CLOTHES_CHANGED. Tham số `old` là giá trị trước khi đổi thuộc tính, không phải ID skin cần áp dụng.

`PlayerCombatAvatarMember.ShowModel(self)`

Vị trí logic: `gclient/gameplay/logic_base/entities/combatavatarmembers/cimp_model.py:713`. PyFunctionObject `0x2ac33e41c70`; PyCodeObject `0x2ac46c640e0`.

Khi model chưa có: model.Load(GetModelData(), OnLoadModel). Khi model đã có: model.Reload(GetModelData(), OnReloadPlayerModel, use_ready_to_appear=False). Nhánh người chơi có quản lý camera/ADS và các component trước/sau reload.

`CombatAvatarMember.GetModelData(self)`

Vị trí logic: `gclient/gameplay/logic_base/entities/combatavatarmembers/cimp_model.py:185`. PyFunctionObject `0x2ac33e40670`; PyCodeObject `0x2ac46e1a760`.

Trong game_logic, lấy body item qua game_logic.GetDisplayHeroSkinItemId(self.id, default=DEFAULT_SUIT), đối chiếu arm_low_level_skin, rồi lấy model_id từ lobby_item_data và dữ liệu model từ unit_model_data. Như vậy ID đầu vào của danh mục là item_id trang phục, không phải chỉ hero_skin_id hoặc model_id. ShowModel không nhận trực tiếp tham số skin_id.

`CombatAvatarMember.GetHeroSkinProto(self)`

Vị trí logic: `gclient/gameplay/logic_base/entities/combatavatarmembers/cimp_model.py:166`. PyFunctionObject `0x2ac33e40510`; PyCodeObject `0x2ac46e1b3e0`.

Đọc ID trang phục đang hiển thị qua game_logic hoặc arm_clothes[ItemSubType.Suit], dùng GetHeroIdAndSkinId để chuyển thành cặp hero_id/skin_id và tra hero_skin_data. Không có bằng chứng rằng chỉnh một trường cục bộ đơn lẻ sẽ vượt qua nguồn trạng thái đang được game_logic sử dụng.

Chuỗi callback sau reload: PlayerCombatAvatarMember.OnReloadPlayerModel → CombatAvatarMember.OnReloadModel. Khi là FPS avatar, OnReloadModel tải/reload hand_model bằng hand_model_id và OnReloadHandModel; vì vậy model nhân vật góc nhìn thứ ba và phần tay góc nhìn thứ nhất là hai bước riêng.

## Đối chiếu với danh sách ID đã xuất

| Ví dụ | item_id | template_id hoặc khóa nhân vật |
|---|---:|---|
| M4A1 - Lava | 510010010 | guise/template 11199001 |
| Talon Knife - Scythe | 2010000240 | guise/template 11000008 |
| Chainblade - Chainflux | 2010000380 | guise/template 11000015 |
| ZERO - Scarlet | 3001130002 | hero_id 113, hero_skin_id 3 |

Các địa chỉ trong JSON là địa chỉ object Python của phiên chụp, **không phải** địa chỉ native để gọi bằng NativeFunction và không phải offset bền vững. Vị trí tệp/line lấy từ co_filename/co_firstlineno của game, không khẳng định các tệp .py đó tồn tại trên đĩa. Bản cập nhật game hoặc khởi động lại có thể đổi địa chỉ và bytecode.

## Evidence, findings và đường gọi

| E-id | source_ref | repro_command / cách đối chiếu | content_hash |
|---|---|---|---|
| E-code | combat_function_evidence/loaded_code_objects.json | Đọc PyFunctionObject.func_code và các trường PyCodeObject theo debug offsets của phiên; bytecode lưu đủ để giải mã ngoại tuyến | sha256.json |
| E-disasm | bloodstrike_combat_bytecode.txt | Python 3.14 dis.Bytecode trên CodeType tái dựng chỉ để disassemble, không thực thi; metadata ở E-code | theo manifest hàm và sha256.json |
| E-classes | combat_function_evidence/class_inventory.json | Đối chiếu module cimp_model, dictionary lớp và các function_ptr | sha256.json |
| E-target | combat_function_evidence/target.json, imports.json, runtime_info.json | PE x64, import snapshot và cookie xdebugpy; identity tái dùng từ cùng PID và executable của đợt trích trước | sha256.json |

| F-id | severity | evidence_ids | confidence | location | status |
|---|---|---|---|---|---|
| F-gun: đổi model dùng guise, material dùng skin | n/a_re | E-code,E-disasm | high | weapon_case.py:4181,4210 | validated at bytecode level |
| F-melee: thay model có nhánh combat, dao đôi/Artifact có luồng riêng | n/a_re | E-code,E-disasm | high | melee_case.py:153; dual_melee_case.py:169; heirloom_case.py:1184 | validated at bytecode level |
| F-hero: callback trang phục → ShowModel → reload thân và tay | n/a_re | E-code,E-classes,E-disasm | high | cimp_model.py:469,713,276 | validated at bytecode level |

P-gun, path_type=callflow: trang bị backpack trong trận → AvatarModel.AddWeapon → EquipCaseFactory.Create → WeaponCase → ChangeWeaponGuise → WeaponBodyIllusion → InitWeapon/part model → material/animation refresh.

P-melee, path_type=callflow: MeleeCase.ChangeWeaponGuise → ChangePartModel → OnWeaponModelLoad → RefreshModelSkin. Dao đôi bổ sung model tay trái; Artifact dùng ChangeHeirloomAttr → RefreshWeaponAppearanceAttrs.

P-hero, path_type=callflow: arm_clothes callback → GetHeroSkinProto → ShowModel → GetModelData → model.Load/Reload → OnReloadPlayerModel → OnReloadModel → hand_model.Load/Reload.

Timeline: (1) kiểm tra PID vẫn hoạt động; (2) đọc metadata các module gameplay, gom 968 hàm có tên/tham chiếu liên quan; (3) xác định lớp thực thi và caller; (4) đọc 22 code object trọng tâm; (5) giải mã bytecode ngoại tuyến và lưu bằng chứng. Mọi phiên attach đã detach trong finally.

## Giới hạn còn lại

Chưa xác minh bằng trace rằng các hàm này đã chạy trong một trận cụ thể; chưa gọi các hàm áp dụng skin, chưa sửa trang phục, chưa thử đổi đối tượng FPS/TPS đang cầm, chưa kiểm chứng đồng bộ máy chủ hoặc góc nhìn người chơi khác. Tài nguyên skin, lớp trang bị, phiên bản và trạng thái model có thể quyết định nhánh thực thi. Phân tích này xác định hàm và loại dữ liệu theo build đang mở, không chứng minh mọi item_id đều áp dụng được hoặc tồn tại một hàm duy nhất ApplySkin(item_id) cho cả ba nhóm.
