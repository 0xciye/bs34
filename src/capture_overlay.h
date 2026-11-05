#pragma once
#include <windows.h>
#include <d3d11.h>
#include <dxgi1_2.h>
#include <dcomp.h>
#include <wrl/client.h>
#include <atomic>
#include <string>
#include "imgui.h"
#include "backends/imgui_impl_dx11.h"

#ifndef WDA_EXCLUDEFROMCAPTURE
#define WDA_EXCLUDEFROMCAPTURE 0x00000011
#endif

// Owns only a transparent visual layer. Never assigns capture affinity to the game HWND.
class CaptureOverlay {
    template<class T> using Ptr=Microsoft::WRL::ComPtr<T>;
    std::atomic<HWND> window_{nullptr};
    std::atomic<HWND> game_{nullptr};
    std::atomic<bool> stopping_{false};
    HANDLE thread_=nullptr,ready_=nullptr;
    DWORD window_error_=0;
    Ptr<ID3D11Device> device_;
    Ptr<ID3D11DeviceContext> context_;
    Ptr<IDXGISwapChain1> swap_;
    Ptr<ID3D11RenderTargetView> rtv_;
    Ptr<IDCompositionDevice> composition_;
    Ptr<IDCompositionTarget> target_;
    Ptr<IDCompositionVisual> visual_;
    UINT width_=1,height_=1;
    std::string error_;

    static LRESULT CALLBACK WindowProc(HWND hwnd,UINT message,WPARAM w,LPARAM l) {
        if(message==WM_NCCREATE) {
            auto* create=reinterpret_cast<CREATESTRUCTW*>(l);
            SetWindowLongPtrW(hwnd,GWLP_USERDATA,reinterpret_cast<LONG_PTR>(create->lpCreateParams));
        }
        if(message==WM_TIMER) {
            auto* self=reinterpret_cast<CaptureOverlay*>(GetWindowLongPtrW(hwnd,GWLP_USERDATA));
            HWND game=self?self->game_.load():nullptr;
            HWND root=game?GetAncestor(game,GA_ROOT):nullptr;
            if(!root||IsIconic(root)||GetForegroundWindow()!=root) ShowWindow(hwnd,SW_HIDE);
            return 0;
        }
        auto* self=reinterpret_cast<CaptureOverlay*>(GetWindowLongPtrW(hwnd,GWLP_USERDATA));
        if(message==WM_NCHITTEST) return HTCLIENT;
        // HTTRANSPARENT only searches windows on this thread; the game uses another thread.
        // Queue input to its existing handler instead of calling ImGui from this window thread.
        if(self&&message>=WM_MOUSEFIRST&&message<=WM_MOUSELAST) {
            HWND game=self->game_.load();
            if(game&&IsWindow(game)) {
                if(message!=WM_MOUSEWHEEL&&message!=WM_MOUSEHWHEEL) {
                    POINT point{static_cast<short>(LOWORD(l)),static_cast<short>(HIWORD(l))};
                    MapWindowPoints(hwnd,game,&point,1);
                    l=MAKELPARAM(point.x,point.y);
                }
                PostMessageW(game,message,w,l);
            }
            return message==WM_XBUTTONDOWN||message==WM_XBUTTONUP||message==WM_XBUTTONDBLCLK?TRUE:0;
        }
        if(message==WM_MOUSEACTIVATE) return MA_NOACTIVATE;
        if(message==WM_ERASEBKGND) return 1;
        if(message==WM_DESTROY) {PostQuitMessage(0);return 0;}
        return DefWindowProcW(hwnd,message,w,l);
    }
    static DWORD WINAPI WindowThread(void* value) {
        auto& self=*static_cast<CaptureOverlay*>(value);
        const std::wstring name=L"CiyE.CaptureLayer."+std::to_wstring(reinterpret_cast<uintptr_t>(&self));
        WNDCLASSEXW cls{};cls.cbSize=sizeof(cls);cls.lpfnWndProc=WindowProc;
        cls.hInstance=GetModuleHandleW(nullptr);cls.lpszClassName=name.c_str();
        if(!RegisterClassExW(&cls)) {self.window_error_=GetLastError();SetEvent(self.ready_);return 0;}
        // Composition supplies per-pixel alpha; a layered GDI redirection surface can cover it in black.
        HWND hwnd=CreateWindowExW(WS_EX_TOPMOST|WS_EX_TRANSPARENT|WS_EX_NOREDIRECTIONBITMAP|WS_EX_TOOLWINDOW|WS_EX_NOACTIVATE,
            name.c_str(),L"CiyE visual layer",WS_POPUP,-10000,-10000,1,1,nullptr,nullptr,cls.hInstance,&self);
        self.window_.store(hwnd);
        if(!hwnd) self.window_error_=GetLastError();
        else {
            SetTimer(hwnd,1,100,nullptr);
            if(!SetWindowDisplayAffinity(hwnd,WDA_EXCLUDEFROMCAPTURE))
                self.window_error_=GetLastError()?GetLastError():ERROR_NOT_SUPPORTED;
        }
        SetEvent(self.ready_);
        if(hwnd) {
            MSG message{};
            while(!self.stopping_.load()&&GetMessageW(&message,nullptr,0,0)>0) {
                TranslateMessage(&message);DispatchMessageW(&message);
            }
            if(IsWindow(hwnd)) DestroyWindow(hwnd);
        }
        self.window_.store(nullptr);
        UnregisterClassW(name.c_str(),cls.hInstance);
        return 0;
    }
    bool Fail(const char* message) {error_=message;Shutdown();return false;}

public:
    bool Ready() const {return window_.load()&&swap_&&rtv_;}
    HWND Window() const {return window_.load();}
    bool Owns(IDXGISwapChain* swap) const {return swap&&swap==swap_.Get();}
    const char* Error() const {return error_.c_str();}

