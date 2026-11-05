#define _WIN32_WINNT 0x0A00
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX

#include <windows.h>
#include <d3d11.h>
#include <dxgi.h>
#include <dwmapi.h>
#include <tlhelp32.h>
#include <shellapi.h>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cfloat>
#include <string>
#include <vector>
#include <deque>
#include <mutex>
#include <atomic>
#include <thread>
#include <chrono>

#include <sstream>
#include <algorithm>
#include <cmath>
#include <windowsx.h>

#include "ui34/ui_renderer.hpp"

#pragma comment(lib, "d3d11.lib")
#pragma comment(lib, "dxgi.lib")
#pragma comment(lib, "dwmapi.lib")
#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "advapi32.lib")
#pragma comment(lib, "user32.lib")

namespace {

constexpr const wchar_t* kBrandW = L"CiyE";
constexpr const wchar_t* kVersionW = L"v2.1";
constexpr const wchar_t* kGame = L"BloodStrike.exe";
constexpr uint8_t kMagic[8] = {'B', 'S', 'L', 'D', 'P', 'A', 'Y', '1'};

// ---------------------------------------------------------------------------
// D3D / window state
// ---------------------------------------------------------------------------

ID3D11Device* g_device = nullptr;
ID3D11DeviceContext* g_context = nullptr;
IDXGISwapChain* g_swap = nullptr;
ID3D11RenderTargetView* g_rtv = nullptr;
HWND g_hwnd = nullptr;
bool g_running = true;

constexpr float kWindowW = 760.0f;
constexpr float kWindowH = 480.0f;
constexpr float kTitlebarH = 44.0f;
constexpr float kTitlebarButtonsW = 84.0f;

void CreateRenderTarget() {
    ID3D11Texture2D* back = nullptr;
    if (SUCCEEDED(g_swap->GetBuffer(0, __uuidof(ID3D11Texture2D), (void**)&back)) && back) {
        g_device->CreateRenderTargetView(back, nullptr, &g_rtv);
        back->Release();
    }
}

void CleanupRenderTarget() {
    if (g_rtv) {
        g_rtv->Release();
        g_rtv = nullptr;
    }
}

bool CreateDeviceD3D(HWND hwnd) {
    DXGI_SWAP_CHAIN_DESC sd{};
    sd.BufferCount = 2;
    sd.BufferDesc.Width = (UINT)kWindowW;
    sd.BufferDesc.Height = (UINT)kWindowH;
    sd.BufferDesc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;  // D2D needs BGRA
    sd.BufferDesc.RefreshRate.Numerator = 60;
    sd.BufferDesc.RefreshRate.Denominator = 1;
    sd.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
    sd.OutputWindow = hwnd;
    sd.SampleDesc.Count = 1;
    sd.Windowed = TRUE;
    sd.SwapEffect = DXGI_SWAP_EFFECT_DISCARD;

    const D3D_FEATURE_LEVEL levels[] = {D3D_FEATURE_LEVEL_11_0, D3D_FEATURE_LEVEL_10_0};
    D3D_FEATURE_LEVEL got;
    HRESULT hr = D3D11CreateDeviceAndSwapChain(
        nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr, D3D11_CREATE_DEVICE_BGRA_SUPPORT, levels, 2,
        D3D11_SDK_VERSION, &sd, &g_swap, &g_device, &got, &g_context);
    if (hr == DXGI_ERROR_UNSUPPORTED) {
        hr = D3D11CreateDeviceAndSwapChain(nullptr, D3D_DRIVER_TYPE_WARP, nullptr,
                                           D3D11_CREATE_DEVICE_BGRA_SUPPORT, levels, 2,
                                           D3D11_SDK_VERSION, &sd, &g_swap, &g_device, &got,
                                           &g_context);
    }
    if (FAILED(hr)) return false;
    CreateRenderTarget();
    return true;
}

void CleanupDeviceD3D() {
    CleanupRenderTarget();
    if (g_swap) {
        g_swap->Release();
        g_swap = nullptr;
    }
    if (g_context) {
        g_context->Release();
        g_context = nullptr;
    }
    if (g_device) {
        g_device->Release();
        g_device = nullptr;
    }
}

// ---------------------------------------------------------------------------
// Logging
// ---------------------------------------------------------------------------

std::mutex g_log_mutex;
std::deque<std::string> g_log_lines;
std::atomic<int> g_log_seq{0};

void Log(const std::string& msg) {
    SYSTEMTIME st{};
    GetLocalTime(&st);
    char head[24];
    sprintf_s(head, "[%02d:%02d:%02d] ", st.wHour, st.wMinute, st.wSecond);
    std::lock_guard<std::mutex> lock(g_log_mutex);
    g_log_lines.push_back(head + msg);
    while (g_log_lines.size() > 800) g_log_lines.pop_front();
    g_log_seq.fetch_add(1);
}

// ---------------------------------------------------------------------------
// Strings / files
// ---------------------------------------------------------------------------

std::wstring Utf8ToWide(const std::string& s) {
    if (s.empty()) return {};
    int n = MultiByteToWideChar(CP_UTF8, 0, s.data(), (int)s.size(), nullptr, 0);
    std::wstring out(n > 0 ? n : 0, L'\0');
    if (n > 0) MultiByteToWideChar(CP_UTF8, 0, s.data(), (int)s.size(), &out[0], n);
    return out;
}

std::string WideToUtf8(const std::wstring& s) {
    if (s.empty()) return {};
    int n = WideCharToMultiByte(CP_UTF8, 0, s.data(), (int)s.size(), nullptr, 0, nullptr, nullptr);
    std::string out(n > 0 ? n : 0, '\0');
    if (n > 0) WideCharToMultiByte(CP_UTF8, 0, s.data(), (int)s.size(), &out[0], n, nullptr, nullptr);
    return out;
}

std::wstring SelfPath() {
    wchar_t path[MAX_PATH]{};
    GetModuleFileNameW(nullptr, path, MAX_PATH);
    return path;
}

std::wstring SelfDir() {
    std::wstring p = SelfPath();
    size_t pos = p.find_last_of(L"\\/");
    return pos == std::wstring::npos ? L"." : p.substr(0, pos);
}

bool ReadFileBytes(const std::wstring& path, std::vector<uint8_t>& out) {
    HANDLE f = CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE,
                           nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (f == INVALID_HANDLE_VALUE) return false;
    LARGE_INTEGER size{};
    if (!GetFileSizeEx(f, &size) || size.QuadPart <= 0 || size.QuadPart > (1ll << 30)) {
        CloseHandle(f);
        return false;
    }
    out.resize((size_t)size.QuadPart);
    DWORD read = 0;
    BOOL ok = ReadFile(f, out.data(), (DWORD)out.size(), &read, nullptr);
    CloseHandle(f);
    return ok && read == out.size();
}

bool WriteFileBytes(const std::wstring& path, const std::vector<uint8_t>& data) {
    HANDLE f = CreateFileW(path.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS,
                           FILE_ATTRIBUTE_NORMAL, nullptr);
    if (f == INVALID_HANDLE_VALUE) return false;
    DWORD wrote = 0;
    BOOL ok = WriteFile(f, data.data(), (DWORD)data.size(), &wrote, nullptr);
    CloseHandle(f);
    return ok && wrote == data.size();
}

// ---------------------------------------------------------------------------
// Embedded payload
// ---------------------------------------------------------------------------

struct PayloadEntry {
    std::string name;
    std::vector<uint8_t> data;
};

bool LoadPayload(std::vector<PayloadEntry>& out) {
    std::vector<uint8_t> file;
    if (!ReadFileBytes(SelfPath(), file)) return false;
    if (file.size() < 16) return false;

    const uint8_t* foot = file.data() + file.size() - 16;
    if (memcmp(foot, kMagic, 8) != 0) return false;

    uint64_t payload_size = 0;
    memcpy(&payload_size, foot + 8, 8);
    if (payload_size == 0 || payload_size > file.size() - 16) return false;

    const size_t body_end = file.size() - 16;
    size_t pos = body_end - (size_t)payload_size;

    while (pos + 4 <= body_end) {
        uint32_t name_len = 0;
        memcpy(&name_len, file.data() + pos, 4);
        pos += 4;
        if (name_len == 0 || name_len > 512 || pos + name_len > body_end) return false;

        std::string name((const char*)file.data() + pos, name_len);
        pos += name_len;

        if (pos + 8 > body_end) return false;
        uint64_t data_len = 0;
        memcpy(&data_len, file.data() + pos, 8);
        pos += 8;
        if (data_len > body_end || pos + (size_t)data_len > body_end) return false;

        PayloadEntry entry;
        entry.name = std::move(name);
        entry.data.assign(file.begin() + pos, file.begin() + pos + (size_t)data_len);
        pos += (size_t)data_len;
        out.push_back(std::move(entry));
    }
    return !out.empty();
}

std::wstring MakeExtractDir() {
    wchar_t tmp[MAX_PATH]{};
    GetTempPathW(MAX_PATH, tmp);
    std::wstring base = std::wstring(tmp) + L"CiyE_BSLoader";
    CreateDirectoryW(base.c_str(), nullptr);
    return base;
}

void WriteRootHint(const std::wstring& base, const std::wstring& used) {
    std::vector<uint8_t> bytes((const uint8_t*)used.data(),
                               (const uint8_t*)(used.data() + used.size()));
    WriteFileBytes(base + L"\\root.txt", bytes);
}

bool ExtractPayload(const std::vector<PayloadEntry>& entries, const std::wstring& dir,
                    std::wstring& used_dir) {
    auto ensure = [](const std::wstring& p) { CreateDirectoryW(p.c_str(), nullptr); };
    ensure(dir);
    ensure(dir + L"\\pyexec");
    ensure(dir + L"\\driver");
    ensure(dir + L"\\ipc");

    // If a previously injected copy still holds the DLLs, use a fresh sibling dir.
    std::wstring target = dir;
    if (GetFileAttributesW((dir + L"\\bs_pyexec.dll").c_str()) != INVALID_FILE_ATTRIBUTES) {
        HANDLE probe = CreateFileW((dir + L"\\bs_pyexec.dll").c_str(), GENERIC_WRITE, 0, nullptr,
                                   OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (probe == INVALID_HANDLE_VALUE) {
            char suffix[32];
            sprintf_s(suffix, "_%lu", (unsigned long)GetCurrentProcessId());
            target = dir + Utf8ToWide(suffix);
            ensure(target);
            ensure(target + L"\\pyexec");
            ensure(target + L"\\driver");
            ensure(target + L"\\ipc");
        } else {
            CloseHandle(probe);
        }
    }

    for (const PayloadEntry& entry : entries) {
        std::wstring rel = Utf8ToWide(entry.name);
        for (wchar_t& ch : rel) {
            if (ch == L'/') ch = L'\\';
        }
        std::wstring path = target + L"\\" + rel;
        size_t slash = path.find_last_of(L'\\');
        if (slash != std::wstring::npos) ensure(path.substr(0, slash));
        if (!WriteFileBytes(path, entry.data)) {
            Log("write failed: " + entry.name);
            return false;
        }
    }
    used_dir = target;
    return true;
}

// ---------------------------------------------------------------------------
// Process / injection primitives
// ---------------------------------------------------------------------------

using NtCreateThreadExFn = LONG(WINAPI*)(PHANDLE, ACCESS_MASK, PVOID, HANDLE, PVOID, PVOID,
                                        ULONG, SIZE_T, SIZE_T, SIZE_T, PVOID);

struct ProcessBasicInformation {
    PVOID Reserved1;
    PVOID PebBaseAddress;
    PVOID Reserved2[2];
    ULONG_PTR UniqueProcessId;
    PVOID Reserved3;
};
using NtQueryInformationProcessFn = LONG(WINAPI*)(HANDLE, ULONG, PVOID, ULONG, PULONG);

struct UnicodeStringRef {
    USHORT Length;
    USHORT MaximumLength;
    PWSTR Buffer;
};

struct LdrEntry {
    LIST_ENTRY InLoadOrderLinks;
    LIST_ENTRY InMemoryOrderLinks;
    LIST_ENTRY InInitializationOrderLinks;
    PVOID DllBase;
    PVOID EntryPoint;
    ULONG SizeOfImage;
    UnicodeStringRef FullDllName;
    UnicodeStringRef BaseDllName;
};

DWORD FindProcess(const wchar_t* name) {
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snap == INVALID_HANDLE_VALUE) return 0;
    PROCESSENTRY32W entry{};
    entry.dwSize = sizeof(entry);
    DWORD pid = 0;
    if (Process32FirstW(snap, &entry)) {
        do {
            if (_wcsicmp(entry.szExeFile, name) == 0) {
                pid = entry.th32ProcessID;
                break;
            }
        } while (Process32NextW(snap, &entry));
    }
    CloseHandle(snap);
    return pid;
}

DWORD WaitForProcess(const wchar_t* name, int seconds) {
    int tries = seconds > 0 ? seconds * 2 : 1;
    for (int i = 0; i < tries; ++i) {
        DWORD pid = FindProcess(name);
        if (pid) return pid;
        Sleep(500);
    }
    return 0;
}

bool EnableDebugPrivilege() {
    HANDLE token = nullptr;
    if (!OpenProcessToken(GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, &token))
        return false;
    LUID luid{};
    if (!LookupPrivilegeValueW(nullptr, L"SeDebugPrivilege", &luid)) {
        CloseHandle(token);
        return false;
    }
    TOKEN_PRIVILEGES tp{};
    tp.PrivilegeCount = 1;
    tp.Privileges[0].Luid = luid;
    tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED;
    BOOL ok = AdjustTokenPrivileges(token, FALSE, &tp, sizeof(tp), nullptr, nullptr);
    DWORD err = GetLastError();
    CloseHandle(token);
    return ok && err == ERROR_SUCCESS;
}

template <typename T>
bool ReadMem(HANDLE process, uintptr_t address, T& out) {
    SIZE_T got = 0;
    return ReadProcessMemory(process, reinterpret_cast<LPCVOID>(address), &out, sizeof(T), &got) &&
           got == sizeof(T);
}

template <typename T>
bool WriteMem(HANDLE process, uintptr_t address, const T& in) {
    SIZE_T put = 0;
    return WriteProcessMemory(process, reinterpret_cast<LPVOID>(address), &in, sizeof(T), &put) &&
           put == sizeof(T);
}

uintptr_t QueryPeb(HANDLE process) {
    HMODULE ntdll = GetModuleHandleW(L"ntdll.dll");
    if (!ntdll) return 0;
    auto query = reinterpret_cast<NtQueryInformationProcessFn>(
        GetProcAddress(ntdll, "NtQueryInformationProcess"));
    if (!query) return 0;
    ProcessBasicInformation info{};
    ULONG size = 0;
    LONG status = query(process, 0, &info, sizeof(info), &size);
    return status == 0 ? reinterpret_cast<uintptr_t>(info.PebBaseAddress) : 0;
}

bool ReadRemoteWide(HANDLE process, const UnicodeStringRef& str, std::wstring& out) {
    if (!str.Buffer || str.Length == 0) return false;
    wchar_t buf[512]{};
    SIZE_T bytes = str.Length;
    if (bytes > sizeof(buf) - sizeof(wchar_t)) bytes = sizeof(buf) - sizeof(wchar_t);
    SIZE_T got = 0;
    if (!ReadProcessMemory(process, str.Buffer, buf, bytes, &got) || got == 0) return false;
    buf[bytes / sizeof(wchar_t)] = 0;
    out.assign(buf);
    return true;
}

uintptr_t FindModuleBase(HANDLE process, uintptr_t peb, const std::wstring& module_name) {
    if (!peb) return 0;
    uintptr_t ldr = 0;
    if (!ReadMem(process, peb + 0x18, ldr) || !ldr) return 0;
    uintptr_t head = ldr + 0x10;
    uintptr_t cursor = 0;
    if (!ReadMem(process, head, cursor)) return 0;
    for (int guard = 0; guard < 2048 && cursor && cursor != head; ++guard) {
        LdrEntry entry{};
        if (!ReadMem(process, cursor - 0x10, entry)) return 0;
        std::wstring name;
        if (ReadRemoteWide(process, entry.BaseDllName, name) &&
            _wcsicmp(name.c_str(), module_name.c_str()) == 0) {
            return reinterpret_cast<uintptr_t>(entry.DllBase);
        }
        uintptr_t next = 0;
        if (!ReadMem(process, cursor, next)) return 0;
        cursor = next;
    }
    return 0;
}

void ZeroRemoteString(HANDLE process, const UnicodeStringRef& str) {
    if (!str.Buffer || str.Length == 0) return;
    std::vector<BYTE> zeros(str.Length, 0);
    SIZE_T put = 0;
    WriteProcessMemory(process, str.Buffer, zeros.data(), zeros.size(), &put);
}

bool HideModuleFromPeb(HANDLE process, uintptr_t module_base, uintptr_t peb) {
    if (!module_base || !peb) return false;
    uintptr_t ldr = 0;
    if (!ReadMem(process, peb + 0x18, ldr) || !ldr) return false;
    uintptr_t head = ldr + 0x10;
    uintptr_t cursor = 0;
    if (!ReadMem(process, head, cursor)) return false;

    for (int guard = 0; guard < 2048 && cursor && cursor != head; ++guard) {
        uintptr_t entry_address = cursor - 0x10;
        LdrEntry entry{};
        if (!ReadMem(process, entry_address, entry)) return false;
        if (reinterpret_cast<uintptr_t>(entry.DllBase) == module_base) {
            const uintptr_t links[3] = {entry_address, entry_address + 0x10, entry_address + 0x20};
            for (uintptr_t link_address : links) {
                LIST_ENTRY link{};
                if (!ReadMem(process, link_address, link)) continue;
                uintptr_t prev = reinterpret_cast<uintptr_t>(link.Blink);
                uintptr_t next = reinterpret_cast<uintptr_t>(link.Flink);
                if (!prev || !next) continue;
                WriteMem(process, prev, next);
                WriteMem(process, next + 8, prev);
            }
            ZeroRemoteString(process, entry.BaseDllName);
            ZeroRemoteString(process, entry.FullDllName);
            return true;
        }
        uintptr_t next = 0;
        if (!ReadMem(process, cursor, next)) return false;
        cursor = next;
    }
    return false;
}

HANDLE CreateHiddenThread(HANDLE process, void* start, void* arg) {
    HMODULE ntdll = GetModuleHandleW(L"ntdll.dll");
    if (ntdll) {
        auto create = reinterpret_cast<NtCreateThreadExFn>(GetProcAddress(ntdll, "NtCreateThreadEx"));
        if (create) {
            HANDLE thread = nullptr;
            constexpr ULONG kHideFromDebugger = 0x4;
            LONG status = create(&thread, THREAD_ALL_ACCESS, nullptr, process, start, arg,
                                 kHideFromDebugger, 0, 0, 0, nullptr);
            if (status == 0 && thread) return thread;
        }
    }
    return CreateRemoteThread(process, nullptr, 0,
                              reinterpret_cast<LPTHREAD_START_ROUTINE>(start), arg, 0, nullptr);
}

HANDLE OpenProcessProgressive(DWORD pid, DWORD& granted) {
    const DWORD masks[] = {
        PROCESS_CREATE_THREAD | PROCESS_QUERY_INFORMATION | PROCESS_VM_OPERATION |
            PROCESS_VM_WRITE | PROCESS_VM_READ,
        PROCESS_CREATE_THREAD | PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_OPERATION |
            PROCESS_VM_WRITE | PROCESS_VM_READ,
        PROCESS_VM_OPERATION | PROCESS_VM_WRITE | PROCESS_VM_READ |
            PROCESS_QUERY_LIMITED_INFORMATION,
        PROCESS_VM_OPERATION | PROCESS_VM_READ | PROCESS_QUERY_LIMITED_INFORMATION,
        PROCESS_QUERY_LIMITED_INFORMATION,
    };
    granted = 0;
    for (DWORD mask : masks) {
        HANDLE handle = OpenProcess(mask, FALSE, pid);
        if (handle) {
            granted = mask;
            return handle;
        }
    }
    return nullptr;
}

bool InjectDll(DWORD pid, const std::wstring& dll_path, bool hide) {
    if (GetFileAttributesW(dll_path.c_str()) == INVALID_FILE_ATTRIBUTES) {
        Log("missing dll: " + WideToUtf8(dll_path));
        return false;
    }

    DWORD granted = 0;
    HANDLE process = OpenProcessProgressive(pid, granted);
    if (!process) {
        Log("OpenProcess denied (HyperShield?)");
        return false;
    }
    const DWORD needed =
        PROCESS_CREATE_THREAD | PROCESS_VM_OPERATION | PROCESS_VM_WRITE | PROCESS_VM_READ;
    if ((granted & needed) != needed) {
        Log("handle rights stripped (have=" + std::to_string(granted) + ")");
        CloseHandle(process);
        return false;
    }

    const SIZE_T path_bytes = (dll_path.size() + 1) * sizeof(wchar_t);
    void* remote = VirtualAllocEx(process, nullptr, path_bytes, MEM_COMMIT | MEM_RESERVE,
                                  PAGE_READWRITE);
    if (!remote) {
        Log("VirtualAllocEx failed");
        CloseHandle(process);
        return false;
    }
    if (!WriteProcessMemory(process, remote, dll_path.c_str(), path_bytes, nullptr)) {
        Log("WriteProcessMemory failed");
        VirtualFreeEx(process, remote, 0, MEM_RELEASE);
        CloseHandle(process);
        return false;
    }

    HMODULE kernel32 = GetModuleHandleW(L"kernel32.dll");
    void* load_library = reinterpret_cast<void*>(GetProcAddress(kernel32, "LoadLibraryW"));
    HANDLE thread = CreateHiddenThread(process, load_library, remote);
    if (!thread) {
        Log("CreateRemoteThread failed");
        VirtualFreeEx(process, remote, 0, MEM_RELEASE);
        CloseHandle(process);
        return false;
    }

    DWORD wait = WaitForSingleObject(thread, 15000);
    DWORD exit_code = 0;
    GetExitCodeThread(thread, &exit_code);
    CloseHandle(thread);
    VirtualFreeEx(process, remote, 0, MEM_RELEASE);

    std::wstring module_name = dll_path.substr(dll_path.find_last_of(L"\\/") + 1);
    uintptr_t peb = QueryPeb(process);
    uintptr_t module_base = FindModuleBase(process, peb, module_name);
    if (!module_base && wait == WAIT_OBJECT_0 && exit_code) module_base = exit_code;
    if (!module_base) {
        Log("injection failed: module not present");
        CloseHandle(process);
        return false;
    }

    bool hidden = false;
    if (hide) hidden = HideModuleFromPeb(process, module_base, peb);
    CloseHandle(process);

    char buf[96];
    sprintf_s(buf, "injected %ls base=0x%llx%s", module_name.c_str(),
              (unsigned long long)module_base, hidden ? " (hidden)" : "");
    Log(buf);
    return true;
}

// ---------------------------------------------------------------------------
// Driver path
// ---------------------------------------------------------------------------

bool DriverDeviceReady() {
    HANDLE h = CreateFileW(L"\\\\.\\WinSyncDrv", GENERIC_READ | GENERIC_WRITE,
                           FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr, OPEN_EXISTING, 0, nullptr);
    if (h == INVALID_HANDLE_VALUE) return false;
    CloseHandle(h);
    return true;
}

bool RunAndWait(const std::wstring& exe, const std::wstring& args, const std::wstring& cwd,
                DWORD timeout_ms, DWORD& exit_code) {
    if (GetFileAttributesW(exe.c_str()) == INVALID_FILE_ATTRIBUTES) return false;

    std::wstring cmdline = L"\"" + exe + L"\"";
    if (!args.empty()) cmdline += L" " + args;

    HANDLE hRead = nullptr, hWrite = nullptr;
    SECURITY_ATTRIBUTES sa{};
    sa.nLength = sizeof(sa);
    sa.bInheritHandle = TRUE;
    CreatePipe(&hRead, &hWrite, &sa, 0);
    SetHandleInformation(hRead, HANDLE_FLAG_INHERIT, 0);

    STARTUPINFOW si{};
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW | (hWrite ? STARTF_USESTDHANDLES : 0);
    si.wShowWindow = SW_HIDE;
    si.hStdOutput = hWrite;
    si.hStdError = hWrite;
    PROCESS_INFORMATION pi{};

    std::vector<wchar_t> mutable_cmd(cmdline.begin(), cmdline.end());
    mutable_cmd.push_back(0);

    BOOL ok = CreateProcessW(exe.c_str(), mutable_cmd.data(), nullptr, nullptr, TRUE,
                             CREATE_NO_WINDOW, nullptr, cwd.c_str(), &si, &pi);
    if (hWrite) CloseHandle(hWrite);

    if (!ok) {
        if (hRead) CloseHandle(hRead);
        return false;
    }

    DWORD wait = WaitForSingleObject(pi.hProcess, timeout_ms);
    exit_code = 1;
    GetExitCodeProcess(pi.hProcess, &exit_code);
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);

