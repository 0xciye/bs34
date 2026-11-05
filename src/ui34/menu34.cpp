// 34Cheat-style D2D menu wired to bs-cheat's real Cfg + F_* flags.
// Each toggle/slider/combo reads and writes g_cfg directly; g_cfg_dirty is
// set so overlay.cpp's save loop flushes to ipc/cfg.bin.
#include "menu34.hpp"
#include "../bs_cfg.hpp"
#include "../skin_bridge.hpp"
#include <string>
#include <vector>
#include <algorithm>
#include <cwctype>

namespace Menu34 {

    namespace {
        constexpr float kCardPad = 16.0f;
        constexpr float kRowGap = 34.0f;

        // u32 color (packed RGBA, little-endian, as ImU32) <-> Config::Color4 (0..1 floats).
        Config::Color4 Unpack(uint32_t rgba) {
            float r = ( rgba        & 0xFF) / 255.0f;
            float g = ((rgba >>  8) & 0xFF) / 255.0f;
            float b = ((rgba >> 16) & 0xFF) / 255.0f;
            float a = ((rgba >> 24) & 0xFF) / 255.0f;
            return {r, g, b, a};
        }
        uint32_t Pack(const Config::Color4& c) {
            auto q = [](float v){ int x = (int)(v * 255.0f + 0.5f); return (uint32_t)std::clamp(x, 0, 255); };
            return q(c.r) | (q(c.g) << 8) | (q(c.b) << 16) | (q(c.a) << 24);
        }

        // Sub-tab index for Skins (local to UI, not persisted).
        int g_skin_page = 0;
        std::wstring g_skin_search;

        // Settings tab's menu-side theme (persisted only inside Config::g_Config).
        int g_theme_index = (int)Config::AccentTheme::CyberpunkCyan;

        void CardTitle(float x, float y, const std::wstring& title, const std::wstring& sub = L"") {
            auto& ui = UI::g_UI;
            const auto& c = ui.GetColors();
            ui.DrawText(title, {x, y}, {280.0f, 20.0f}, c.TextPrimary, UI::FontHeader);
            if (!sub.empty()) ui.DrawText(sub, {x, y + 20.0f}, {280.0f, 16.0f}, c.TextTertiary, UI::FontSmall);
        }

        void SectionLabel(float x, float y, float w, const std::wstring& label) {
            auto& ui = UI::g_UI;
            const auto& c = ui.GetColors();
            ui.DrawText(label, {x, y}, {w, 16.0f}, c.TextTertiary, UI::FontSmall);
            ui.DrawLine({x, y + 18.0f}, {x + w, y + 18.0f}, c.BorderSubtle, 1.0f);
        }

        void DrawCard(float x, float y, float w, float h) {
            auto& ui = UI::g_UI;
            const auto& c = ui.GetColors();
            ui.FillRoundedRect({x, y}, {w, h}, 8.0f, c.BgSurface);
            ui.DrawRoundedRect({x, y}, {w, h}, 8.0f, c.BorderSubtle, 1.0f);
        }

        // Toggle bound to a flag mask. Returns true if the state changed.
        bool FlagToggle(const Math::Vector2& pos, const std::wstring& label, uint32_t flag) {
            bool on = Has(flag);
            bool changed = UI::g_UI.RenderToggle(pos, label, on);
            if (changed) SetF(flag, on);
            return changed;
        }

        // Slider bound to a float field in g_cfg. Marks dirty on change.
        bool CfgSlider(const Math::Vector2& pos, const std::wstring& label, float& field,
                       float lo, float hi, const std::wstring& suffix = L"", int decimals = 1) {
            float before = field;
            bool changed = UI::g_UI.RenderSlider(pos, label, field, lo, hi, suffix, decimals);
            if (changed && field != before) g_cfg_dirty = true;
            return changed;
        }
        bool CfgIntSlider(const Math::Vector2& pos, const std::wstring& label, int32_t& field,
                          int lo, int hi, const std::wstring& suffix = L"") {
            int tmp = field;
            bool changed = UI::g_UI.RenderIntSlider(pos, label, tmp, lo, hi, suffix);
            if (changed && tmp != field) { field = tmp; g_cfg_dirty = true; }
            return changed;
        }

