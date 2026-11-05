// Minimal shims so 34Cheat's ui_renderer compiles standalone inside bs-cheat.
// Supplies only the symbols UIRenderer touches (Math::Vector2, Config::Color4,
// Config::AccentTheme, Config::g_Config, Diagnostics::Log).
#pragma once
#include <sstream>
#include <iostream>
#include <cstdint>

namespace Math {
    struct Vector2 {
        float x{0.0f};
        float y{0.0f};
        Vector2() = default;
        Vector2(float ix, float iy) : x(ix), y(iy) {}
    };
}

namespace Config {
    struct Color4 {
        float r{1.0f}, g{1.0f}, b{1.0f}, a{1.0f};
        Color4() = default;
        Color4(float ir, float ig, float ib, float ia) : r(ir), g(ig), b(ib), a(ia) {}
    };

    enum class AccentTheme : int {
        MidnightPurple = 0,
        CrimsonRed,
        CyberpunkCyan,
        EmeraldGreen,
        Monochrome,
    };

    struct CustomizationCfg {
        AccentTheme Theme{AccentTheme::CyberpunkCyan};
        bool ReducedMotion{false};
        int MenuHotkey{0x2D};   // VK_INSERT
        int PanicHotkey{0x23};  // VK_END
    };

    struct RootCfg {
        CustomizationCfg Customization{};
    };

    inline RootCfg g_Config{};
}

namespace Diagnostics {
    namespace detail {
        inline void append(std::ostringstream&) {}
        template <class T, class... Rest>
        inline void append(std::ostringstream& os, const T& v, const Rest&... rest) {
            os << v;
            append(os, rest...);
        }
    }
    template <class... Args>
    inline void Log(const Args&... args) {
        std::ostringstream os;
        detail::append(os, args...);
        OutputDebugStringA((os.str() + "\n").c_str());
    }
}