    if (hRead) {
        char buf[1024];
        DWORD read = 0;
        std::string accumulated;
        while (ReadFile(hRead, buf, sizeof(buf) - 1, &read, nullptr) && read > 0) {
            buf[read] = 0;
            accumulated += buf;
        }
        CloseHandle(hRead);

        size_t start = 0;
        while (start < accumulated.size()) {
            size_t end = accumulated.find_first_of("\r\n", start);
            if (end == std::string::npos) end = accumulated.size();
            if (end > start) {
                std::string line = accumulated.substr(start, end - start);
                if (!line.empty() && line != "\r") {
                    Log("  > " + line);
                }
            }
            start = end + 1;
        }
    }

    return wait == WAIT_OBJECT_0;
}

bool LoadKernelDriver(const std::wstring& dir) {
    std::wstring drv_dir = dir + L"\\driver";
    std::wstring kdmapper = drv_dir + L"\\kdmapper.exe";
    std::wstring sys = drv_dir + L"\\bskdrv.sys";
    if (GetFileAttributesW(kdmapper.c_str()) == INVALID_FILE_ATTRIBUTES ||
        GetFileAttributesW(sys.c_str()) == INVALID_FILE_ATTRIBUTES) {
        Log("driver payload not embedded");
        return false;
    }
    Log("loading kernel driver via kdmapper...");
    DWORD code = 1;
    std::wstring sys_arg = L"\"" + sys + L"\"";
    RunAndWait(kdmapper, sys_arg, drv_dir, 20000, code);
    for (int i = 0; i < 10; ++i) {
        if (DriverDeviceReady()) {
            Log("kernel driver ready");
            return true;
        }
        Sleep(500);
    }
    Log("kernel driver did not respond");
    return false;
}

