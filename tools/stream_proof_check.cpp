// Native render/affinity checks on disposable off-screen windows; no game/OBS access.
#include "../src/capture_overlay.h"
#include <cassert>
#include <iostream>

static void Visuals() {
    ImGui::GetBackgroundDrawList()->AddRectFilled(ImVec2(4,4),ImVec2(80,80),IM_COL32(255,0,0,255));
    ImGui::GetBackgroundDrawList()->AddCircle(ImVec2(150,100),40,IM_COL32(0,255,0,255));
}
static unsigned Pixel(ID3D11Device* device,ID3D11DeviceContext* context,ID3D11Texture2D* source,UINT x=0,UINT y=0) {
    D3D11_TEXTURE2D_DESC d{};source->GetDesc(&d);d.Usage=D3D11_USAGE_STAGING;d.BindFlags=0;
    d.CPUAccessFlags=D3D11_CPU_ACCESS_READ;d.MiscFlags=0;
    Microsoft::WRL::ComPtr<ID3D11Texture2D> copy;
    assert(SUCCEEDED(device->CreateTexture2D(&d,nullptr,&copy)));context->CopyResource(copy.Get(),source);
    D3D11_MAPPED_SUBRESOURCE mapped{};assert(SUCCEEDED(context->Map(copy.Get(),0,D3D11_MAP_READ,0,&mapped)));
    unsigned value=*reinterpret_cast<unsigned*>(static_cast<unsigned char*>(mapped.pData)+y*mapped.RowPitch+x*4);
    context->Unmap(copy.Get(),0);return value;
}
static ID3D11Device* test_device=nullptr;
static ID3D11DeviceContext* test_context=nullptr;
static UINT received_count=0;
static UINT received_messages[8]{};
static LPARAM received_points[8]{};
static bool check_imgui_input=false;
static LRESULT CALLBACK GameWindowProc(HWND window,UINT message,WPARAM w,LPARAM l) {
    if(check_imgui_input) {
        auto& io=ImGui::GetIO();
        if(message==WM_MOUSEMOVE) io.AddMousePosEvent(static_cast<short>(LOWORD(l)),static_cast<short>(HIWORD(l)));
        if(message==WM_LBUTTONDOWN||message==WM_LBUTTONUP) io.AddMouseButtonEvent(0,message==WM_LBUTTONDOWN);
    }
    if(message>=WM_MOUSEFIRST&&message<=WM_MOUSELAST&&received_count<8) {
        received_messages[received_count]=message;received_points[received_count++]=l;
        return 0;
    }
    return DefWindowProcW(window,message,w,l);
}
static void CheckProtectedPixels(const ImDrawList*,const ImDrawCmd*) {
    Microsoft::WRL::ComPtr<ID3D11RenderTargetView> output;
    Microsoft::WRL::ComPtr<ID3D11Resource> resource;
    Microsoft::WRL::ComPtr<ID3D11Texture2D> back;
    test_context->OMGetRenderTargets(1,&output,nullptr);assert(output);
    output->GetResource(&resource);assert(SUCCEEDED(resource.As(&back)));
    assert(Pixel(test_device,test_context,back.Get())==0); // Empty surface must be transparent, not opaque black.
    assert((Pixel(test_device,test_context,back.Get(),10,10)>>24)==255); // ESP fixture is visible.
    assert((Pixel(test_device,test_context,back.Get(),210,230)>>24)>0); // Menu shares protected output.
}
int main() {
    CoInitializeEx(nullptr,COINIT_MULTITHREADED);
    WNDCLASSW cls{};cls.lpfnWndProc=GameWindowProc;cls.hInstance=GetModuleHandleW(nullptr);cls.lpszClassName=L"CiyEProofCheck";
    RegisterClassW(&cls);
    HWND game=CreateWindowW(cls.lpszClassName,L"Disposable capture test",WS_POPUP,-10000,-10000,640,480,
                            nullptr,nullptr,cls.hInstance,nullptr);assert(game);
    Microsoft::WRL::ComPtr<ID3D11Device> device;Microsoft::WRL::ComPtr<ID3D11DeviceContext> context;
    HRESULT hr=D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_HARDWARE,nullptr,0,nullptr,0,D3D11_SDK_VERSION,
                                 &device,nullptr,&context);
    if(FAILED(hr)) hr=D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,
                                      &device,nullptr,&context);
    if(FAILED(hr)) {std::cerr<<"D3D11 unavailable\n";return 2;}
    test_device=device.Get();test_context=context.Get();
    D3D11_TEXTURE2D_DESC d{};d.Width=640;d.Height=480;d.ArraySize=d.MipLevels=1;
    d.SampleDesc.Count=1;d.Format=DXGI_FORMAT_R8G8B8A8_UNORM;d.BindFlags=D3D11_BIND_RENDER_TARGET;
    Microsoft::WRL::ComPtr<ID3D11Texture2D> game_back;
    Microsoft::WRL::ComPtr<ID3D11RenderTargetView> game_rtv;
    assert(SUCCEEDED(device->CreateTexture2D(&d,nullptr,&game_back)));
    assert(SUCCEEDED(device->CreateRenderTargetView(game_back.Get(),nullptr,&game_rtv)));
    ImGui::CreateContext();auto& io=ImGui::GetIO();io.DisplaySize=ImVec2(640,480);io.DeltaTime=1.f/60;
    io.IniFilename=nullptr;io.LogFilename=nullptr;io.FontDefault=io.Fonts->AddFontDefault();
    assert(ImGui_ImplDX11_Init(device.Get(),context.Get()));
    CaptureOverlay layer;
    for(int cycle=0;cycle<3;++cycle) {
        ImGui_ImplDX11_NewFrame();ImGui::NewFrame();ImGui::Render();
        if(!layer.Initialize(device.Get(),context.Get())) {std::cerr<<layer.Error()<<"\n";return 3;}
        assert(layer.Ready()&&layer.Window()!=game);
        DWORD affinity=0;assert(GetWindowDisplayAffinity(layer.Window(),&affinity)&&affinity==WDA_EXCLUDEFROMCAPTURE);
        assert(GetWindowDisplayAffinity(game,&affinity)&&affinity==WDA_NONE);
        const LONG_PTR styles=GetWindowLongPtrW(layer.Window(),GWL_EXSTYLE);
        assert((styles&WS_EX_TRANSPARENT)&&(styles&WS_EX_NOACTIVATE)&&(styles&WS_EX_NOREDIRECTIONBITMAP));
        assert(!(styles&WS_EX_LAYERED));
        assert(!layer.Position(game,false));
        assert(SendMessageW(layer.Window(),WM_NCHITTEST,0,0)==HTCLIENT);
        received_count=0;
        POINT expected{12,34};MapWindowPoints(layer.Window(),game,&expected,1);
        SendMessageW(layer.Window(),WM_LBUTTONDOWN,MK_LBUTTON,MAKELPARAM(12,34));
        SendMessageW(layer.Window(),WM_LBUTTONUP,0,MAKELPARAM(12,34));
        SendMessageW(layer.Window(),WM_MOUSEWHEEL,MAKEWPARAM(0,WHEEL_DELTA),MAKELPARAM(-25,40));
        MSG queued{};
        while(PeekMessageW(&queued,game,WM_MOUSEFIRST,WM_MOUSELAST,PM_REMOVE)) DispatchMessageW(&queued);
        assert(received_count==3&&received_messages[0]==WM_LBUTTONDOWN&&received_messages[1]==WM_LBUTTONUP);
        assert(received_points[0]==MAKELPARAM(expected.x,expected.y)&&received_points[1]==received_points[0]);
        assert(received_messages[2]==WM_MOUSEWHEEL&&received_points[2]==MAKELPARAM(-25,40));
        assert(!layer.Position(game,false));
        // Closing the menu must not disable delivery to game UI/gameplay.
        SendMessageW(layer.Window(),WM_RBUTTONDOWN,MK_RBUTTON,MAKELPARAM(12,34));
        SendMessageW(layer.Window(),WM_RBUTTONUP,0,MAKELPARAM(12,34));
        while(PeekMessageW(&queued,game,WM_MOUSEFIRST,WM_MOUSELAST,PM_REMOVE)) DispatchMessageW(&queued);
        assert(received_count==5&&received_messages[3]==WM_RBUTTONDOWN&&received_messages[4]==WM_RBUTTONUP);
        ShowWindow(layer.Window(),SW_SHOWNOACTIVATE);
        for(int attempt=0;attempt<100&&IsWindowVisible(layer.Window());++attempt) Sleep(10);
        assert(!IsWindowVisible(layer.Window()));
        assert(layer.Resize(800,600));assert(layer.Resize(640,480));
        ID3D11RenderTargetView* output=game_rtv.Get();context->OMSetRenderTargets(1,&output,nullptr);
        const float clear[4]={.125f,.25f,.375f,1};context->ClearRenderTargetView(game_rtv.Get(),clear);
        const unsigned before=Pixel(device.Get(),context.Get(),game_back.Get());
        ImGuiContext* primary=ImGui::GetCurrentContext();
        ImGui_ImplDX11_NewFrame();ImGui::NewFrame();Visuals();
        ImGui::SetNextWindowPos(ImVec2(200,200));ImGui::SetNextWindowSize(ImVec2(300,150));
        ImGui::Begin("Protected menu");ImGui::TextUnformatted("Menu and visuals share capture protection");ImGui::End();
        ImGui::GetForegroundDrawList()->AddCallback(CheckProtectedPixels,nullptr);
        ImGui::Render();
        assert(layer.Render(ImGui::GetDrawData()));
        assert(ImGui::GetCurrentContext()==primary);
        Microsoft::WRL::ComPtr<ID3D11RenderTargetView> restored;context->OMGetRenderTargets(1,&restored,nullptr);
        assert(restored.Get()==game_rtv.Get());
        assert(Pixel(device.Get(),context.Get(),game_back.Get())==before);
        assert(GetWindowDisplayAffinity(game,&affinity)&&affinity==WDA_NONE);
        check_imgui_input=true;bool clicked=false;
        ImGui::GetIO().AddFocusEvent(true);
        POINT click{40,220};MapWindowPoints(game,layer.Window(),&click,1);
        for(int frame=0;frame<6;++frame) {
            SendMessageW(layer.Window(),WM_MOUSEMOVE,0,MAKELPARAM(click.x,click.y));
            if(frame==2) SendMessageW(layer.Window(),WM_LBUTTONDOWN,MK_LBUTTON,MAKELPARAM(click.x,click.y));
            if(frame==4) SendMessageW(layer.Window(),WM_LBUTTONUP,0,MAKELPARAM(click.x,click.y));
            while(PeekMessageW(&queued,game,WM_MOUSEFIRST,WM_MOUSELAST,PM_REMOVE)) DispatchMessageW(&queued);
            ImGui_ImplDX11_NewFrame();ImGui::NewFrame();
            ImGui::SetNextWindowPos(ImVec2(20,200));ImGui::SetNextWindowSize(ImVec2(150,100));
            ImGui::Begin("Click delivery",nullptr,ImGuiWindowFlags_NoTitleBar);
            ImGui::SetCursorPos(ImVec2(10,10));clicked|=ImGui::Button("Delivered",ImVec2(100,30));
            ImGui::End();ImGui::Render();assert(layer.Render(ImGui::GetDrawData()));
        }
        assert(clicked);check_imgui_input=false;
        HWND removed=layer.Window();layer.Shutdown();
        assert(!layer.Ready()&&!IsWindow(removed));
        // The primary context/font atlas still renders after the protected surface closes.
        ImGui_ImplDX11_NewFrame();ImGui::NewFrame();ImGui::TextUnformatted("Main context intact");ImGui::Render();
        ImGui_ImplDX11_RenderDrawData(ImGui::GetDrawData());
    }
    ImGui_ImplDX11_Shutdown();ImGui::DestroyContext();DestroyWindow(game);
    UnregisterClassW(cls.lpszClassName,cls.hInstance);CoUninitialize();
    std::cout<<"Capture layer checks passed: transparent background, protected menu/ESP pixels, game affinity unchanged, separate pixels, context restore, resize and teardown.\n";
    return 0;
}