        // Combo/keybind bound to an int field.
        bool CfgCombo(const Math::Vector2& pos, const std::wstring& label, int32_t& field,
                      const std::vector<std::wstring>& options) {
            int tmp = field;
            bool changed = UI::g_UI.RenderCombo(pos, label, tmp, options);
            if (changed && tmp != field) { field = tmp; g_cfg_dirty = true; }
            return changed;
        }
        bool CfgKeybind(const Math::Vector2& pos, const std::wstring& label, int32_t& field) {
            int tmp = field;
            bool changed = UI::g_UI.RenderKeybind(pos, label, tmp);
            if (changed && tmp != field) { field = tmp; g_cfg_dirty = true; }
            return changed;
        }

        // Color button bound to a uint32 field. Keeps a persistent Color4 next
        // to g_cfg so slider drags report smooth value; syncs on release.
        struct ColorSlot { uint32_t* field; Config::Color4 scratch; uint32_t last_packed; };
        ColorSlot& Slot(uint32_t* field) {
            static std::vector<ColorSlot> slots;
            for (auto& s : slots) if (s.field == field) {
                // Pull external changes (e.g. Reset colors button).
                if (s.last_packed != *field) {
                    s.scratch = Unpack(*field);
                    s.last_packed = *field;
                }
                return s;
            }
            slots.push_back({field, Unpack(*field), *field});
            return slots.back();
        }
        void CfgColor(const Math::Vector2& pos, const std::wstring& label, uint32_t& field) {
            auto& slot = Slot(&field);
            Config::Color4 before = slot.scratch;
            UI::g_UI.RenderColorButton(pos, label, slot.scratch);
            // Pack back every frame so slider drags are live.
            uint32_t packed = Pack(slot.scratch);
            if (packed != slot.last_packed) {
                field = packed;
                slot.last_packed = packed;
                if (before.r != slot.scratch.r || before.g != slot.scratch.g ||
                    before.b != slot.scratch.b || before.a != slot.scratch.a) {
                    g_cfg_dirty = true;
                }
            }
        }
    }

    bool MainMenu::Initialize(IDXGISwapChain* swap) {
        if (m_initialized) return true;
        if (!UI::g_UI.Initialize(swap)) return false;
        m_initialized = true;
        return true;
    }

    void MainMenu::ReloadConfig() {
        const bool valid = g_cfg.pad[0] == CFG_UI_TAG && g_cfg.pad[1] <= 4;
        g_theme_index = valid ? static_cast<int>(g_cfg.pad[1]) : 2;
        Config::g_Config.Customization.Theme = static_cast<Config::AccentTheme>(g_theme_index);
        Config::g_Config.Customization.ReducedMotion = valid && g_cfg.pad[2] != 0;
        UI::g_UI.UpdateTheme(Config::g_Config.Customization.Theme);
    }

    void MainMenu::Shutdown() {
        if (m_initialized) { UI::g_UI.Shutdown(); m_initialized = false; }
    }

    void MainMenu::UpdateInput(const Math::Vector2& mouse, bool mouseDown) {
        UI::g_UI.UpdateInput(mouse, mouseDown);
    }