bool MapViaDriver(const std::wstring& dir, DWORD pid, const std::wstring& pyexec,
                  const std::wstring& overlay) {
    (void)pid;
    std::wstring bsmap = dir + L"\\bsmap.exe";
    if (GetFileAttributesW(bsmap.c_str()) == INVALID_FILE_ATTRIBUTES) {
        Log("bsmap.exe not embedded");
        return false;
    }
    std::wstring args = L"\"" + std::wstring(kGame) + L"\" \"" + pyexec + L"\" \"" + overlay + L"\"";
    Log("mapping modules through kernel driver...");
    DWORD code = 1;
    RunAndWait(bsmap, args, dir, 30000, code);
    char buf[64];
    sprintf_s(buf, "bsmap exit=%lu", (unsigned long)code);
    Log(buf);
    return code == 0;
}

// ---------------------------------------------------------------------------
// Worker state
// ---------------------------------------------------------------------------

enum Phase { kIdle = 0, kWaiting = 1, kInjecting = 2, kReady = 3, kFailed = 4 };

std::atomic<int> g_phase{kIdle};
std::atomic<unsigned long> g_pid{0};
std::atomic<bool> g_busy{false};
std::atomic<bool> g_driver_mode{false};
std::atomic<bool> g_used_driver{false};
std::atomic<unsigned long> g_live_pid{0};
std::atomic<bool> g_auto_inject{false};
std::atomic<bool> g_close_on_done{false};

