// 34Cheat-style D2D overlay menu, mapped to bs-cheat's real feature list
// (Visuals / Aim / Skins / Settings). Visual layer only — wire the toggles
// to g_cfg / F_* flags in overlay.cpp when porting the core.
#pragma once
#include <dxgi.h>
#include "ui_renderer.hpp"

namespace Menu34 {

    enum class Tab { Visuals, Aim, Skins, Settings, Count };
    constexpr int kTabCount = (int)Tab::Count;

    class MainMenu {
    public:
        bool Initialize(IDXGISwapChain* swap);
        void Shutdown();
        void ReloadConfig();
        void UpdateInput(const Math::Vector2& mouse, bool mouseDown);
        void AddWheel(float notches) { UI::g_UI.AddWheel(notches); }
        void AddChar(wchar_t c) { UI::g_UI.AddCharacter(c); }
        void Render();
        bool IsPopupOpen() const { return UI::g_UI.IsPopupOpen(); }
        bool IsCapturingInput() const { return UI::g_UI.IsCapturingInput(); }

        void SetPos(const Math::Vector2& p) { m_pos = p; }
        const Math::Vector2& GetPos() const { return m_pos; }
        const Math::Vector2& GetSize() const { return m_size; }

    private:
        Math::Vector2 m_pos{120.0f, 80.0f};
        Math::Vector2 m_size{820.0f, 560.0f};
        int m_activeTab = (int)Tab::Visuals;
        int m_skinSubtab = 0;
        bool m_dragging = false;
        Math::Vector2 m_dragOffset{0, 0};
        bool m_initialized = false;
        bool m_centered_once = false;
        float m_visual_scroll = 0.f;

        void RenderSidebar();
        void RenderHeader();
        void RenderBody();
        void RenderTabVisuals(float x, float y, float colW, float gap);
        void RenderTabAim(float x, float y, float colW, float gap);
        void RenderTabSkins(float x, float y, float colW, float gap);
        void RenderTabSettings(float x, float y, float colW, float gap);
    };

    inline MainMenu g_Menu;

} // namespace Menu34