    void MainMenu::RenderSidebar() {
        auto& ui = UI::g_UI;
        const auto& c = ui.GetColors();
        const float sideW = 188.0f;
        const float x = m_pos.x, y = m_pos.y, h = m_size.y;

        ui.FillRoundedRect({x, y}, {sideW, h}, 10.0f, c.BgSurface);
        ui.DrawLine({x + sideW, y + 12.0f}, {x + sideW, y + h - 12.0f}, c.BorderSubtle, 1.0f);
        ui.DrawLogo({x + 18.0f, y + 18.0f}, 24.0f);

        struct TabEntry { Tab tab; UI::Icon icon; const wchar_t* label; };
        TabEntry tabs[] = {
            { Tab::Visuals,  UI::Icon::Visuals,   L"Visuals" },
            { Tab::Aim,      UI::Icon::Aim,       L"Aim" },
            { Tab::Skins,    UI::Icon::Players,   L"Skins" },
            { Tab::Settings, UI::Icon::Settings,  L"Settings" },
        };

        float by = y + 72.0f;
        for (const auto& t : tabs) {
            Math::Vector2 bp{x + 10.0f, by};
            Math::Vector2 bs{sideW - 20.0f, 36.0f};
            bool hovered = ui.IsHovered(bp, bs);
            bool active = m_activeTab == (int)t.tab;
            D2D1_COLOR_F bg = active ? c.AccentGlow
                : (hovered ? UI::WithAlpha(c.BgElevated, 0.55f) : D2D1::ColorF(0, 0, 0, 0));
            if (bg.a > 0.0f) ui.FillRoundedRect(bp, bs, 7.0f, bg);
            if (active) ui.FillRoundedRect({bp.x, bp.y + 8.0f}, {3.0f, 20.0f}, 1.5f, c.Accent);
            D2D1_COLOR_F iconCol = active ? c.Accent : (hovered ? c.TextPrimary : c.TextSecondary);
            ui.DrawIcon(t.icon, {bp.x + 24.0f, bp.y + bs.y * 0.5f}, 14.0f, iconCol);
            ui.DrawText(t.label, {bp.x + 44.0f, bp.y}, {bs.x - 54.0f, bs.y},
                active ? c.TextPrimary : (hovered ? c.TextPrimary : c.TextSecondary), UI::FontBody);
            if (hovered && ui.IsMouseClicked()) { m_activeTab = (int)t.tab; ui.ClosePopups(); }
            by += 42.0f;
        }

        ui.DrawText(L"CiyE", {x + 18.0f, y + h - 32.0f}, {sideW - 36.0f, 14.0f},
            c.TextTertiary, UI::FontSmall);
        ui.DrawText(L"v2.1", {x + 18.0f, y + h - 32.0f}, {sideW - 36.0f, 14.0f},
            c.TextTertiary, UI::FontSmall, DWRITE_TEXT_ALIGNMENT_TRAILING);
    }

    void MainMenu::RenderHeader() {
        auto& ui = UI::g_UI;
        const auto& c = ui.GetColors();
        const float sideW = 188.0f;
        const float x = m_pos.x + sideW;
        const float y = m_pos.y;
        const float w = m_size.x - sideW;

        const wchar_t* names[] = {L"Visuals", L"Aim", L"Skins", L"Settings"};
        ui.DrawText(names[m_activeTab], {x + 22.0f, y + 22.0f}, {260.0f, 28.0f},
            c.TextPrimary, UI::FontTitle);

        if (ui.RenderIconButton({x + w - 44.0f, y + 20.0f}, {28.0f, 28.0f}, UI::Icon::Close, true)) {
            SetF(F_MENU_OPEN, false);
        }
        ui.DrawLine({x + 20.0f, y + 64.0f}, {x + w - 20.0f, y + 64.0f}, c.BorderSubtle, 1.0f);
    }