void InjectWorker(bool driver_mode) {
    g_busy.store(true);
    g_phase.store(kWaiting);

    Log("reading embedded payload...");
    std::vector<PayloadEntry> payload;
    if (!LoadPayload(payload)) {
        Log("payload missing - rebuild with pack_loader");
        g_phase.store(kFailed);
        g_busy.store(false);
        return;
    }

    std::wstring dir;
    std::wstring base = MakeExtractDir();
    if (!ExtractPayload(payload, base, dir)) {
        Log("payload extraction failed");
        g_phase.store(kFailed);
        g_busy.store(false);
        return;
    }
    WriteRootHint(base, dir);
    Log("payload ready (" + std::to_string(payload.size()) + " files)");

    std::wstring pyexec = dir + L"\\bs_pyexec.dll";
    std::wstring overlay = dir + L"\\bs_overlay.dll";

    Log("waiting for BloodStrike.exe (up to 90s)...");
    DWORD pid = WaitForProcess(kGame, 90);
    if (!pid) {
        Log("game not found - start it and press INJECT again");
        g_phase.store(kFailed);
        g_busy.store(false);
        return;
    }
    g_pid.store(pid);
    char buf[64];
    sprintf_s(buf, "found BloodStrike.exe pid=%lu", (unsigned long)pid);
    Log(buf);

    if (!EnableDebugPrivilege()) Log("warning: SeDebugPrivilege not enabled (run as admin)");

    g_phase.store(kInjecting);
    bool ok = false;

    if (driver_mode) {
        g_used_driver.store(true);
        if (!DriverDeviceReady()) LoadKernelDriver(dir);
        if (DriverDeviceReady()) ok = MapViaDriver(dir, pid, pyexec, overlay);
        if (!ok) {
            Log("driver path unavailable - falling back to usermode");
            g_used_driver.store(false);
        }
    }

    if (!ok) {
        Log("injecting python bridge...");
        ok = InjectDll(pid, pyexec, true);
        if (ok) {
            Log("waiting for runtime boot...");
            Sleep(2000);
            Log("injecting overlay...");
            ok = InjectDll(pid, overlay, true);
        }
    }

    if (ok) {
        Log("done - press INSERT in game to open the menu");
        g_phase.store(kReady);
    } else {
        Log("injection failed");
        g_phase.store(kFailed);
    }
    g_busy.store(false);
}

// ---------------------------------------------------------------------------
// UI - 34Cheat visual language (D2D immediate mode)
// ---------------------------------------------------------------------------

constexpr float kPi34 = 3.14159265f;

std::wstring Utf8ToWideL(const std::string& s) {
    if (s.empty()) return {};
    int n = MultiByteToWideChar(CP_UTF8, 0, s.data(), (int)s.size(), nullptr, 0);
    std::wstring out(n > 0 ? n : 0, L'\0');
    if (n > 0) MultiByteToWideChar(CP_UTF8, 0, s.data(), (int)s.size(), &out[0], n);
    return out;
}

enum StepStatus { StepPending, StepWorking, StepCompleted, StepFailed };

struct PipelineStep {
    std::wstring Title;
    std::wstring Detail;
    StepStatus Status{StepPending};
};

std::vector<PipelineStep> g_steps;
int g_current_step = 0;
float g_target_progress = 0.0f;
float g_shown_progress = 0.0f;
float g_intro_time = 0.0f;
bool g_intro_done = false;
float g_ready_time = 0.0f;
std::wstring g_hwid;

void BuildSteps(bool driver) {
    g_steps.clear();
    g_steps.push_back({ L"Payload",     L"Extracting embedded modules", StepWorking });
    if (driver) {
        g_steps.push_back({ L"Driver",  L"Mapping kernel driver",       StepPending });
    }
    g_steps.push_back({ L"BloodStrike", L"Waiting for BloodStrike.exe", StepPending });
    g_steps.push_back({ L"Inject",      L"Loading overlay into the game", StepPending });
    g_current_step = 0;
    g_target_progress = 0.0f;
    g_shown_progress = 0.0f;
}

void InitSteps() {
    BuildSteps(g_driver_mode.load());
    DWORD serial = 0;
    GetVolumeInformationA("C:\\", nullptr, 0, &serial, nullptr, nullptr, nullptr, 0);
    wchar_t buf[16];
    swprintf_s(buf, L"%08X", serial);
    g_hwid = buf;
}

float Phase34(float t, float from, float to) {
    float x = (t - from) / (to - from);
    if (x < 0) x = 0; if (x > 1) x = 1; return x;
}
float EaseOut34(float x) { return 1.0f - (1.0f - x) * (1.0f - x) * (1.0f - x); }
float EaseInOut34(float x) { return x < 0.5f ? 4.0f * x * x * x : 1.0f - std::pow(-2.0f * x + 2.0f, 3.0f) / 2.0f; }

constexpr float kIntroExit34 = 2.85f;
constexpr float kIntroEnd34 = 3.30f;

void RenderStep34(const PipelineStep& step, const Math::Vector2& pos, float width, bool last) {
    auto& ui = UI::g_UI;
    const auto& c = ui.GetColors();
    const float rowH = 58.0f;
    Math::Vector2 marker{pos.x + 10.0f, pos.y + 11.0f};

    if (!last) {
        ui.DrawLine({marker.x, marker.y + 14.0f}, {marker.x, pos.y + rowH + 1.0f},
            step.Status == StepCompleted ? UI::WithAlpha(c.Success, 0.45f) : c.BorderSubtle, 1.5f);
    }
    D2D1_COLOR_F titleColor = c.TextPrimary;
    switch (step.Status) {
    case StepCompleted:
        ui.FillCircle(marker, 9.0f, c.Success);
        ui.DrawIcon(UI::Icon::Check, marker, 10.0f, D2D1::ColorF(0x0F1012, 1.0f));
        break;
    case StepWorking:
        ui.DrawCircle(marker, 8.0f, c.BorderSubtle, 2.0f);
        ui.DrawArc(marker, 8.0f, ui.Time() * 5.0f, kPi34 * 1.2f, c.Accent, 2.0f);
        break;
    case StepFailed:
        ui.FillCircle(marker, 9.0f, c.Danger);
        ui.DrawIcon(UI::Icon::Cross, marker, 9.0f, D2D1::ColorF(0xFFFFFF, 1.0f));
        break;
    case StepPending:
        ui.DrawCircle(marker, 8.0f, c.BorderHover, 1.5f);
        titleColor = c.TextTertiary;
        break;
    }
    float textX = pos.x + 34.0f;
    ui.DrawText(step.Title, {textX, pos.y + 1.0f}, {width - 34.0f, 20.0f}, titleColor, UI::FontBold);
    ui.DrawText(step.Detail, {textX, pos.y + 21.0f}, {width - 34.0f, 18.0f},
        step.Status == StepFailed ? c.Danger : c.TextSecondary, UI::FontSmall);
}

void RenderStatusMark34(const Math::Vector2& pos, float size, bool ready, bool failed) {
    auto& ui = UI::g_UI;
    const auto& colors = ui.GetColors();
    const Math::Vector2 c{pos.x + size * 0.5f, pos.y + size * 0.5f};
    const float r = size * 0.5f + 7.0f;
    ui.DrawLogoMark(pos, size);
    if (failed) {
        ui.DrawCircle(c, r, UI::WithAlpha(colors.Danger, 0.7f), 1.5f);
    } else if (ready) {
        ui.DrawCircle(c, r, UI::WithAlpha(colors.Success, 0.7f), 1.5f);
    } else {
        const float spin = ui.Time() * 2.4f;
        ui.DrawCircle(c, r, colors.BorderSubtle, 1.5f);
        ui.DrawArc(c, r, spin, kPi34 * 0.55f, colors.Accent, 2.0f);
        ui.DrawArc(c, r, spin + kPi34, kPi34 * 0.55f, colors.Accent, 2.0f);
    }
}

