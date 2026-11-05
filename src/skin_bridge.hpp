// Narrow bridge so Menu34 (separate TU) can browse and apply skins without
// pulling in overlay.cpp's catalog statics.
#pragma once
#include <cstdint>
#include <string>
#include <vector>

struct SkinRow {
    uint32_t    apply_item;  // id passed back to SkinBridge::Apply
    std::string label;       // skin name (NameOf)
    std::string group;       // weapon label or hero label
    std::string rarity;      // "Legendary", "Ultra", …
    bool        equipped;    // currently equipped in this slot
};

namespace SkinBridge {
    bool Ready();
    void Reload();
    // page: 0=Characters, 1=Knives, 2=Guns, 3=Inventory
    std::vector<SkinRow> Browse(int page, const std::string& search);
    void Apply(int page, uint32_t apply_item);
}