    void MainMenu::RenderTabVisuals(float x, float y, float colW, float gap) {
        auto& ui = UI::g_UI;
        const auto& c = ui.GetColors();
        ui.SetItemWidth(colW - kCardPad * 2.0f);

        // Left card: ESP + Elements
        const float cardH = 620.0f;
        DrawCard(x, y, colW, cardH);
        float xi = x + kCardPad;
        CardTitle(xi, y + 12.0f, L"ESP");
        float row = y + 50.0f;
        FlagToggle({xi, row}, L"Enable ESP",   F_ESP);             row += kRowGap;
        SectionLabel(xi, row, colW - kCardPad * 2.0f, L"ELEMENTS"); row += 26.0f;
        FlagToggle({xi, row}, L"Box",          F_ESP_BOX);         row += kRowGap;
        FlagToggle({xi, row}, L"Skeleton",     F_ESP_SKELETON);    row += kRowGap;
        FlagToggle({xi, row}, L"Snapline",     F_ESP_LINE);        row += kRowGap;
        FlagToggle({xi, row}, L"Name",         F_ESP_NAME);        row += kRowGap;
        FlagToggle({xi, row}, L"Weapon",       F_ESP_GUN);         row += kRowGap;
        FlagToggle({xi, row}, L"Distance",     F_ESP_DISTANCE);    row += kRowGap;
        FlagToggle({xi, row}, L"Health",       F_ESP_HEALTH);      row += kRowGap;
        FlagToggle({xi, row}, L"Armor",        F_ESP_ARMOR);       row += kRowGap;
        FlagToggle({xi, row}, L"Head dot",     F_ESP_HEADDOT);     row += kRowGap;
        FlagToggle({xi, row}, L"Counter",      F_ESP_COUNT);

        const float x2 = x + colW + gap;
        DrawCard(x2, y, colW, cardH);
        float xi2 = x2 + kCardPad;
        CardTitle(xi2, y + 12.0f, L"Target filters");
        row = y + 50.0f;
        FlagToggle({xi2, row}, L"Show teammates", F_ESP_TEAM); row += kRowGap;
        ui.DrawText(L"Vehicles are always excluded.", {xi2, row}, {colW - kCardPad * 2.0f, 20.0f}, c.TextSecondary, UI::FontSmall);
        row += 28.0f;
        SectionLabel(xi2, row, colW - kCardPad * 2.0f, L"STYLE"); row += 26.0f;
        FlagToggle({xi2, row}, L"Corner box",   F_ESP_CORNER);   row += kRowGap;
        FlagToggle({xi2, row}, L"Outline",      F_ESP_OUTLINE);  row += kRowGap;
        FlagToggle({xi2, row}, L"Filled",       F_ESP_FILLED);   row += kRowGap;
        FlagToggle({xi2, row}, L"Gradient",     F_ESP_GRADIENT); row += kRowGap;
        FlagToggle({xi2, row}, L"Shadow",       F_ESP_SHADOW);   row += kRowGap;
        CfgSlider({xi2, row}, L"Thickness", g_cfg.box_thickness, 0.5f, 5.0f, L" px", 1); row += 48.0f;

        SectionLabel(xi2, row, colW - kCardPad * 2.0f, L"FILTER"); row += 26.0f;
        FlagToggle({xi2, row}, L"Visible check", F_ESP_VISIBLE); row += kRowGap;
        CfgIntSlider({xi2, row}, L"Max distance", g_cfg.esp_max_dist, 50, 2000, L" m"); row += 48.0f;

        SectionLabel(xi2, row, colW - kCardPad * 2.0f, L"COLORS"); row += 24.0f;
        auto colorRow = [&](const std::wstring& label, uint32_t& cl, float& yy) {
            ui.DrawText(label, {xi2, yy + 4.0f}, {colW - kCardPad * 2.0f - 40.0f, 20.0f}, c.TextSecondary, UI::FontBody);
            CfgColor({x2 + colW - kCardPad - 28.0f, yy + 6.0f}, label, cl);
            yy += 28.0f;
        };
        colorRow(L"Visible",  g_cfg.col_box, row);
        colorRow(L"Hidden",   g_cfg.col_box_hidden, row);
        colorRow(L"Team",     g_cfg.col_team, row);
    }