void RenderIntro34(float exit) {
    auto& ui = UI::g_UI;
    const auto& colors = ui.GetColors();
    const float t = g_intro_time;
    const float W = kWindowW;
    const float fade = 1.0f - EaseInOut34(exit);
    const float lift = -EaseInOut34(exit) * 14.0f;
    ui.FillRect({0, 0}, {kWindowW, kWindowH}, UI::WithAlpha(colors.BgBase, fade));
    const float tile = 76.0f;
    const Math::Vector2 c{W * 0.5f, 158.0f + lift};
    const float open = EaseOut34(Phase34(t, 0.05f, 0.70f));
    const float fill = EaseOut34(Phase34(t, 0.45f, 0.95f));
    if (open > 0.0f && fill < 1.0f) {
        const float half = tile * 0.5f * (0.18f + 0.82f * open);
        const float rot = (1.0f - open) * kPi34 * 0.75f;
        std::vector<Math::Vector2> square;
        for (int i = 0; i < 4; ++i) {
            float a = rot + kPi34 * 0.25f + i * kPi34 * 0.5f;
            square.push_back({c.x + std::cos(a) * half * 1.41421f, c.y + std::sin(a) * half * 1.41421f});
        }
        ui.DrawPolygon(square, UI::WithAlpha(colors.Accent, open * (1.0f - fill) * fade), 2.0f);
    }
    if (fill > 0.0f) {
        if (fill < 1.0f) {
            const float s = tile * fill;
            ui.FillRoundedRect({c.x - s * 0.5f, c.y - s * 0.5f}, {s, s}, s * 0.28f, UI::WithAlpha(colors.Accent, fade));
        } else {
            ui.DrawLogoMark({c.x - tile * 0.5f, c.y - tile * 0.5f}, tile, Phase34(t, 0.80f, 1.55f), fade);
        }
    }
    const float orbit = EaseOut34(Phase34(t, 1.00f, 1.60f));
    if (orbit > 0.0f) {
        const float spin = t * 2.4f;
        const float r1 = tile * 0.5f + 16.0f + (1.0f - orbit) * 10.0f;
        const float r2 = tile * 0.5f + 25.0f + (1.0f - orbit) * 16.0f;
        const D2D1_COLOR_F inner = UI::WithAlpha(colors.Accent, 0.9f * orbit * fade);
        ui.DrawArc(c, r1, -kPi34 * 0.85f + spin, kPi34 * 0.62f * orbit, inner, 2.5f);
        ui.DrawArc(c, r1, kPi34 * 0.15f + spin, kPi34 * 0.62f * orbit, inner, 2.5f);
        ui.DrawArc(c, r2, kPi34 * 0.40f - spin * 0.7f, kPi34 * 0.45f * orbit, UI::WithAlpha(colors.Accent, 0.35f * orbit * fade), 1.5f);
    }
    const float word = EaseOut34(Phase34(t, 1.20f, 1.70f));
    if (word > 0.0f) {
        const float wy = 246.0f + lift + (1.0f - word) * 10.0f;
        const float wordW = ui.MeasureText(L"CiyE", UI::FontTitle);
        const float x = c.x - wordW * 0.5f;
        ui.DrawText(L"CiyE", {x, wy}, {wordW + 2.0f, 30.0f}, UI::WithAlpha(colors.TextPrimary, word * fade), UI::FontTitle);
        const float sub = EaseOut34(Phase34(t, 1.35f, 1.85f));
        ui.DrawText(L"BloodStrike internal", {c.x - 140.0f, wy + 30.0f}, {280.0f, 18.0f},
            UI::WithAlpha(colors.TextTertiary, sub * fade), UI::FontSmall, DWRITE_TEXT_ALIGNMENT_CENTER);
    }
    const float bar = EaseOut34(Phase34(t, 1.45f, 1.85f));
    if (bar > 0.0f) {
        const float barW = 220.0f;
        const float by = 328.0f + lift;
        const float progress = EaseInOut34(Phase34(t, 1.55f, 2.75f));
        ui.FillRoundedRect({c.x - barW * 0.5f, by}, {barW, 3.0f}, 1.5f, UI::WithAlpha(colors.BorderSubtle, colors.BorderSubtle.a * bar * fade));
        if (progress > 0.0f) {
            ui.FillRoundedRect({c.x - barW * 0.5f, by}, {barW * progress, 3.0f}, 1.5f, UI::WithAlpha(colors.Accent, bar * fade));
        }
        const wchar_t* status = progress < 0.45f ? L"Loading interface" : (progress < 0.97f ? L"Preparing startup" : L"Opening loader");
        ui.DrawText(status, {c.x - 140.0f, by + 12.0f}, {280.0f, 18.0f},
            UI::WithAlpha(colors.TextSecondary, bar * fade), UI::FontSmall, DWRITE_TEXT_ALIGNMENT_CENTER);
    }
}

void RenderTitleButtons34() {
    auto& ui = UI::g_UI;
    const float W = kWindowW;
    if (ui.RenderIconButton({W - 80.0f, 8.0f}, {32.0f, 28.0f}, UI::Icon::Minimize)) {
        ShowWindow(g_hwnd, SW_MINIMIZE);
    }
    if (ui.RenderIconButton({W - 44.0f, 8.0f}, {32.0f, 28.0f}, UI::Icon::Close, true)) {
        g_running = false;
    }
}

bool g_launch_requested = false;

// Pump pipeline forward based on actual bs-cheat phase from InjectWorker.
// Step indices depend on mode: user = [Payload, BloodStrike, Inject]; kernel = [Payload, Driver, BloodStrike, Inject].
void SyncStepsFromPhase() {
    int phase = g_phase.load();
    const bool driver = g_driver_mode.load();
    const int idxPayload = 0;
    const int idxDriver = driver ? 1 : -1;
    const int idxProc = driver ? 2 : 1;
    const int idxInject = driver ? 3 : 2;
    const int total = (int)g_steps.size();

    auto advance = [&](int target, float progress) {
        if (g_current_step <= target) {
            g_steps[g_current_step].Status = StepCompleted;
            g_current_step = target + 1;
            if (g_current_step < total) g_steps[g_current_step].Status = StepWorking;
            g_target_progress = progress;
        }
    };

    if (g_current_step == idxPayload && phase != kIdle) {
        g_steps[idxPayload].Detail = L"Embedded modules ready";
        advance(idxPayload, driver ? 0.2f : 0.3f);
    }
    if (idxDriver >= 0 && g_current_step == idxDriver && phase == kInjecting) {
        g_steps[idxDriver].Detail = g_used_driver.load() ? L"Kernel driver ready" : L"Driver skipped";
        advance(idxDriver, 0.45f);
    }
    if (g_current_step == idxProc) {
        DWORD pid = g_pid.load();
        if (pid) {
            wchar_t buf[48]; swprintf_s(buf, L"Attached PID %lu", (unsigned long)pid);
            g_steps[idxProc].Detail = buf;
            advance(idxProc, 0.75f);
        }
    }
    if (g_current_step == idxInject && phase == kReady) {
        g_steps[idxInject].Detail = g_used_driver.load() ? L"Mapped via driver" : L"Overlay injected";
        advance(idxInject, 1.0f);
    }
    if (phase == kFailed) {
        for (int i = 0; i < total; ++i) {
            if (g_steps[i].Status == StepWorking) {
                g_steps[i].Status = StepFailed;
                g_steps[i].Detail = L"See activity log";
                break;
            }
        }
    }
}

