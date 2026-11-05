# Hoàn thiện đường hiệu ứng skin

Ngày 2026-11-05. Người dùng yêu cầu hoàn thiện hiệu ứng skin, đặc biệt vệt đạn nếu skin có; sau đó xác nhận đã đủ và yêu cầu build. Phạm vi: hiệu ứng hiển thị phía client, giữ dữ liệu mạng/entity gốc và các thay đổi tính năng đang có trong working tree.

## Thay đổi

- Làm mới cả guise_item_id, extra.guise_item_id, cache hiệu ứng, InitFpsProperty và racer khi áp dụng skin. Trường hợp model không đổi vẫn sửa metadata/cờ hiệu ứng; tránh nạp lại liên tục khi trạng thái đã đúng.
- Hai cached property show_guise_bullet_trace/show_guise_hit_effect ban đầu đọc display_guise_item_id của vũ khí từ server, nên vẫn trả False dù model đã được đổi. Getter mới dùng item/template đã áp dụng trên đúng case được đánh dấu, đúng người chơi và đúng space; case khác giữ getter gốc.
- Chỉ bật hiệu ứng khi item_feature_data và gun_skin_template_data có dữ liệu tương ứng. Giữ FPS/ADS/TPS tracer, hiệu ứng trúng từng vật liệu và hiệu ứng nòng do game cung cấp; không tạo ID thay thế cho skin không có hiệu ứng.
- Kill feed nhận bản sao packet với item/template skin của local caster và đúng weapon. Packet gốc, điểm số và thông tin người chơi khác giữ nguyên.
- Renderer AvatarModel.PlaySkinDeadAnimAndEffect dùng bản giải mã riêng cho một lần render để chọn kill_fx, vật liệu tan biến và biến thể team-kill của skin; không ghi đè final_kill_info được replicate hay thay pickle.loads toàn cục.
- Callback KillAvatar/KnockDownAvatar của local player dùng đúng item skin khi game kiểm tra âm thanh và hiệu ứng trên màn hình. Giữ nguyên kết quả callback gốc.
- Binding không giữ các space cũ khi chuyển phòng. Lỗi lúc làm mới không được đánh dấu thành công, để lần sau thử lại.

## Kiểm chứng

E-before: current-effect-state-main-thread.json cho thấy M4A1 đang có guise_id=11100018 và guise_item_id=5100000950 nhưng hai cờ tracer/hit đều False. E-after: installed-effects-2.json ghi nhận cùng skin sau sửa có hai cờ True, 10 cấu hình hit material, new_fire_sfx_id=818 và new_fire_ads_sfx_id=819. Việc áp dụng và đọc trạng thái này thực hiện trên callback engine, không gọi API engine từ luồng Frida.

F-001: sự khác nhau giữa case.guise_item_id và getter dựa trên display_guise_item_id giải thích thiếu vệt đạn/trúng đích. Bằng chứng getter nằm ở effect-gates-targeted.json. Path: Apply skin → _skin_fx_bind → ClearGuiseItemCache/InitFpsProperty → cached property của case → gshare.effect_util.PlayBallisticEffect.

F-002: metadata của kill feed và renderer được xác minh ở function-metadata.json và functions.dis.txt. Path hiển thị: packet caster/weapon → _skin_fx_info → PushKillRecord; final_kill_info → decoder riêng của một render call → PlaySkinDeadAnimAndEffect → PlaySkinDeadEffect/PlayKillTeamAnim. Sự hiện diện của tài nguyên không tự chứng minh mọi biến thể đã tải DLC hoặc đã được thử trong trận.

Người dùng xác nhận “đã đủ” trước yêu cầu build cuối. Không suy diễn thành đã kiểm tra trực tiếp mọi skin trong catalog. Deathbox cosmetic riêng vẫn được phân biệt với kill-team extra model; use_dynamic_box là model bounding box, không phải loot crate.

154 unittest đã qua. Hồi quy bao gồm sửa metadata khi model không đổi, tracer/hit theo skin, skin không có tracer, lọc đúng local caster/weapon/space, giữ packet gốc, team-kill không bị tự tạo, decoder render không sửa entity hoặc pickle toàn cục, callback âm thanh và thử lại sau lỗi tải tài nguyên.