    void MainMenu::RenderTabAim(float x, float y, float colW, float gap) {
        auto& ui = UI::g_UI;
        ui.SetItemWidth(colW - kCardPad * 2.0f);

        const float cardH = 420.0f;
        DrawCard(x, y, colW, cardH);
        float xi = x + kCardPad;
        CardTitle(xi, y + 12.0f, L"Aimbot");
        float row = y + 50.0f;
        FlagToggle({xi, row}, L"Enable",    F_AIM); row += kRowGap;
        FlagToggle({xi, row}, L"Humanize",  F_AIM_HUMANIZE); row += kRowGap;
        CfgSlider({xi, row}, L"Human smoothing", g_cfg.human_smooth, 0.01f, 1.f, L"", 2); row += 48.f;
        CfgSlider({xi, row}, L"FOV",        g_cfg.aim_fov,      1.0f, 180.0f, L"\x00B0", 1); row += 48.0f;
        CfgSlider({xi, row}, L"Smooth",     g_cfg.aim_smooth,   0.01f, 1.0f,  L"",       2); row += 48.0f;
        CfgSlider({xi, row}, L"Distance",   g_cfg.aim_max_dist, 10.0f, 2000.0f, L" m",   0); row += 48.0f;
        std::vector<std::wstring> bones = {L"Head", L"Neck", L"Spine", L"Pelvis", L"Random"};
        CfgCombo({xi, row}, L"Bone", g_cfg.aim_bone, bones); row += kRowGap;
        FlagToggle({xi, row}, L"Multipoint", F_AIM_MULTIPOINT); row += kRowGap;
        FlagToggle({xi, row}, L"Prediction", F_AIM_PREDICT);

        const float x2 = x + colW + gap;
        DrawCard(x2, y, colW, cardH);
        float xi2 = x2 + kCardPad;
        CardTitle(xi2, y + 12.0f, L"Targeting");
        row = y + 50.0f;
        FlagToggle({xi2, row}, L"Visible only", F_AIM_VISIBLE);    row += kRowGap;
        FlagToggle({xi2, row}, L"Teammates",    F_AIM_TEAM);       row += kRowGap;
        bool ignore_knocked = (g_cfg.reserved & OPT_AIM_IGNORE_KNOCKED) != 0;
        if (ui.RenderToggle({xi2, row}, L"Ignore knocked targets", ignore_knocked)) {
            if (ignore_knocked) g_cfg.reserved |= OPT_AIM_IGNORE_KNOCKED;
            else g_cfg.reserved &= ~OPT_AIM_IGNORE_KNOCKED;
            g_cfg_dirty = true;
        }
        row += kRowGap;
        FlagToggle({xi2, row}, L"FOV circle",   F_AIM_FOV_CIRCLE); row += kRowGap + 6.0f;

        SectionLabel(xi2, row, colW - kCardPad * 2.0f, L"RECOIL"); row += 24.0f;
        FlagToggle({xi2, row}, L"Enable",   F_RECOIL); row += kRowGap;
        CfgSlider({xi2, row}, L"Strength",  g_cfg.humanize, 0.0f, 2.0f, L"", 2); row += 48.0f;

        SectionLabel(xi2, row, colW - kCardPad * 2.0f, L"KEYBIND"); row += 24.0f;
        CfgKeybind({xi2, row}, L"Key", g_cfg.aim_key);
    }