void RenderFrame34() {
    auto& ui = UI::g_UI;
    const auto& colors = ui.GetColors();
    const float W = kWindowW;
    const float H = kWindowH;

    ui.FillRect({0, 0}, {W, H}, colors.BgBase);

    // Title strip
    const float logoW = ui.DrawLogo({20.0f, 11.0f}, 22.0f);
    (void)logoW;
    {
        const std::wstring tag = std::wstring(kVersionW);
        const float tagW = ui.MeasureText(tag, UI::FontSmall) + 14.0f;
        const Math::Vector2 tagPos{20.0f + logoW + 10.0f, 13.0f};
        ui.FillRoundedRect(tagPos, {tagW, 18.0f}, 9.0f, colors.BgElevated);
        ui.DrawText(tag, tagPos, {tagW, 18.0f}, colors.TextTertiary, UI::FontSmall, DWRITE_TEXT_ALIGNMENT_CENTER);
    }
    ui.DrawLine({0, kTitlebarH}, {W, kTitlebarH}, colors.BorderSubtle, 1.0f);
    RenderTitleButtons34();

    const int phase = g_phase.load();
    const bool ready = phase == kReady;
    const bool failed = phase == kFailed;
    const bool busy = g_busy.load();

    const float leftX = 28.0f;
    const float leftW = 268.0f;

    std::wstring headline, line;
    if (failed) { headline = L"Setup stopped"; line = L"See the red step on the right."; }
    else if (ready) { headline = L"Session ready"; line = L"Press INSERT in game to open the menu."; }
    else if (g_current_step == 2) { headline = L"Waiting for BloodStrike"; line = L"Start Blood Strike to continue."; }
    else if (busy) { headline = L"Starting session"; line = L"This takes a few seconds."; }
    else { headline = L"Ready when you are"; line = L"Choose a mode and start the session."; }

    g_shown_progress = ui.Animate(UI::HashId(L"loader.progress"), 0, g_target_progress, 8.0f);

    RenderStatusMark34({leftX, 66.0f}, 40.0f, ready, failed);
    ui.DrawText(headline, {leftX, 120.0f}, {leftW, 30.0f}, colors.TextPrimary, UI::FontTitle);
    ui.DrawText(line, {leftX, 152.0f}, {leftW, 20.0f}, colors.TextSecondary, UI::FontBody);

    auto factRow = [&](float y, const std::wstring& label, const std::wstring& value) {
        ui.DrawLine({leftX, y}, {leftX + leftW, y}, colors.BorderSubtle, 1.0f);
        ui.DrawText(label, {leftX, y + 1.0f}, {110.0f, 32.0f}, colors.TextTertiary, UI::FontBody);
        ui.DrawText(value, {leftX + 110.0f, y + 1.0f}, {leftW - 110.0f, 32.0f}, colors.TextPrimary, UI::FontMono, DWRITE_TEXT_ALIGNMENT_TRAILING);
    };
    const bool driver = g_driver_mode.load();
    DWORD live = g_live_pid.load();
    DWORD pid = g_pid.load(); if (!pid) pid = live;
    factRow(190.0f, L"Mode", driver ? L"Kernel" : L"User");
    factRow(223.0f, L"Device", g_hwid);
    factRow(256.0f, L"Process", pid ? (L"PID " + std::to_wstring(pid)) : L"Not found");
    ui.DrawLine({leftX, 289.0f}, {leftX + leftW, 289.0f}, colors.BorderSubtle, 1.0f);

    // Mode switch (pill)
    const Math::Vector2 modeBtnSize{(leftW - 10.0f) * 0.5f, 32.0f};
    const float modeY = 304.0f;
    if (!busy) {
        bool prevDriver = driver;
        if (ui.RenderButton({leftX, modeY}, modeBtnSize, L"User", !driver)) g_driver_mode.store(false);
        if (ui.RenderButton({leftX + modeBtnSize.x + 10.0f, modeY}, modeBtnSize, L"Kernel", driver)) g_driver_mode.store(true);
        if (g_driver_mode.load() != prevDriver) BuildSteps(g_driver_mode.load());
    } else {
        ui.FillRoundedRect({leftX, modeY}, modeBtnSize, 6.0f, colors.BgElevated);
        ui.DrawText(L"User", {leftX, modeY}, modeBtnSize, driver ? colors.TextTertiary : colors.TextPrimary, UI::FontBold, DWRITE_TEXT_ALIGNMENT_CENTER);
        ui.FillRoundedRect({leftX + modeBtnSize.x + 10.0f, modeY}, modeBtnSize, 6.0f, colors.BgElevated);
        ui.DrawText(L"Kernel", {leftX + modeBtnSize.x + 10.0f, modeY}, modeBtnSize, driver ? colors.TextPrimary : colors.TextTertiary, UI::FontBold, DWRITE_TEXT_ALIGNMENT_CENTER);
    }

    // Progress block (anchored just above the start button)
    const float btnH = 42.0f;
    const float btnY = H - btnH - 20.0f;
    const float barY = btnY - 22.0f;
    const float pctY = barY - 22.0f;

    std::wstringstream pct;
    pct << static_cast<int>(std::round(g_shown_progress * 100.0f)) << L"%";
    ui.DrawText(L"Progress", {leftX, pctY}, {leftW - 70.0f, 16.0f}, colors.TextTertiary, UI::FontSmall);
    ui.DrawText(pct.str(), {leftX + leftW - 70.0f, pctY}, {70.0f, 16.0f},
        failed ? colors.Danger : (ready ? colors.Success : colors.TextSecondary), UI::FontMono, DWRITE_TEXT_ALIGNMENT_TRAILING);
    ui.RenderProgressBar({leftX, barY}, {leftW, 4.0f}, g_shown_progress, ready ? colors.Success : colors.Accent);

    std::wstring buttonLabel = failed ? L"Close" : (ready ? L"Close loader" : (busy ? L"Working..." : L"Start session"));
    bool canPress = !busy || ready || failed;
    if (ui.RenderButton({leftX, btnY}, {leftW, btnH}, buttonLabel, true, canPress)) {
        if (failed || ready) {
            g_running = false;
        } else if (!busy) {
            bool dm = g_driver_mode.load();
            g_used_driver.store(dm);
            std::thread(InjectWorker, dm).detach();
        }
    }

    // Right panel: pipeline
    const float panelX = leftX + leftW + 32.0f;
    const float panelY = 58.0f;
    const float panelW = W - panelX - 16.0f;
    const float panelH = H - panelY - 16.0f;
    ui.FillRoundedRect({panelX, panelY}, {panelW, panelH}, 10.0f, colors.BgSurface);
    ui.DrawRoundedRect({panelX, panelY}, {panelW, panelH}, 10.0f, colors.BorderSubtle, 1.0f);

    ui.DrawText(L"Startup", {panelX + 20.0f, panelY + 16.0f}, {160.0f, 20.0f}, colors.TextPrimary, UI::FontHeader);
    const int total = (int)g_steps.size();
    const std::wstring counter = ready ? L"Done"
        : std::to_wstring((std::min)(g_current_step + 1, total)) + L" of " + std::to_wstring(total);
    ui.DrawText(counter, {panelX + panelW - 120.0f, panelY + 18.0f}, {100.0f, 18.0f},
        ready ? colors.Success : colors.TextTertiary, UI::FontMono, DWRITE_TEXT_ALIGNMENT_TRAILING);
    ui.DrawLine({panelX + 20.0f, panelY + 46.0f}, {panelX + panelW - 20.0f, panelY + 46.0f}, colors.BorderSubtle, 1.0f);

    float stepY = panelY + 62.0f;
    for (size_t i = 0; i < g_steps.size(); ++i) {
        RenderStep34(g_steps[i], {panelX + 20.0f, stepY}, panelW - 40.0f, i + 1 == g_steps.size());
        stepY += 58.0f;
    }

    // Activity log (last 3 lines)
    std::vector<std::string> lines;
    { std::lock_guard<std::mutex> lk(g_log_mutex);
      size_t n = (std::min)(g_log_lines.size(), (size_t)3);
      lines.assign(g_log_lines.end() - (ptrdiff_t)n, g_log_lines.end());
    }
    float logY = panelY + panelH - 68.0f;
    ui.DrawLine({panelX + 20.0f, logY - 8.0f}, {panelX + panelW - 20.0f, logY - 8.0f}, colors.BorderSubtle, 1.0f);
    for (const auto& ln : lines) {
        ui.DrawText(Utf8ToWideL(ln), {panelX + 20.0f, logY}, {panelW - 40.0f, 16.0f}, colors.TextTertiary, UI::FontSmall);
        logY += 16.0f;
    }
}

LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam) {
    switch (msg) {
        case WM_NCHITTEST: {
            POINT pt{GET_X_LPARAM(lparam), GET_Y_LPARAM(lparam)};
            ScreenToClient(hwnd, &pt);
            if (pt.y >= 0 && pt.y < (int)kTitlebarH && pt.x < (int)(kWindowW - kTitlebarButtonsW)) {
                return HTCAPTION;
            }
            return HTCLIENT;
        }
        case WM_MOUSEWHEEL:
            UI::g_UI.AddWheel((float)GET_WHEEL_DELTA_WPARAM(wparam) / WHEEL_DELTA);
            return 0;
        case WM_CHAR:
            UI::g_UI.AddCharacter((wchar_t)wparam);
            return 0;
        case WM_KEYDOWN:
            if (wparam == VK_ESCAPE) g_running = false;
            return 0;
        case WM_SIZE:
            if (wparam != SIZE_MINIMIZED && g_device && g_swap) {
                CleanupRenderTarget();
                g_swap->ResizeBuffers(0, (UINT)LOWORD(lparam), (UINT)HIWORD(lparam), DXGI_FORMAT_UNKNOWN, 0);
                CreateRenderTarget();
            }
            return 0;
        case WM_SYSCOMMAND:
            if ((wparam & 0xfff0) == SC_KEYMENU) return 0;
            break;
        case WM_CLOSE:
            g_running = false;
            DestroyWindow(hwnd);
            return 0;
        case WM_DESTROY:
            PostQuitMessage(0);
            return 0;
        default:
            break;
    }
    return DefWindowProcW(hwnd, msg, wparam, lparam);
}

}  // namespace

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE, PWSTR, int) {
    WNDCLASSEXW wc{};
    wc.cbSize = sizeof(wc);
    wc.style = CS_HREDRAW | CS_VREDRAW;
    wc.lpfnWndProc = WndProc;
    wc.hInstance = instance;
    wc.hCursor = LoadCursorW(nullptr, (LPCWSTR)IDC_ARROW);
    wc.hIcon = (HICON)LoadImageW(instance, MAKEINTRESOURCEW(101), IMAGE_ICON,
        GetSystemMetrics(SM_CXICON), GetSystemMetrics(SM_CYICON), LR_DEFAULTCOLOR);
    wc.hIconSm = (HICON)LoadImageW(instance, MAKEINTRESOURCEW(101), IMAGE_ICON,
        GetSystemMetrics(SM_CXSMICON), GetSystemMetrics(SM_CYSMICON), LR_DEFAULTCOLOR);
    wc.lpszClassName = L"CiyELoaderWindow34";
    RegisterClassExW(&wc);

    int screen_w = GetSystemMetrics(SM_CXSCREEN);
    int screen_h = GetSystemMetrics(SM_CYSCREEN);
    int pos_x = (screen_w - (int)kWindowW) / 2;
    int pos_y = (screen_h - (int)kWindowH) / 2;

    g_hwnd = CreateWindowExW(WS_EX_APPWINDOW, wc.lpszClassName, L"CiyE",
                             WS_POPUP | WS_MINIMIZEBOX,
                             pos_x, pos_y, (int)kWindowW, (int)kWindowH,
                             nullptr, nullptr, instance, nullptr);
    if (!g_hwnd) return 1;

    MARGINS margins = {1, 1, 1, 1};
    DwmExtendFrameIntoClientArea(g_hwnd, &margins);
    const DWORD cornerPref = 33;
    int round = 2;
    DwmSetWindowAttribute(g_hwnd, cornerPref, &round, sizeof(round));
    BOOL dark = TRUE;
    DwmSetWindowAttribute(g_hwnd, 20, &dark, sizeof(dark));

    ShowWindow(g_hwnd, SW_SHOWDEFAULT);
    UpdateWindow(g_hwnd);

    if (!CreateDeviceD3D(g_hwnd)) {
        CleanupDeviceD3D();
        DestroyWindow(g_hwnd);
        return 1;
    }
    if (!UI::g_UI.Initialize(g_swap)) {
        CleanupDeviceD3D();
        DestroyWindow(g_hwnd);
        return 1;
    }

    InitSteps();
    Log("CiyE loader ready.");

    while (g_running) {
        MSG msg;
        while (PeekMessageW(&msg, nullptr, 0, 0, PM_REMOVE)) {
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
            if (msg.message == WM_QUIT) g_running = false;
        }
        if (!g_running) break;
        if (IsIconic(g_hwnd)) {
            Sleep(10);
            continue;
        }

        // Auto-scan for the game while idle.
        static DWORD last_scan = 0;
        DWORD now_tick = GetTickCount();
        if (!g_busy.load() && now_tick - last_scan > 800) {
            last_scan = now_tick;
            DWORD found = FindProcess(kGame);
            g_live_pid.store(found);
            if (!found) g_pid.store(0);
        }
        if (g_auto_inject.load() && !g_busy.load() && g_phase.load() == kIdle && g_live_pid.load()) {
            bool dm = g_driver_mode.load();
            g_used_driver.store(dm);
            g_busy.store(true);
            std::thread(InjectWorker, dm).detach();
        }

        SyncStepsFromPhase();

        POINT mp{};
        GetCursorPos(&mp);
        ScreenToClient(g_hwnd, &mp);
        bool mdown = (GetForegroundWindow() == g_hwnd) && (GetAsyncKeyState(VK_LBUTTON) & 0x8000) != 0;
        Math::Vector2 mouse{(float)mp.x, (float)mp.y};

        if (!g_intro_done) {
            g_intro_time += UI::g_UI.DeltaTime();
            if (g_intro_time >= kIntroEnd34) g_intro_done = true;
        }
        const bool inIntro = !g_intro_done;
        const float exitP = inIntro ? Phase34(g_intro_time, kIntroExit34, kIntroEnd34) : 0.0f;
        const bool pointerLive = !inIntro ||
            (mouse.y < kTitlebarH && mouse.x >= kWindowW - kTitlebarButtonsW);
        UI::g_UI.UpdateInput(pointerLive ? mouse : Math::Vector2{-1000.0f, -1000.0f}, pointerLive && mdown);

        const auto& bg = UI::g_UI.GetColors().BgBase;
        const float clearColor[4] = {bg.r, bg.g, bg.b, 1.0f};
        g_context->OMSetRenderTargets(1, &g_rtv, nullptr);
        g_context->ClearRenderTargetView(g_rtv, clearColor);

        UI::g_UI.BeginDraw();
        if (!inIntro || exitP > 0.0f) RenderFrame34();
        if (inIntro) {
            RenderIntro34(exitP);
            RenderTitleButtons34();
        }
        UI::g_UI.RenderPopups();
        UI::g_UI.EndDraw();
        g_swap->Present(1, 0);

        if (g_close_on_done.load() && g_phase.load() == kReady) {
            static bool posted = false;
            if (!posted) { posted = true; PostMessageW(g_hwnd, WM_CLOSE, 0, 0); }
        }
    }

    UI::g_UI.Shutdown();
    CleanupDeviceD3D();
    DestroyWindow(g_hwnd);
    UnregisterClassW(wc.lpszClassName, instance);
    return 0;
}