    bool Initialize(ID3D11Device* device,ID3D11DeviceContext* context) {
        if(Ready()) return true;
        Shutdown();error_.clear();window_error_=0;stopping_.store(false);
        if(!device||!context||!ImGui::GetCurrentContext()) return Fail("Capture layer device unavailable.");
        ready_=CreateEventW(nullptr,TRUE,FALSE,nullptr);
        if(!ready_) return Fail("Could not initialize capture layer.");
        thread_=CreateThread(nullptr,0,WindowThread,this,0,nullptr);
        if(!thread_) return Fail("Could not create capture layer window.");
        if(WaitForSingleObject(ready_,5000)!=WAIT_OBJECT_0||window_error_||!Window())
            return Fail("Capture exclusion unavailable. ESP/FOV hidden.");
        device_=device;context_=context;
        Ptr<IDXGIDevice> dxgi;Ptr<IDXGIAdapter> adapter;Ptr<IDXGIFactory2> factory;
        if(FAILED(device->QueryInterface(IID_PPV_ARGS(&dxgi)))||FAILED(dxgi->GetAdapter(&adapter))||
           FAILED(adapter->GetParent(IID_PPV_ARGS(&factory)))) return Fail("Capture layer DXGI setup failed.");
        DXGI_SWAP_CHAIN_DESC1 desc{};desc.Width=desc.Height=1;desc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;
        desc.SampleDesc.Count=1;desc.BufferUsage=DXGI_USAGE_RENDER_TARGET_OUTPUT;desc.BufferCount=2;
        desc.SwapEffect=DXGI_SWAP_EFFECT_FLIP_SEQUENTIAL;desc.Scaling=DXGI_SCALING_STRETCH;
        desc.AlphaMode=DXGI_ALPHA_MODE_PREMULTIPLIED;
        if(FAILED(factory->CreateSwapChainForComposition(device,&desc,nullptr,&swap_)))
            return Fail("Capture layer swap chain unavailable.");
        if(FAILED(DCompositionCreateDevice(dxgi.Get(),IID_PPV_ARGS(&composition_)))||
           FAILED(composition_->CreateTargetForHwnd(Window(),TRUE,&target_))||
           FAILED(composition_->CreateVisual(&visual_))||FAILED(visual_->SetContent(swap_.Get()))||
           FAILED(target_->SetRoot(visual_.Get()))||FAILED(composition_->Commit()))
            return Fail("Capture layer composition unavailable.");
        width_=height_=0;
        return Resize(1,1);
    }
    void Hide() {if(HWND hwnd=Window()) ShowWindow(hwnd,SW_HIDE);}
    bool Position(HWND game,bool visible) {
        game_.store(game);
        RECT bounds{};POINT origin{};
        if(!Window()||!IsWindow(game)||IsIconic(game)||!GetClientRect(game,&bounds)||
           !ClientToScreen(game,&origin)||bounds.right<=0||bounds.bottom<=0) {Hide();return false;}
        if(!Resize(static_cast<UINT>(bounds.right),static_cast<UINT>(bounds.bottom))) {Hide();return false;}
        if(!visible) {Hide();return false;}
        RECT current{};GetWindowRect(Window(),&current);
        if(current.left!=origin.x||current.top!=origin.y||
           current.right-current.left!=bounds.right||current.bottom-current.top!=bounds.bottom)
            SetWindowPos(Window(),nullptr,origin.x,origin.y,bounds.right,bounds.bottom,
                         SWP_NOACTIVATE|SWP_NOZORDER|SWP_NOOWNERZORDER);
        return true;
    }
    bool Resize(UINT width,UINT height) {
        if(!swap_||!width||!height) return false;
        if(rtv_&&width==width_&&height==height_) return true;
        Hide();
        Ptr<ID3D11RenderTargetView> old;Ptr<ID3D11DepthStencilView> depth;
        context_->OMGetRenderTargets(1,&old,&depth);context_->OMSetRenderTargets(0,nullptr,nullptr);rtv_.Reset();
        HRESULT result=swap_->ResizeBuffers(0,width,height,DXGI_FORMAT_UNKNOWN,0);
        if(SUCCEEDED(result)) {
            Ptr<ID3D11Texture2D> back;
            result=swap_->GetBuffer(0,IID_PPV_ARGS(&back));
            if(SUCCEEDED(result)) result=device_->CreateRenderTargetView(back.Get(),nullptr,&rtv_);
        }
        ID3D11RenderTargetView* restore=old.Get();context_->OMSetRenderTargets(1,&restore,depth.Get());
        if(FAILED(result)) {error_="Capture layer resize failed. ESP/FOV hidden.";return false;}
        const float transparent[4]={0,0,0,0};
        context_->ClearRenderTargetView(rtv_.Get(),transparent);
        width_=width;height_=height;return true;
    }
    bool Render(ImDrawData* data) {
        if(!Ready()||!data) return false;
        Ptr<ID3D11RenderTargetView> old;Ptr<ID3D11DepthStencilView> depth;
        context_->OMGetRenderTargets(1,&old,&depth);
        ID3D11RenderTargetView* output=rtv_.Get();context_->OMSetRenderTargets(1,&output,nullptr);
        const float clear[4]={0,0,0,0};context_->ClearRenderTargetView(rtv_.Get(),clear);
        ImGui_ImplDX11_RenderDrawData(data);
        const HRESULT result=swap_->Present(0,0);
        output=old.Get();context_->OMSetRenderTargets(1,&output,depth.Get());
        if(FAILED(result)) {Hide();error_="Capture layer presentation failed. ESP/FOV hidden.";return false;}
        HWND game=game_.load();HWND root=game?GetAncestor(game,GA_ROOT):nullptr;
        if(root&&!IsIconic(root)&&GetForegroundWindow()==root&&!IsWindowVisible(Window()))
            ShowWindow(Window(),SW_SHOWNOACTIVATE);
        return true;
    }
    void Shutdown() {
        stopping_.store(true);
        Hide();
        visual_.Reset();target_.Reset();composition_.Reset();rtv_.Reset();swap_.Reset();
        context_.Reset();device_.Reset();
        if(HWND hwnd=Window()) PostMessageW(hwnd,WM_CLOSE,0,0);
        if(thread_) {WaitForSingleObject(thread_,INFINITE);CloseHandle(thread_);thread_=nullptr;}
        if(ready_) {CloseHandle(ready_);ready_=nullptr;}
        window_.store(nullptr);game_.store(nullptr);width_=height_=1;
    }
};