    void MainMenu::RenderTabSkins(float x, float y, float colW, float gap) {
        auto& ui = UI::g_UI;
        const auto& c = ui.GetColors();
        const float fullW = colW * 2.0f + gap;
        ui.SetItemWidth(fullW - kCardPad * 2.0f);

        const float cardH = 460.0f;
        DrawCard(x, y, fullW, cardH);
        float xi = x + kCardPad;
        CardTitle(xi, y + 12.0f, L"Skins");

        ui.SetItemWidth(fullW * 0.5f);
        ui.RenderTextInput({xi, y + 50.0f}, L"Search", g_skin_search);

        ui.SetItemWidth(fullW * 0.5f - kCardPad);
        FlagToggle({xi + fullW * 0.5f + 8.0f, y + 70.0f}, L"Current hero", F_SKIN_CURRENT);
        {
            bool on = g_cfg.auto_skin != 0;
            if (ui.RenderToggle({xi + fullW * 0.5f + 8.0f, y + 70.0f + kRowGap}, L"Auto apply", on)) {
                g_cfg.auto_skin = on ? 1u : 0u;
                g_cfg_dirty = true;
            }
        }

        // Row 2: sub-tabs + Reload button
        const wchar_t* subTabs[] = {L"Characters", L"Knives", L"Guns", L"Inventory"};
        const float toolbarY = y + 150.0f;
        const float reloadW = 110.0f;
        const float tabsRegionW = fullW - kCardPad * 2.0f - reloadW - 12.0f;
        float tabW = (tabsRegionW - 24.0f) / 4.0f;
        float tx = xi;
        for (int i = 0; i < 4; ++i) {
            bool active = g_skin_page == i;
            if (ui.RenderButton({tx, toolbarY}, {tabW, 30.0f}, subTabs[i], active)) g_skin_page = i;
            tx += tabW + 8.0f;
        }
        if (ui.RenderButton({x + fullW - kCardPad - reloadW, toolbarY}, {reloadW, 30.0f}, L"Reload", false)) {
            SkinBridge::Reload();
        }
        ui.DrawLine({xi, toolbarY + 40.0f}, {xi + fullW - kCardPad * 2.0f, toolbarY + 40.0f}, c.BorderSubtle, 1.0f);

        // List area (scrollable via mouse wheel)
        const float listX = xi;
        const float listY = toolbarY + 50.0f;
        const float listW = fullW - kCardPad * 2.0f;
        const float listH = cardH - (listY - y) - 12.0f;

        if (!SkinBridge::Ready()) {
            ui.DrawText(L"Catalog not loaded.",
                {listX, listY + 10.0f}, {listW, 20.0f}, c.TextTertiary, UI::FontBody);
            return;
        }

        // Convert wide search -> narrow lowercase for bridge
        std::string ns;
        ns.reserve(g_skin_search.size());
        for (wchar_t w : g_skin_search) if (w < 128) ns.push_back((char)std::towlower(w));

        static int s_scroll = 0;
        static int s_last_page = -1;
        if (s_last_page != g_skin_page) { s_scroll = 0; s_last_page = g_skin_page; }
        float wheel = ui.ConsumeWheel();
        if (wheel != 0.0f && ui.IsHovered({listX, listY}, {listW, listH})) {
            s_scroll -= (int)(wheel * 3.0f);
            if (s_scroll < 0) s_scroll = 0;
        }

        auto rows = SkinBridge::Browse(g_skin_page, ns);
        if (rows.empty()) {
            ui.DrawText(L"No skins match.", {listX, listY + 10.0f}, {listW, 20.0f}, c.TextTertiary, UI::FontBody);
            return;
        }

        const float rowH = 48.0f;
        int max_rows = (int)(listH / (rowH + 4.0f));
        if (s_scroll > (int)rows.size() - 1) s_scroll = std::max(0, (int)rows.size() - 1);

        ui.PushClip({listX, listY}, {listW, listH});
        float ry = listY;
        for (int i = s_scroll; i < (int)rows.size() && i < s_scroll + max_rows; ++i) {
            const auto& r = rows[i];
            Math::Vector2 rp{listX, ry};
            Math::Vector2 rs{listW, rowH};
            bool hovered = ui.IsHovered(rp, rs);
            D2D1_COLOR_F bg = r.equipped ? c.AccentGlow
                : (hovered ? UI::WithAlpha(c.BgElevated, 0.6f) : c.BgElevated);
            ui.FillRoundedRect(rp, rs, 6.0f, bg);
            ui.FillRoundedRect({rp.x + 10.0f, rp.y + 10.0f}, {28.0f, 28.0f}, 6.0f, c.AccentGlow);
            ui.DrawIcon(UI::Icon::Visuals, {rp.x + 24.0f, rp.y + 24.0f}, 14.0f, c.Accent);

            // Label (wide conversion from narrow utf-8 — simplified: ASCII only path)
            std::wstring wlabel(r.label.begin(), r.label.end());
            std::wstring wgroup(r.group.begin(), r.group.end());
            std::wstring wrarity(r.rarity.begin(), r.rarity.end());
            ui.DrawText(wlabel, {rp.x + 48.0f, rp.y + 4.0f}, {rs.x - 180.0f, 20.0f}, c.TextPrimary, UI::FontBody);
            std::wstring sub = wgroup + L"  \x00B7  " + wrarity;
            ui.DrawText(sub, {rp.x + 48.0f, rp.y + 24.0f}, {rs.x - 180.0f, 18.0f}, c.TextTertiary, UI::FontSmall);

            // Apply button on the right
            Math::Vector2 bp{rp.x + rs.x - 110.0f, rp.y + 9.0f};
            if (ui.RenderButton(bp, {98.0f, 30.0f}, r.equipped ? L"Equipped" : L"Apply", !r.equipped, true)) {
                if (!r.equipped) SkinBridge::Apply(g_skin_page, r.apply_item);
            }
            ry += rowH + 4.0f;
        }
        ui.PopClip();

        // Scroll hint
        wchar_t cnt[64];
        int shown = std::min((int)rows.size(), max_rows);
        swprintf_s(cnt, L"%d – %d of %d", s_scroll + 1, s_scroll + shown, (int)rows.size());
        ui.DrawText(cnt, {listX + listW - 140.0f, listY + listH - 18.0f},
            {140.0f, 16.0f}, c.TextTertiary, UI::FontSmall, DWRITE_TEXT_ALIGNMENT_TRAILING);
    }