// --- dead code below (kept to preserve old helpers if ever referenced) ---
#if 0
void DrawCard(ImDrawList* dl, ImVec2 p, ImVec2 size, const char* label, const char* value,
              ImU32 color, ImFont* font, float font_size) {
    dl->AddRectFilled(p, ImVec2(p.x + size.x, p.y + size.y), IM_COL32(17, 21, 31, 255), S(12));
    dl->AddRect(p, ImVec2(p.x + size.x, p.y + size.y), IM_COL32(34, 42, 58, 255), S(12));
    dl->AddRectFilled(ImVec2(p.x + S(14), p.y + S(15)), ImVec2(p.x + S(17), p.y + size.y - S(15)),
                      color, S(2));
    dl->AddText(g_font_small, S(11), ImVec2(p.x + S(27), p.y + S(12)), kMuted, label);
    dl->AddText(font, font_size, ImVec2(p.x + S(27), p.y + S(31)), color, value);
}

bool ToggleButton(const char* label, bool active, ImVec2 size) {
    if (active) ImGui::PushStyleColor(ImGuiCol_Button, ImVec4(.22f, .19f, .31f, 1));
    bool clicked = ImGui::Button(label, size);
    if (active) ImGui::PopStyleColor();
    return clicked;
}

const char* PhaseText(int phase) {
    switch (phase) {
        case kWaiting: return "WAITING";
        case kInjecting: return "INJECTING";
        case kReady: return "READY";
        case kFailed: return "FAILED";
        default: return "IDLE";
    }
}

ImU32 PhaseColor(int phase) {
    switch (phase) {
        case kWaiting: return kWarn;
        case kInjecting: return kAccent;
        case kReady: return kSuccess;
        case kFailed: return kError;
        default: return kMuted;
    }
}

void RenderUI() {
    auto& io = ImGui::GetIO();
    ImGui::SetNextWindowPos(ImVec2(0, 0)); ImGui::SetNextWindowSize(io.DisplaySize);
    ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding, ImVec2(0, 0));
    ImGui::Begin("##root", nullptr, ImGuiWindowFlags_NoDecoration | ImGuiWindowFlags_NoMove |
                 ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoSavedSettings);
    auto* dl = ImGui::GetWindowDrawList(); const ImVec2 wp = ImGui::GetWindowPos(), ws = io.DisplaySize;
    dl->AddRectFilled(wp, ImVec2(wp.x + ws.x, wp.y + ws.y), CiyEUi::Ground);
    const float margin = S(28), left = S(264), gap = S(32), right_x = margin + left + gap;
    CiyEUi::Logo(dl, ImVec2(wp.x + S(20), wp.y + S(12)), S(22));
    dl->AddText(g_font_med, S(13), ImVec2(wp.x + S(54), wp.y + S(15)), kText, kBrand);
    const float badge_x = S(54) + g_font_med->CalcTextSizeA(S(13), FLT_MAX, 0, kBrand).x + S(10);
    const float badge_w = g_font_small->CalcTextSizeA(S(11.5f), FLT_MAX, 0, kVersion).x + S(14);
    dl->AddRectFilled(ImVec2(wp.x+badge_x,wp.y+S(13)),ImVec2(wp.x+badge_x+badge_w,wp.y+S(31)),CiyEUi::Elevated,S(9));
    dl->AddText(g_font_small,S(11.5f),ImVec2(wp.x+badge_x+S(7),wp.y+S(16)),kMuted,kVersion);
    dl->AddLine(ImVec2(wp.x,wp.y+S(44)),ImVec2(wp.x+ws.x,wp.y+S(44)),CiyEUi::Border);
    static DWORD last_scan = 0;
    DWORD now_tick = GetTickCount();
    if (!g_busy.load() && now_tick - last_scan > 800) {
        last_scan = now_tick; DWORD found = FindProcess(kGame);
        g_live_pid.store(found); if (!found) g_pid.store(0);
    }
    bool busy = g_busy.load();
    if (g_auto_inject.load() && !busy && g_phase.load() == kIdle && g_live_pid.load()) {
        bool dm_auto = g_driver_mode.load(); g_used_driver.store(dm_auto); g_busy.store(true);
        std::thread(InjectWorker, dm_auto).detach(); busy = true;
    }
    const int phase = g_phase.load();
    unsigned long pid = g_pid.load(); if (!pid) pid = g_live_pid.load();
    const char* title = phase == kReady ? "Session ready" : phase == kFailed ? "Session needs attention" : busy ? "Starting session" : "Ready when you are";
    CiyEUi::Logo(dl, ImVec2(wp.x + margin, wp.y + S(66)), S(40));
    dl->AddCircle(ImVec2(wp.x + margin + S(20), wp.y + S(86)), S(25), PhaseColor(phase), 48, S(1.25f));
    dl->AddText(g_font_bold, S(20), ImVec2(wp.x + margin, wp.y + S(120)), kText, title);
    dl->AddText(g_font, S(13), ImVec2(wp.x + margin, wp.y + S(152)), kMuted, "Blood Strike");
    dl->AddLine(ImVec2(wp.x + margin, wp.y + S(190)), ImVec2(wp.x + margin + left, wp.y + S(190)), CiyEUi::Border);
    ImGui::SetCursorPos(ImVec2(margin, S(203)));
    ImGui::TextDisabled("Launch mode"); ImGui::SameLine(S(170));
    ImGui::TextUnformatted(g_driver_mode.load() ? "Kernel mode" : "User mode");
    ImGui::SetCursorPos(ImVec2(margin, S(234)));
    ImGui::BeginDisabled(busy);
    if (ToggleButton("User mode", !g_driver_mode.load(), ImVec2(S(127), S(32)))) g_driver_mode.store(false);
    ImGui::SameLine(0, S(10));
    if (ToggleButton("Kernel mode", g_driver_mode.load(), ImVec2(S(127), S(32)))) g_driver_mode.store(true);
    ImGui::EndDisabled();
    ImGui::SetCursorPos(ImVec2(margin, ws.y - S(86)));
    ImGui::PushStyleColor(ImGuiCol_Button, ImGui::ColorConvertU32ToFloat4(CiyEUi::Accent));
    ImGui::PushStyleColor(ImGuiCol_ButtonHovered, ImVec4(.73f, .65f, 1, 1));
    ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(.07f, .055f, .11f, 1));
    ImGui::BeginDisabled(busy);
    if (ImGui::Button(busy ? "Starting..." : "Start session", ImVec2(left, S(40)))) {
        if (!busy) { bool dm = g_driver_mode.load(); g_used_driver.store(dm); std::thread(InjectWorker, dm).detach(); }
    }
    ImGui::EndDisabled(); ImGui::PopStyleColor(3);
    ImGui::SetCursorPos(ImVec2(margin, S(284)));
    bool auto_start = g_auto_inject.load(), close_done = g_close_on_done.load();
    if (CiyEUi::Toggle("Start automatically", &auto_start, left, g_scale)) g_auto_inject.store(auto_start);
    ImGui::SetCursorPos(ImVec2(margin, S(318)));
    if (CiyEUi::Toggle("Close when ready", &close_done, left, g_scale)) g_close_on_done.store(close_done);
    ImGui::SetCursorPos(ImVec2(margin, ws.y - S(42)));
    if (ImGui::Button("Open folder", ImVec2(S(122), S(28)))) { std::wstring dir = SelfDir(); ShellExecuteW(nullptr, L"open", dir.c_str(), nullptr, nullptr, SW_SHOWNORMAL); }
    ImGui::SetCursorPos(ImVec2(right_x, S(58)));
    ImGui::PushStyleColor(ImGuiCol_ChildBg, ImGui::ColorConvertU32ToFloat4(CiyEUi::Surface));
    ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding, ImVec2(S(20), S(18)));
    ImGui::BeginChild("startup", ImVec2(ws.x - right_x - S(16), ws.y - S(74)), ImGuiChildFlags_Borders);
    ImGui::PushFont(g_font_med, S(14));
    ImGui::TextUnformatted("Startup");
    ImGui::PopFont();
    ImGui::Dummy(ImVec2(0, S(14)));
    ImGui::Separator();
    ImGui::Dummy(ImVec2(0, S(16)));
    auto status_row = [&](const char* label, const char* detail, ImU32 color, bool last = false) {
        const float row_y = ImGui::GetCursorPosY();
        ImVec2 pos = ImGui::GetCursorScreenPos();
        dl = ImGui::GetWindowDrawList();
        const ImVec2 center(pos.x + S(9), pos.y + S(9));
        if (!last) dl->AddLine(ImVec2(center.x, center.y + S(13)), ImVec2(center.x, center.y + S(59)), CiyEUi::Border, S(1));
        if (color == kSuccess) {
            dl->AddCircleFilled(center, S(9), color);
            dl->AddLine(ImVec2(center.x-S(3),center.y),ImVec2(center.x-S(1),center.y+S(2)),CiyEUi::Ground,S(1.5f));
            dl->AddLine(ImVec2(center.x-S(1),center.y+S(2)),ImVec2(center.x+S(4),center.y-S(3)),CiyEUi::Ground,S(1.5f));
        } else dl->AddCircle(center, S(8), color, 24, S(1.5f));
        ImGui::SetCursorPosX(ImGui::GetCursorPosX() + S(34)); ImGui::BeginGroup();
        ImGui::PushFont(g_font_med, S(13)); ImGui::TextUnformatted(label); ImGui::PopFont();
        ImGui::PushFont(g_font_small, S(11.5f));
        ImGui::PushStyleColor(ImGuiCol_Text, ImGui::ColorConvertU32ToFloat4(color == kError ? kError : kMuted));
        ImGui::TextWrapped("%s", detail); ImGui::PopStyleColor(); ImGui::PopFont(); ImGui::EndGroup();
        ImGui::SetCursorPosY(row_y + S(72));
    };
    char pid_text[80]; if (pid) sprintf_s(pid_text, "BloodStrike.exe - PID %lu", pid); else strcpy_s(pid_text, "Open Blood Strike to continue.");
    status_row("Game process", pid_text, pid ? kSuccess : kWarn);
    status_row("Launch mode", g_driver_mode.load() ? "Kernel mode selected" : "User mode selected", kAccent);
    status_row("Current state", PhaseText(phase), PhaseColor(phase), true);
    ImGui::Separator();
    if (ImGui::CollapsingHeader("Activity log")) {
        std::vector<std::string> lines;
        { std::lock_guard<std::mutex> lock(g_log_mutex); lines.assign(g_log_lines.begin(), g_log_lines.end()); }
        if (lines.empty()) ImGui::TextDisabled("No activity yet.");
        for (const auto& line : lines) ImGui::TextWrapped("%s", line.c_str());
    }
    ImGui::EndChild(); ImGui::PopStyleVar(); ImGui::PopStyleColor();
    if (g_close_on_done.load() && g_phase.load() == kReady) {
        static bool close_posted = false; if (!close_posted) { close_posted = true; PostMessageW(g_hwnd, WM_CLOSE, 0, 0); }
    }
    ImGui::End(); ImGui::PopStyleVar();
}

