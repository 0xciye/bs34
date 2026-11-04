#pragma once
#include "imgui.h"
#include <cmath>

namespace CiyEUi {
inline constexpr ImU32 Accent = IM_COL32(164, 143, 246, 255);
inline constexpr ImU32 Text = IM_COL32(232, 232, 236, 255);
inline constexpr ImU32 Muted = IM_COL32(158, 158, 169, 255);
inline constexpr ImU32 Ground = IM_COL32(16, 16, 18, 255);
inline constexpr ImU32 Surface = IM_COL32(21, 22, 24, 255);
inline constexpr ImU32 Border = IM_COL32(41, 42, 47, 255);
inline void ApplyStyle(float scale = 1.0f) {
    ImGui::StyleColorsDark();
    auto& s = ImGui::GetStyle();
    s.FontSizeBase = 13 * scale;
    s.WindowRounding = 12; s.ChildRounding = 10; s.FrameRounding = 6;
    s.PopupRounding = 8; s.GrabRounding = 5; s.ScrollbarRounding = 6;
    s.WindowBorderSize = 1; s.ChildBorderSize = 1; s.FrameBorderSize = 0;
    s.WindowPadding = ImVec2(24, 18); s.FramePadding = ImVec2(10, 6);
    s.ItemSpacing = ImVec2(10, 8); s.ItemInnerSpacing = ImVec2(8, 6);
    s.ScrollbarSize = 5;
    auto* c = s.Colors;
    c[ImGuiCol_Text] = ImGui::ColorConvertU32ToFloat4(Text);
    c[ImGuiCol_TextDisabled] = ImGui::ColorConvertU32ToFloat4(Muted);
    c[ImGuiCol_WindowBg] = ImGui::ColorConvertU32ToFloat4(Surface);
    c[ImGuiCol_ChildBg] = ImVec4(0, 0, 0, 0);
    c[ImGuiCol_PopupBg] = ImVec4(.085f, .085f, .095f, 1);
    c[ImGuiCol_Border] = ImGui::ColorConvertU32ToFloat4(Border);
    c[ImGuiCol_FrameBg] = c[ImGuiCol_Button] = ImVec4(.13f, .13f, .145f, 1);
    c[ImGuiCol_FrameBgHovered] = c[ImGuiCol_ButtonHovered] = ImVec4(.18f, .17f, .215f, 1);
    c[ImGuiCol_FrameBgActive] = c[ImGuiCol_ButtonActive] = ImVec4(.23f, .205f, .31f, 1);
    c[ImGuiCol_Header] = ImVec4(.13f, .135f, .145f, 1);
    c[ImGuiCol_TabSelected] = ImVec4(.20f, .18f, .27f, 1);
    c[ImGuiCol_HeaderHovered] = c[ImGuiCol_TabHovered] = ImVec4(.24f, .21f, .33f, 1);
    c[ImGuiCol_HeaderActive] = ImVec4(.28f, .245f, .39f, 1);
    c[ImGuiCol_CheckMark] = c[ImGuiCol_SliderGrab] = ImGui::ColorConvertU32ToFloat4(Accent);
    c[ImGuiCol_SliderGrabActive] = ImVec4(.76f, .68f, 1, 1);
    c[ImGuiCol_Tab] = ImVec4(.10f, .10f, .115f, 1);
    c[ImGuiCol_Separator] = ImGui::ColorConvertU32ToFloat4(Border);
    c[ImGuiCol_ScrollbarBg] = ImVec4(0, 0, 0, 0);
    c[ImGuiCol_ScrollbarGrab] = ImVec4(.28f, .28f, .32f, 1);
    c[ImGuiCol_ScrollbarGrabHovered] = ImVec4(.40f, .37f, .49f, 1);
    if (scale != 1) s.ScaleAllSizes(scale);
}

inline void Logo(ImDrawList* dl, ImVec2 p, float size) {
    dl->AddRectFilled(p, ImVec2(p.x + size, p.y + size), Accent, size * .28f);
    const ImVec2 top(p.x + size * .5f, p.y + size * .20f);
    const ImVec2 left(p.x + size * .20f, p.y + size * .37f);
    const ImVec2 mid(p.x + size * .5f, p.y + size * .54f);
    const ImVec2 right(p.x + size * .80f, p.y + size * .37f);
    const ImVec2 bottom(p.x + size * .5f, p.y + size * .84f);
    dl->AddQuadFilled(top, right, mid, left, IM_COL32(29, 24, 46, 255));
    dl->AddQuadFilled(left, mid, bottom, ImVec2(left.x, p.y + size * .67f), IM_COL32(65, 54, 96, 255));
    dl->AddQuadFilled(mid, right, ImVec2(right.x, p.y + size * .67f), bottom, IM_COL32(100, 84, 145, 255));
}

enum class Icon { Eye, Target, Skins, Settings };
inline void DrawIcon(ImDrawList* dl, ImVec2 p, Icon icon, ImU32 color) {
    const float t = 1.5f;
    if (icon == Icon::Eye) {
        dl->AddBezierCubic(ImVec2(p.x-7,p.y), ImVec2(p.x-3,p.y-6), ImVec2(p.x+3,p.y-6), ImVec2(p.x+7,p.y), color,t);
        dl->AddBezierCubic(ImVec2(p.x-7,p.y), ImVec2(p.x-3,p.y+6), ImVec2(p.x+3,p.y+6), ImVec2(p.x+7,p.y), color,t);
        dl->AddCircle(p,2.2f,color,16,t);
    } else if (icon == Icon::Target) {
        dl->AddCircle(p,4.7f,color,20,t);
        dl->AddLine(ImVec2(p.x-8,p.y),ImVec2(p.x-3,p.y),color,t);
        dl->AddLine(ImVec2(p.x+3,p.y),ImVec2(p.x+8,p.y),color,t);
        dl->AddLine(ImVec2(p.x,p.y-8),ImVec2(p.x,p.y-3),color,t);
        dl->AddLine(ImVec2(p.x,p.y+3),ImVec2(p.x,p.y+8),color,t);
    } else if (icon == Icon::Skins) {
        ImVec2 points[] = {{p.x-3,p.y-6},{p.x-7,p.y-3},{p.x-5,p.y},{p.x-3,p.y-1},{p.x-3,p.y+6},
                          {p.x+3,p.y+6},{p.x+3,p.y-1},{p.x+5,p.y},{p.x+7,p.y-3},{p.x+3,p.y-6},
                          {p.x+1,p.y-4},{p.x-1,p.y-4}};
        dl->AddPolyline(points,12,color,t,ImDrawFlags_Closed);
    } else {
        dl->AddCircle(p,4,color,20,t);
        for (int i=0;i<8;++i) {
            float a=i*3.14159265f/4;
            dl->AddLine(ImVec2(p.x+std::cos(a)*6,p.y+std::sin(a)*6),ImVec2(p.x+std::cos(a)*8,p.y+std::sin(a)*8),color,t);
        }
    }
}

inline bool NavItem(const char* label, Icon icon, bool active, float width) {
    ImGui::PushID(label);
    ImVec2 p=ImGui::GetCursorScreenPos();
    ImGui::PushStyleColor(ImGuiCol_Button,ImVec4(0,0,0,0));
    ImGui::PushStyleColor(ImGuiCol_ButtonHovered,ImVec4(0,0,0,0));
    ImGui::PushStyleColor(ImGuiCol_ButtonActive,ImVec4(0,0,0,0));
    bool pressed=ImGui::Button("##nav",ImVec2(width,36));
    bool hovered=ImGui::IsItemHovered();
    ImGui::PopStyleColor(3);
    auto* dl=ImGui::GetWindowDrawList();
    if(active||hovered) dl->AddRectFilled(p,ImVec2(p.x+width,p.y+36),active?IM_COL32(33,34,38,255):IM_COL32(27,28,31,255),8);
    DrawIcon(dl,ImVec2(p.x+20,p.y+18),icon,active?Accent:Muted);
    dl->AddText(ImVec2(p.x+40,p.y+(36-ImGui::GetFontSize())*.5f),active?Text:Muted,label);
    ImGui::PopID();
    return pressed;
}

inline bool Toggle(const char* label, bool* value, float width=0, float scale=1) {
    ImGui::PushID(label);
    const ImVec2 p=ImGui::GetCursorScreenPos();
    const float h=30*scale, track_w=32*scale, track_h=18*scale;
    if(width<=0) width=ImGui::CalcTextSize(label,nullptr,true).x+48*scale;
    ImGui::PushStyleColor(ImGuiCol_Button,ImVec4(0,0,0,0));
    ImGui::PushStyleColor(ImGuiCol_ButtonHovered,ImVec4(0,0,0,0));
    ImGui::PushStyleColor(ImGuiCol_ButtonActive,ImVec4(0,0,0,0));
    const bool pressed=ImGui::Button("##switch",ImVec2(width,h));
    if(pressed) *value=!*value;
    const bool hovered=ImGui::IsItemHovered();
    ImGui::PopStyleColor(3);
    auto* dl=ImGui::GetWindowDrawList();
    if(hovered) dl->AddRectFilled(p,ImVec2(p.x+width,p.y+h),IM_COL32(255,255,255,8),5*scale);
    ImGuiID anim_id=ImGui::GetID("position");
    auto* storage=ImGui::GetStateStorage();
    float x=storage->GetFloat(anim_id,*value?1.f:0.f);
    x+=((*value?1.f:0.f)-x)*(1-std::exp(-20*ImGui::GetIO().DeltaTime));
    storage->SetFloat(anim_id,x);
    const ImVec2 track(p.x+width-track_w,p.y+(h-track_h)*.5f);
    ImVec4 off=ImGui::ColorConvertU32ToFloat4(IM_COL32(33,34,38,255));
    ImVec4 on=ImGui::ColorConvertU32ToFloat4(Accent);
    ImVec4 fill(off.x+(on.x-off.x)*x,off.y+(on.y-off.y)*x,off.z+(on.z-off.z)*x,1);
    dl->AddRectFilled(track,ImVec2(track.x+track_w,track.y+track_h),ImGui::GetColorU32(fill),track_h*.5f);
    if(x<.5f) dl->AddRect(track,ImVec2(track.x+track_w,track.y+track_h),ImGui::GetColorU32(ImGuiCol_TextDisabled),track_h*.5f);
    dl->AddCircleFilled(ImVec2(track.x+9*scale+14*scale*x,track.y+9*scale),6*scale,
                        ImGui::GetColorU32(*value?ImVec4(.08f,.07f,.12f,1):ImVec4(.64f,.65f,.69f,1)));
    ImGui::PushStyleColor(ImGuiCol_Text,ImGui::ColorConvertU32ToFloat4((*value||hovered)?Text:Muted));
    const char* end=label;
    while(*end && !(end[0]=='#' && end[1]=='#')) ++end;
    dl->PushClipRect(p,ImVec2(track.x-8*scale,p.y+h),true);
    dl->AddText(ImVec2(p.x,p.y+(h-ImGui::GetFontSize())*.5f),ImGui::GetColorU32(ImGuiCol_Text),label,end);
    dl->PopClipRect();
    ImGui::PopStyleColor();
    ImGui::PopID();
    return pressed;
}

inline bool CloseButton(const char* id, ImVec2 size) {
    const ImVec2 p=ImGui::GetCursorScreenPos();
    ImGui::PushStyleColor(ImGuiCol_Button,ImVec4(0,0,0,0));
    bool pressed=ImGui::Button(id,size);
    ImGui::PopStyleColor();
    const ImVec2 center(p.x+size.x*.5f,p.y+size.y*.5f);
    auto* dl=ImGui::GetWindowDrawList();
    dl->AddLine(ImVec2(center.x-3,center.y-3),ImVec2(center.x+3,center.y+3),Muted,1.5f);
    dl->AddLine(ImVec2(center.x-3,center.y+3),ImVec2(center.x+3,center.y-3),Muted,1.5f);
    return pressed;
}
inline const char* Rarity(unsigned quality) {
    switch (quality) {
    case 4: return "Legendary"; case 5: return "Ultra"; case 6: return "Eternal";
    case 7: return "EVO"; case 8: return "XTREME"; default: return "";
    }
}
}