    void MainMenu::RenderTabSettings(float x, float y, float colW, float gap) {
        auto& ui = UI::g_UI;
        ui.SetItemWidth(colW - kCardPad * 2.0f);

        const float cardH = 420.0f;
        DrawCard(x, y, colW, cardH);
        float xi = x + kCardPad;
        CardTitle(xi, y + 12.0f, L"General");
        float row = y + 50.0f;
        CfgKeybind({xi, row}, L"Menu key", g_cfg.menu_key); row += kRowGap + 8.0f;

        Math::Vector2 btnSz{colW - kCardPad * 2.0f, 32.0f};
        if (ui.RenderButton({xi, row}, btnSz, L"Save", true)) SaveConfiguration();
        row += 38.0f;
        const std::string status = ConfigurationStatus();
        ui.DrawText(std::wstring(status.begin(), status.end()), {xi, row}, {btnSz.x, 36.f}, ui.GetColors().TextSecondary, UI::FontSmall);
        row += 44.f;

        SectionLabel(xi, row, colW - kCardPad * 2.0f, L"APPEARANCE"); row += 24.0f;
        std::vector<std::wstring> themes = {L"Purple", L"Crimson", L"Cyan", L"Emerald", L"Mono"};
        if (ui.RenderCombo({xi, row}, L"Accent", g_theme_index, themes)) {
            Config::g_Config.Customization.Theme = (Config::AccentTheme)g_theme_index;
            UI::g_UI.UpdateTheme(Config::g_Config.Customization.Theme);
            g_cfg.pad[0] = CFG_UI_TAG;
            g_cfg.pad[1] = static_cast<uint32_t>(g_theme_index);
            g_cfg.pad[2] = Config::g_Config.Customization.ReducedMotion ? 1u : 0u;
            g_cfg_dirty = true;
        }
        row += kRowGap;
        {
            bool rm = Config::g_Config.Customization.ReducedMotion;
            if (ui.RenderToggle({xi, row}, L"Reduced motion", rm)) {
                Config::g_Config.Customization.ReducedMotion = rm;
                g_cfg.pad[0] = CFG_UI_TAG;
                g_cfg.pad[1] = static_cast<uint32_t>(g_theme_index);
                g_cfg.pad[2] = rm ? 1u : 0u;
                g_cfg_dirty = true;
            }
        }

        const float x2 = x + colW + gap;
        DrawCard(x2, y, colW, cardH);
        float xi2 = x2 + kCardPad;
        CardTitle(xi2, y + 12.0f, L"Protection");
        row = y + 50.0f;
        FlagToggle({xi2, row}, L"Block reports",  F_BLOCK_REPORT);   row += kRowGap;
        FlagToggle({xi2, row}, L"Unlock effects", F_UNLOCK_EFFECTS); row += kRowGap;
        FlagToggle({xi2, row}, L"Stream-proof",   F_STREAM_PROOF);   row += kRowGap + 10.0f;

        SectionLabel(xi2, row, colW - kCardPad * 2.0f, L"SESSION"); row += 24.0f;
        {
            Math::Vector2 bp{xi2, row};
            Math::Vector2 bs{colW - kCardPad * 2.0f, 34.0f};
            bool hovered = ui.IsHovered(bp, bs);
            const auto& c = ui.GetColors();
            D2D1_COLOR_F bg = hovered ? UI::Mix(c.Danger, D2D1::ColorF(D2D1::ColorF::White), 0.12f) : c.Danger;
            ui.FillRoundedRect(bp, bs, 6.0f, bg);
            ui.DrawText(L"Safe exit", bp, bs, D2D1::ColorF(0xFFFFFF, 1.0f),
                UI::FontBold, DWRITE_TEXT_ALIGNMENT_CENTER);
            if (hovered && ui.IsMouseClicked()) SetF(F_EXIT_CHEAT, true);
        }
    }