// ---------------------------------------------------------------------------
// Fonts / style / window
// ---------------------------------------------------------------------------

ImFont* LoadFont(const char* path, float size) {
    if (GetFileAttributesA(path) == INVALID_FILE_ATTRIBUTES) return nullptr;
    ImFontConfig cfg;
    cfg.OversampleH = 2;
    cfg.OversampleV = 1;
    cfg.PixelSnapH = true;
    return ImGui::GetIO().Fonts->AddFontFromFileTTF(path, size, &cfg);
}

void LoadFonts() {
    g_font = LoadFont("C:\\Windows\\Fonts\\segoeui.ttf", S(13));
    g_font_med = LoadFont("C:\\Windows\\Fonts\\seguisb.ttf", S(14));
    g_font_bold = LoadFont("C:\\Windows\\Fonts\\seguisb.ttf", S(20));
    g_font_small = LoadFont("C:\\Windows\\Fonts\\segoeui.ttf", S(11.5f));
    g_font_mono = LoadFont("C:\\Windows\\Fonts\\consola.ttf", S(13));
    if (!g_font) g_font = ImGui::GetIO().Fonts->AddFontDefault();
    if (!g_font_med) g_font_med = g_font;
    if (!g_font_bold) g_font_bold = g_font;
    if (!g_font_small) g_font_small = g_font;
    if (!g_font_mono) g_font_mono = g_font;
}

void ApplyStyle() { CiyEUi::ApplyStyle(g_scale); ImGui::GetStyle().WindowRounding = 0; ImGui::GetStyle().WindowBorderSize = 0; }

void ApplyDarkTitleBar(HWND hwnd) {
    BOOL dark = TRUE;
    DwmSetWindowAttribute(hwnd, 20, &dark, sizeof(dark));
    COLORREF caption = RGB(16, 16, 18);
    DwmSetWindowAttribute(hwnd, 35, &caption, sizeof(caption));
    COLORREF text = RGB(230, 236, 248);
    DwmSetWindowAttribute(hwnd, 36, &text, sizeof(text));
}

LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam) {
    if (ImGui_ImplWin32_WndProcHandler(hwnd, msg, wparam, lparam)) return true;

    switch (msg) {
        case WM_SIZE:
            if (wparam != SIZE_MINIMIZED && g_device && g_swap) {
                CleanupRenderTarget();
                g_swap->ResizeBuffers(0, (UINT)LOWORD(lparam), (UINT)HIWORD(lparam),
                                      DXGI_FORMAT_UNKNOWN, 0);
                CreateRenderTarget();
            }
            return 0;
        case WM_SYSCOMMAND:
            if ((wparam & 0xfff0) == SC_KEYMENU) return 0;
            break;
        case WM_CLOSE:
            g_running = false;
            DestroyWindow(hwnd);
            return 0;
        case WM_DESTROY:
            PostQuitMessage(0);
            return 0;
        default:
            break;
    }
    return DefWindowProcW(hwnd, msg, wparam, lparam);
}

}  // namespace

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE, PWSTR, int) {
    ImGui_ImplWin32_EnableDpiAwareness();

    UINT dpi = 96;
    if (HMODULE user32 = GetModuleHandleW(L"user32.dll")) {
        typedef UINT(WINAPI * GetDpiForSystemFn)();
        auto get_dpi = reinterpret_cast<GetDpiForSystemFn>(GetProcAddress(user32, "GetDpiForSystem"));
        if (get_dpi) dpi = get_dpi();
    }
    g_scale = dpi / 96.0f;
    if (g_scale < 0.75f) g_scale = 0.75f;
    if (g_scale > 2.5f) g_scale = 2.5f;

    WNDCLASSEXW wc{};
    wc.cbSize = sizeof(wc);
    wc.style = CS_CLASSDC;
    wc.lpfnWndProc = WndProc;
    wc.hInstance = instance;
    wc.hCursor = LoadCursor(nullptr, IDC_ARROW);
    wc.lpszClassName = L"CiyELoaderWindow";
    RegisterClassExW(&wc);

    int win_w = (int)S(680);
    int win_h = (int)S(520);
    int screen_w = GetSystemMetrics(SM_CXSCREEN);
    int screen_h = GetSystemMetrics(SM_CYSCREEN);
    int pos_x = (screen_w - win_w) / 2;
    int pos_y = (screen_h - win_h) / 2;

    g_hwnd = CreateWindowExW(0, wc.lpszClassName, L"CiyE Loader", WS_OVERLAPPED | WS_CAPTION |
                                 WS_SYSMENU | WS_MINIMIZEBOX,
                             pos_x, pos_y, win_w, win_h, nullptr, nullptr, instance, nullptr);
    if (!g_hwnd) return 1;

    ApplyDarkTitleBar(g_hwnd);
    ShowWindow(g_hwnd, SW_SHOWDEFAULT);
    UpdateWindow(g_hwnd);

    if (!CreateDeviceD3D(g_hwnd)) {
        CleanupDeviceD3D();
        DestroyWindow(g_hwnd);
        return 1;
    }

    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGuiIO& io = ImGui::GetIO();
    io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;
    io.IniFilename = nullptr;

    LoadFonts();
    ApplyStyle();

    ImGui_ImplWin32_Init(g_hwnd);
    ImGui_ImplDX11_Init(g_device, g_context);

    Log("CiyE loader ready.");
    Log("select mode and press INJECT.");

    while (g_running) {
        MSG msg;
        while (PeekMessageW(&msg, nullptr, 0, 0, PM_REMOVE)) {
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
            if (msg.message == WM_QUIT) g_running = false;
        }
        if (!g_running) break;
        if (IsIconic(g_hwnd)) {
            Sleep(10);
            continue;
        }

        ImGui_ImplDX11_NewFrame();
        ImGui_ImplWin32_NewFrame();
        ImGui::NewFrame();

        RenderUI();

        ImGui::Render();
        const float clear[4] = {0.03f, 0.04f, 0.06f, 1.0f};
        g_context->OMSetRenderTargets(1, &g_rtv, nullptr);
        g_context->ClearRenderTargetView(g_rtv, clear);
        ImGui_ImplDX11_RenderDrawData(ImGui::GetDrawData());
        g_swap->Present(1, 0);
    }

    return 0;
}
#endif