    void MainMenu::RenderBody() {
        const float sideW = 188.0f;
        const float bodyX = m_pos.x + sideW + 22.0f;
        const float bodyY = m_pos.y + 88.0f;
        const float gap = 16.0f;
        const float bodyW = m_size.x - sideW - 44.0f;
        const float colW = (bodyW - gap) * 0.5f;

        switch (m_activeTab) {
        case (int)Tab::Visuals: {
            auto& ui = UI::g_UI;
            const float height = std::max(1.f, m_size.y - 104.f);
            const float max_scroll = std::max(0.f, 620.f - height);
            const float wheel = ui.ConsumeWheel();
            if (!ui.IsPopupOpen() && ui.IsHovered({bodyX, bodyY}, {bodyW, height}))
                m_visual_scroll = std::clamp(m_visual_scroll - wheel * 48.f, 0.f, max_scroll);
            ui.PushClip({bodyX, bodyY}, {bodyW, height});
            RenderTabVisuals(bodyX, bodyY - m_visual_scroll, colW, gap);
            ui.PopClip();
            if (max_scroll > 0) {
                const float thumb_h = height * height / 620.f;
                const float thumb_y = bodyY + (height - thumb_h) * m_visual_scroll / max_scroll;
                ui.FillRoundedRect({bodyX + bodyW + 6.f, thumb_y}, {3.f, thumb_h}, 1.5f, ui.GetColors().BorderHover);
            }
            break;
        }
        case (int)Tab::Aim:      RenderTabAim(bodyX, bodyY, colW, gap); break;
        case (int)Tab::Skins:    RenderTabSkins(bodyX, bodyY, colW, gap); break;
        case (int)Tab::Settings: RenderTabSettings(bodyX, bodyY, colW, gap); break;
        }
    }

    void MainMenu::Render() {
        if (!m_initialized) return;
        auto& ui = UI::g_UI;
        const auto& c = ui.GetColors();

        // Center on first show (viewport may be unknown at construction).
        Math::Vector2 vp = ui.GetViewportSize();
        if (!m_centered_once && vp.x > 1.0f && vp.y > 1.0f) {
            m_pos = {(vp.x - m_size.x) * 0.5f, (vp.y - m_size.y) * 0.5f};
            if (m_pos.x < 20.0f) m_pos.x = 20.0f;
            if (m_pos.y < 20.0f) m_pos.y = 20.0f;
            m_centered_once = true;
        }

        const Math::Vector2 mouse = ui.GetMousePos();
        const bool mdown = ui.IsMouseDown();
        const Math::Vector2 hdrPos{m_pos.x + 188.0f, m_pos.y};
        const Math::Vector2 hdrSize{m_size.x - 248.0f, 64.0f};
        if (!m_dragging && mdown && ui.IsHovered(hdrPos, hdrSize) && ui.IsMouseClicked()) {
            m_dragging = true;
            m_dragOffset = {mouse.x - m_pos.x, mouse.y - m_pos.y};
        }
        if (m_dragging) {
            if (!mdown) m_dragging = false;
            else m_pos = {mouse.x - m_dragOffset.x, mouse.y - m_dragOffset.y};
        }

        ui.BeginDraw();

        // Focus gate: dim the game behind the menu so the user's attention locks in.
        if (vp.x > 1.0f && vp.y > 1.0f) {
            ui.FillRect({0, 0}, vp, D2D1::ColorF(0, 0, 0, 0.55f));
        }

        ui.DrawShadow(m_pos, m_size, 10.0f, 8.0f, 28.0f, 0.65f);
        ui.FillRoundedRect(m_pos, m_size, 10.0f, c.BgBase);
        ui.DrawRoundedRect(m_pos, m_size, 10.0f, c.BorderSubtle, 1.0f);

        RenderSidebar();
        RenderHeader();
        RenderBody();

        ui.RenderPopups();
        ui.EndDraw();
    }

} // namespace Menu34
