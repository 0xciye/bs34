import builtins
import os
import sys
import struct
import time
import math
import random
import traceback

try:
    import MUI
except Exception:
    MUI = None

def _root_dir():
    for key in ('BS_ROOT', 'BS_CHEAT_ROOT'):
        v = os.environ.get(key)
        if v and os.path.isdir(v):
            return os.path.abspath(v)
    here = os.path.dirname(os.path.abspath(globals().get('__file__') or '.'))
    cand = os.path.abspath(os.path.join(here, '..'))
    if os.path.isdir(os.path.join(cand, 'ipc')) or os.path.basename(here).lower() == 'pyexec':
        return cand
    return here


BS_ROOT = _root_dir()
IPC_DIR = os.path.join(BS_ROOT, 'ipc')
try:
    os.makedirs(IPC_DIR, exist_ok=True)
except Exception:
    pass
STATE_PATH = os.path.join(IPC_DIR, 'state.bin')
CFG_PATH = os.path.join(IPC_DIR, 'cfg.bin')
CATALOG_PATH = os.path.join(IPC_DIR, 'catalog.bin')
ERR_PATH = os.path.join(IPC_DIR, 'runtime_err.txt')

CFG_MAGIC = 0x42534346
STATE_MAGIC = 0x42535331
CATALOG_MAGIC = 0x42534354
VERSION = 6
MAX_ENTITIES = 128

CFG_FMT = '<IIIIIiIiiifffffiiI' + 'I' * 13 + 'f' + 'I' * 8
STATE_FMT = '<IIIIQ14fBBH'
ENT_FMT = '<Q40s32s3f3f2f2f3fi4BI32f'
CAT_HEAD_FMT = '<IIII'
CAT_ENTRY_FMT = '<IIII48s'

CFG_SIZE = struct.calcsize(CFG_FMT)
STATE_HEAD_SIZE = struct.calcsize(STATE_FMT)
ENT_SIZE = struct.calcsize(ENT_FMT)
CAT_HEAD_SIZE = struct.calcsize(CAT_HEAD_FMT)
CAT_ENTRY_SIZE = struct.calcsize(CAT_ENTRY_FMT)
STATE_SIZE = STATE_HEAD_SIZE + ENT_SIZE * MAX_ENTITIES
MAX_HERO = 4096
MAX_GUN = 65536

assert CFG_SIZE == 160
assert STATE_HEAD_SIZE == 84
assert ENT_SIZE == 272
assert CAT_ENTRY_SIZE == 64

IDX_MAGIC = 0
IDX_VERSION = 1
IDX_SEQ = 2
IDX_FLAGS = 3
IDX_APPLY_SEQ = 4
IDX_APPLY_TYPE = 5
IDX_APPLY_ITEM = 6
IDX_AIM_KEY = 7
IDX_FLICK_KEY = 8
IDX_MENU_KEY = 9
IDX_AIM_FOV = 10
IDX_AIM_SMOOTH = 11
IDX_AIM_MAX_DIST = 12
IDX_FLICK_FOV = 13
IDX_HUMANIZE = 14
IDX_AIM_BONE = 15
IDX_ESP_MAX_DIST = 16
IDX_OPTIONS = 17
IDX_COL_BOX = 18
IDX_COL_BOX_HIDDEN = 19
IDX_COL_TEAM = 20
IDX_COL_MONSTER = 21
IDX_COL_SKEL = 22
IDX_COL_LINE = 23
IDX_COL_NAME = 24
IDX_COL_GUN = 25
IDX_COL_DIST = 26
IDX_COL_HEALTH = 27
IDX_COL_HEADDOT = 28
IDX_COL_COUNT = 29
IDX_ESP_STYLE = 30
IDX_BOX_THICK = 31
IDX_SKIN_HERO = 32
IDX_SKIN_GUN = 33
IDX_SKIN_KNIFE = 34
IDX_AUTO_SKIN = 35

OPT_AIM_TOGGLE = 1 << 0

F_MENU_OPEN = 1 << 0
F_ESP = 1 << 1
F_ESP_BOX = 1 << 2
F_ESP_SKELETON = 1 << 3
F_ESP_LINE = 1 << 4
F_ESP_NAME = 1 << 5
F_ESP_GUN = 1 << 6
F_ESP_DISTANCE = 1 << 7
F_ESP_HEALTH = 1 << 8
F_ESP_HEADDOT = 1 << 9
F_ESP_TEAM = 1 << 10
F_ESP_VISIBLE = 1 << 11
F_ESP_COUNT = 1 << 12
F_AIM = 1 << 13
F_AIM_VISIBLE = 1 << 14
F_AIM_TEAM = 1 << 15
F_AIM_FOV_CIRCLE = 1 << 16
F_AIM_HUMANIZE = 1 << 17
F_FLICK = 1 << 18
F_FLICK_FIRE = 1 << 19
F_UNLOCK_EFFECTS = 1 << 20
F_BLOCK_REPORT = 1 << 21
F_SKIN_CURRENT = 1 << 22
F_RECOIL = 1 << 23
F_FLICK_FOV_CIRCLE = 1 << 24

DEFAULT_FLAGS = (F_MENU_OPEN | F_ESP | F_ESP_BOX | F_ESP_NAME | F_ESP_DISTANCE |
                 F_ESP_HEALTH | F_ESP_HEADDOT | F_AIM_FOV_CIRCLE |
                 F_UNLOCK_EFFECTS | F_BLOCK_REPORT | F_SKIN_CURRENT |
                 F_RECOIL | F_ESP_COUNT | (1 << 27) | (1 << 28) | (1 << 29) | (1 << 30))

DEFAULT_CFG = (
    CFG_MAGIC, VERSION, 0, DEFAULT_FLAGS,
    0, 0, 0,
    0x02, 0x05, 0x2D,
    8.0, 0.35, 400.0, 15.0, 0.90,
    0, 400, 0,
    4036750176, 3948567280, 3707742810, 3947940095,
    3952864096, 3198316889, 4294045164, 3957250262,
    4040674760, 4036750176, 3959422975, 4288408416,
    0, 1.5,
    0, 0, 0, 1,
    0, 0, 0, 0,
)

_runtime = None
_state_seq = 0
_last_state = 0.0
_last_apply_seq = -1
_last_apply_try = 0.0
_last_catalog_check = 0.0
_last_err = 0.0
_flick_prev = False
_last_flick = 0.0
_fire_release_at = 0.0
_aim_prev = False
_aim_latched = False
_aim_hold_until = 0.0
_aim_diag_t = 0.0
_aim_fallback_n = 0
_aim_sign_y = -1.0
_aim_sign_p = -1.0
_aim_sign_ready = False
_aim_eid = None
_aim_eid_t = 0.0
_aim_hold_log_t = 0.0
_perf_t = 0.0
_perf_last = 0.0
_state_file_t = 0.0
_g_log_t = 0.0
_g_slow = 0.0
_flick_queue = None
_aim_busy = False
_jit_t = 0.0
_recoil_t = 0.0
_recoil_grace = 0.0
_vis_cache = {}
_melee_cache = {}
_gather_cache = (0.0, None, None, [])
_last_gather = 0.0
_last_hooks = 0.0
_last_scrub = 0.0
_bone_cache = {}
_gun_cache = {}
_diag_t = 0.0
_ent_list_cache = None
_apply_tries = 0
_apply_seq_seen = -1
_skin_diag = set()
_hooks_done = False
_hook_avatar_id = None
_booted = False
_model_to_hero = {}
_unlock_cache = {}
_unlock_done = False
_unlock_iter = None
_unlock_scan_t = 0.0
_unlock_changed = 0
_wrapped_preds = set()
_last_unlock = 0.0
_my_gen = 0
_skin_auto_seen = None
_skin_task = []
_skin_task_t = 0.0
_skin_fail = {}
_skin_last_reapply = 0.0
_skin_respect_current = False

_cfg_cache_vals = DEFAULT_CFG
_cfg_cache_mtime = -1
_cfg_cache_t = 0.0
_local_cache = None
_hero_id_cache = None
_class_hooks_at = 0.0
_log_last_msg = None
_log_last_t = 0.0
_path = None

HERO_NAMES = {
    101: 'Ethan', 102: 'Jet', 103: 'Nova', 104: 'Val', 105: 'Hank',
    106: 'Spike', 107: 'E.M.', 108: 'Krak', 110: 'Ran', 111: 'Nach',
    112: 'Blas', 113: 'Zero', 114: 'Volt', 115: 'Emma', 116: 'Kain',
    117: 'Katy', 119: 'Jack', 122: 'Luci', 124: 'Alon', 125: 'Vox',
}


def _sys_log(msg):
    global _last_err, _log_last_msg, _log_last_t
    now = time.time()
    text = str(msg)[:1200]
    if text == _log_last_msg and now - _log_last_t < 10.0:
        return
    if now - _last_err < 0.5:
        return
    _last_err = now
    _log_last_msg = text
    _log_last_t = now
    try:
        try:
            if os.path.getsize(ERR_PATH) > 2 * 1024 * 1024:
                os.remove(ERR_PATH)
        except Exception:
            pass
        with open(ERR_PATH, 'a', encoding='utf-8', errors='replace') as f:
            f.write(time.strftime('%H:%M:%S ') + text + '\n')
    except Exception:
        pass


BONE_NAMES = [
    ('biped Head', 'Bip001 Head', 'Head'),                                    # 0: Head
    ('biped Neck', 'Bip001 Neck', 'Neck'),                                    # 1: Neck
    ('biped Spine1', 'biped Spine', 'Bip001 Spine2', 'Spine'),                # 2: Spine
    ('biped Pelvis', 'Bip001 Pelvis', 'biped Hip', 'Bip001 Hip', 'Pelvis'),   # 3: Pelvis
    ('biped L UpperArm', 'Bip001 L UpperArm', 'L UpperArm', 'LUpperArm'),    # 4: L Shoulder
    ('biped L Forearm', 'Bip001 L Forearm', 'L Forearm', 'LForeArm'),         # 5: L Elbow
    ('biped L Hand', 'Bip001 L Hand', 'L Hand', 'LHand'),                     # 6: L Hand
    ('biped R UpperArm', 'Bip001 R UpperArm', 'R UpperArm', 'RUpperArm'),    # 7: R Shoulder
    ('biped R Forearm', 'Bip001 R Forearm', 'R Forearm', 'RForeArm'),         # 8: R Elbow
    ('biped R Hand', 'Bip001 R Hand', 'R Hand', 'RHand'),                     # 9: R Hand
    ('biped L Thigh', 'Bip001 L Thigh', 'L Thigh', 'LThigh'),                 # 10: L Hip
    ('biped L Calf', 'Bip001 L Calf', 'L Calf', 'LCalf'),                     # 11: L Knee
    ('biped L Foot', 'Bip001 L Foot', 'L Foot', 'LFoot'),                     # 12: L Foot
    ('biped R Thigh', 'Bip001 R Thigh', 'R Thigh', 'RThigh'),                 # 13: R Hip
    ('biped R Calf', 'Bip001 R Calf', 'R Calf', 'RCalf'),                     # 14: R Knee
    ('biped R Foot', 'Bip001 R Foot', 'R Foot', 'RFoot')                      # 15: R Foot
]

def _close(a, b, tol=1e-9):
    return a is not None and b is not None and abs(a - b) < tol


def _flag(cfg, bit):
    try:
        return bool(int(cfg[IDX_FLAGS]) & bit)
    except Exception:
        return False


def _options(cfg):
    try:
        return int(cfg[IDX_OPTIONS])
    except Exception:
        return 0


def _get_track_mode_toggle(cfg):
    return bool(_options(cfg) & OPT_AIM_TOGGLE)


def _view_snap_smooth(cfg):
    try:
        return ((_options(cfg) >> 8) & 0xFF) / 100.0
    except Exception:
        return 0.0


def _vec(v):
    if v is None:
        return None
    try:
        t = v.tuple()
        return (float(t[0]), float(t[1]), float(t[2]))
    except Exception:
        pass
    try:
        return (float(v.x), float(v.y), float(v.z))
    except Exception:
        pass
    try:
        return (float(v[0]), float(v[1]), float(v[2]))
    except Exception:
        return None


_V3_CLASS = None


def _v3(v):
    t = _vec(v)
    if t is None:
        return None
    global _V3_CLASS
    try:
        if _V3_CLASS is None:
            from MType import Vector3 as _V
            _V3_CLASS = _V
        return _V3_CLASS(t[0], t[1], t[2])
    except Exception:
        return t


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _len(a):
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def _norm(a):
    n = _len(a)
    if n < 1e-9:
        return (0.0, 0.0, 0.0)
    return (a[0] / n, a[1] / n, a[2] / n)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _id_u64(v):
    try:
        return int(v) & 0xFFFFFFFFFFFFFFFF
    except Exception:
        pass
    h = 1469598103934665603
    try:
        data = str(v).encode('utf-8', 'replace')
    except Exception:
        data = b''
    for b in data:
        h = ((h ^ b) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return h


def _finite(*xs):
    for x in xs:
        try:
            if not math.isfinite(float(x)):
                return False
        except Exception:
            return False
    return True


_shm_state_p = None
_shm_cfg_p = None

def _init_ctypes_shm():
    global _shm_state_p, _shm_cfg_p
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.windll.kernel32
        k32.OpenFileMappingA.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCSTR]
        k32.OpenFileMappingA.restype = wintypes.HANDLE
        k32.CreateFileMappingA.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.LPCSTR]
        k32.CreateFileMappingA.restype = wintypes.HANDLE
        k32.MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
        k32.MapViewOfFile.restype = ctypes.c_void_p

        PAGE_READWRITE = 0x04
        FILE_MAP_ALL_ACCESS = 0x000F001F

        if _shm_state_p is None:
            h = k32.OpenFileMappingA(FILE_MAP_ALL_ACCESS, False, b"Local\\BS_IPC_STATE")
            if not h:
                h = k32.CreateFileMappingA(wintypes.HANDLE(-1), None, PAGE_READWRITE, 0, 65536, b"Local\\BS_IPC_STATE")
            if h:
                _shm_state_p = k32.MapViewOfFile(h, FILE_MAP_ALL_ACCESS, 0, 0, 65536)

        if _shm_cfg_p is None:
            h = k32.OpenFileMappingA(FILE_MAP_ALL_ACCESS, False, b"Local\\BS_IPC_CFG")
            if not h:
                h = k32.CreateFileMappingA(wintypes.HANDLE(-1), None, PAGE_READWRITE, 0, CFG_SIZE, b"Local\\BS_IPC_CFG")
            if h:
                _shm_cfg_p = k32.MapViewOfFile(h, FILE_MAP_ALL_ACCESS, 0, 0, CFG_SIZE)
    except Exception:
        pass

def _write(path, data):
    global _state_file_t
    if path == STATE_PATH:
        if _shm_state_p is None:
            _init_ctypes_shm()
        if _shm_state_p:
            try:
                import ctypes
                ctypes.memmove(_shm_state_p, data, len(data))
            except Exception:
                pass
            now = time.time()
            if now - _state_file_t < 0.25:
                return True
            _state_file_t = now
    tmp = path + '.tmp'
    try:
        with open(tmp, 'wb') as f:
            f.write(data)
        for _ in range(4):
            try:
                os.replace(tmp, path)
                return True
            except OSError:
                time.sleep(0.001)
    except Exception:
        pass
    try:
        with open(path, 'wb') as f:
            f.write(data)
        return True
    except Exception:
        return False


def _read(path, size):
    try:
        with open(path, 'rb') as f:
            return f.read(size)
    except Exception:
        return None


def _bytes(x, n):
    if x is None:
        return b''.ljust(n, b'\x00')
    try:
        b = str(x).encode('utf-8', 'replace')[:max(0, n - 1)]
    except Exception:
        b = b''
    while b:
        try:
            b.decode('utf-8')
            break
        except UnicodeDecodeError:
            b = b[:-1]
    return b.ljust(n, b'\x00')


def _read_cfg():
    global _cfg_cache_vals, _cfg_cache_mtime, _cfg_cache_t
    now = time.time()
    if now - _cfg_cache_t < 0.033:
        return _cfg_cache_vals
    _cfg_cache_t = now
    raw = None
    if _shm_cfg_p is None:
        _init_ctypes_shm()
    if _shm_cfg_p:
        try:
            import ctypes
            candidate = ctypes.string_at(_shm_cfg_p, CFG_SIZE)
            if len(candidate) == CFG_SIZE:
                v = struct.unpack(CFG_FMT, candidate)
                if v[0] == CFG_MAGIC and v[1] == VERSION:
                    _cfg_cache_vals = v
                    return v
        except Exception:
            pass
    try:
        mtime = os.stat(CFG_PATH).st_mtime_ns
    except Exception:
        mtime = -1
    if mtime == _cfg_cache_mtime:
        return _cfg_cache_vals
    _cfg_cache_mtime = mtime
    raw = _read(CFG_PATH, CFG_SIZE)
    if raw is None or len(raw) != CFG_SIZE:
        _cfg_cache_vals = DEFAULT_CFG
        return DEFAULT_CFG
    try:
        vals = struct.unpack(CFG_FMT, raw)
        if vals[0] != CFG_MAGIC or vals[1] != VERSION:
            _cfg_cache_vals = DEFAULT_CFG
        else:
            _cfg_cache_vals = vals
    except Exception:
        _cfg_cache_vals = DEFAULT_CFG
    return _cfg_cache_vals


def _make_cfg_default():
    try:
        os.makedirs(IPC_DIR, exist_ok=True)
        raw = _read(CFG_PATH, CFG_SIZE)
        if raw is None or len(raw) != CFG_SIZE:
            _write(CFG_PATH, struct.pack(CFG_FMT, *DEFAULT_CFG))
            return
        vals = struct.unpack(CFG_FMT, raw)
        if vals[0] != CFG_MAGIC or vals[1] != VERSION:
            _write(CFG_PATH, struct.pack(CFG_FMT, *DEFAULT_CFG))
    except Exception:
        _sys_log(traceback.format_exc())


def _weapon_util():
    try:
        from gshare import weapon_util
        return weapon_util
    except Exception:
        return None


def _melee_value(value, space):
    try:
        value = int(value)
    except Exception:
        return False
    if value <= 0:
        return False
    key = (space, value)
    if key in _melee_cache:
        return _melee_cache[key]
    res = False
    wu = _weapon_util()
    if wu is not None:
        for fn_name in ('IsWeaponMelee', 'IsWeaponMeleeSharp'):
            fn = getattr(wu, fn_name, None)
            if callable(fn):
                try:
                    if bool(fn(value)):
                        res = True
                        break
                except Exception:
                    pass
        if not res:
            try:
                from gshare import consts
                gt = None
                gfn = getattr(wu, 'GetWeaponGunType', None)
                if callable(gfn):
                    gt = gfn(value)
                keys = set()
                for base_name in ('GunType', 'EquipmentType', 'WeaponType'):
                    base = getattr(consts, base_name, None)
                    if base is None:
                        continue
                    for k, v in vars(base).items():
                        if not k.isupper():
                            continue
                        if any(x in k for x in ('KNIFE', 'MELEE', 'BLADE', 'SWORD', 'HAMMER', 'AXE')):
                            keys.add(v)
                if gt is not None and keys and gt in keys:
                    res = True
            except Exception:
                pass
    _melee_cache[key] = res
    return res


def _melee_gid(gid, wid=None):
    if wid:
        return _melee_value(wid, 'w')
    return _melee_value(gid, 'g')


def _melee_name(name):
    try:
        s = str(name).lower()
    except Exception:
        return False
    for w in ('knife', 'karambit', 'dagger', 'machete', 'bayonet', 'blade', 'sword', 'axe', 'hammer',
              'kunai', 'tanto', 'cleaver', 'sickle', 'scythe', 'pickaxe', 'shovel', 'crowbar', 'wrench',
              'katana', 'rapier', 'spear', 'halberd', 'trident', 'nunchaku', 'tonfa', 'mace', 'flail',
              'chainsaw', 'bowie', 'stiletto', 'kukri', 'gauntlet', 'claw', 'baseball',
              '\u5200', '\u5251', '\u65a7', '\u9524', '\u5315', '\u68cd', '\u9570',
              '\u77db', '\u621f', '\u722a', '\u9576'):
        if w in s:
            return True
    return False


_CN_WORDS = (
    ('\u8774\u8776\u5200', 'Butterfly Knife'), ('\u519b\u5200', 'Combat Knife'),
    ('\u722a\u5200', 'Karambit'), ('\u6b66\u58eb\u5200', 'Katana'), ('\u592a\u5200', 'Katana'),
    ('\u9570\u5200', 'Scythe'), ('\u780d\u5200', 'Machete'), ('\u5f2f\u5200', 'Kukri'),
    ('\u523a\u5200', 'Bayonet'), ('\u957f\u77db', 'Spear'), ('\u957f\u67aa', 'Spear'),
    ('\u6218\u65a7', 'Tactical Axe'), ('\u5927\u5251', 'Greatsword'),
    ('\u62f3\u5957', 'Boxing Gloves'), ('\u624b\u5957', 'Gloves'),
    ('\u68d2\u7403\u68cd', 'Baseball Bat'), ('\u4e09\u53c9\u621f', 'Trident'),
    ('\u82e6\u65e0', 'Kunai'), ('\u624b\u91cc\u5251', 'Shuriken'), ('\u7535\u952f', 'Chainsaw'),
    ('\u72fc\u7259\u68cd', 'Mace'), ('\u5315\u9996', 'Knife'), ('\u9ed8\u8ba4', 'Default'),
    ('\u9650\u5b9a', 'Limited'), ('\u4f20\u8bf4', 'Legend'), ('\u673a\u68b0', 'Mech'),
    ('\u8d5b\u535a', 'Cyber'), ('\u84b8\u6c7d', 'Steam'), ('\u5723\u8bde', 'Christmas'),
    ('\u4e07\u5723', 'Halloween'), ('\u65b0\u5e74', 'New Year'), ('\u51a0\u519b', 'Champion'),
    ('\u7cbe\u82f1', 'Elite'), ('\u5929\u4f7f', 'Angel'), ('\u6076\u9b54', 'Devil'),
    ('\u9ab7\u9ac5', 'Skull'), ('\u8d64', 'Red'), ('\u7ea2', 'Red'), ('\u84dd', 'Blue'),
    ('\u7eff', 'Green'), ('\u91d1', 'Gold'), ('\u94f6', 'Silver'), ('\u9ed1', 'Black'),
    ('\u767d', 'White'), ('\u7d2b', 'Purple'), ('\u9ec4', 'Yellow'), ('\u6a59', 'Orange'),
    ('\u7c89', 'Pink'), ('\u9752', 'Cyan'), ('\u7070', 'Gray'), ('\u6697', 'Dark'),
    ('\u706b', 'Fire'), ('\u51b0', 'Ice'), ('\u96f7', 'Thunder'), ('\u6bd2', 'Poison'),
    ('\u8840', 'Blood'), ('\u9f99', 'Dragon'), ('\u864e', 'Tiger'), ('\u72fc', 'Wolf'),
    ('\u51e4', 'Phoenix'), ('\u795e', 'Divine'), ('\u9b54', 'Demon'), ('\u5929', 'Sky'),
    ('\u6d77', 'Sea'), ('\u661f', 'Star'), ('\u6708', 'Moon'), ('\u65e5', 'Sun'),
    ('\u591c', 'Night'), ('\u5f71', 'Shadow'), ('\u77db', 'Spear'), ('\u621f', 'Halberd'),
    ('\u9570', 'Sickle'), ('\u65a7', 'Axe'), ('\u9524', 'Hammer'), ('\u5251', 'Sword'),
    ('\u5200', 'Knife'), ('\u68cd', 'Staff'), ('\u67aa', 'Gun'), ('\u722a', 'Claw'),
)

_MELEE_LABEL = {2: 'Knife', 3: 'Karambit', 4: 'Scythe', 5: 'Spear',
                6: 'Axe', 7: 'Sword', 8: 'Kunai'}

_NAME_MODULES = ('gclient.data.lobby_item_data', 'gclient.data.equip_data',
                 'gclient.data.gun_data', 'gclient.data.weapon_data',
                 'gclient.data.item_data', 'gclient.data.gun_skin_template_data')


def _cn_swap(text):
    try:
        s = str(text)
    except Exception:
        return ''
    for cn, en in _CN_WORDS:
        if cn in s:
            s = s.replace(cn, ' %s ' % en)
    return s


def _melee_kind(name):
    try:
        s = str(name).lower()
    except Exception:
        return 2
    groups = ((3, ('karambit', 'claw', '\u722a')),
              (4, ('scythe', 'sickle', '\u9570')),
              (5, ('spear', 'halberd', 'trident', '\u77db', '\u621f')),
              (6, ('axe', 'hammer', 'mace', '\u65a7', '\u9524')),
              (7, ('katana', 'sword', 'blade', '\u5251')),
              (8, ('kunai', 'shuriken', 'dart')))
    for kind, words in groups:
        if any(w in s for w in words):
            return kind
    return 2


def _name_tables():
    out = []
    seen = set()
    for n in _NAME_MODULES:
        try:
            m = __import__(n, fromlist=['data'])
        except Exception:
            continue
        d = getattr(m, 'data', None)
        if isinstance(d, dict) and id(d) not in seen:
            seen.add(id(d))
            out.append(d)
    return out


def _ascii_ok(text):
    try:
        return all(32 <= ord(c) < 127 for c in str(text))
    except Exception:
        return False


def _ascii_clean(text):
    try:
        out = []
        last_space = False
        for c in _cn_swap(text):
            if 32 <= ord(c) < 127:
                out.append(c)
                last_space = c == ' '
            elif not last_space:
                out.append(' ')
                last_space = True
        s = ''.join(out).strip(' -_|:')
        s = ' '.join(s.split())
        s = s.replace('- ', ' ').replace(' -', ' ')
        s = ' '.join(s.split())
        return s if any(ch.isalnum() for ch in s) else ''
    except Exception:
        return ''


def _pick_name(v, fallback=''):
    keys = ('name_en', 'skin_name_en', 'en_name', 'english_name', 'display_name_en',
            'name', 'skin_name', 'gun_name', 'weapon_name', 'short_desc', 'item_description')
    for k in keys:
        try:
            s = v.get(k)
        except Exception:
            continue
        if s and _ascii_ok(s):
            return str(s), True
    for k in keys:
        try:
            s = v.get(k)
        except Exception:
            continue
        if not s:
            continue
        t = _ascii_clean(s)
        if t:
            return t, False
    for k in keys:
        try:
            s = v.get(k)
        except Exception:
            continue
        if s and str(s).strip():
            return str(s).strip(), False
    return fallback, False


_melee_set_cache = None


def _melee_gid_set():
    global _melee_set_cache
    if _melee_set_cache is not None:
        return _melee_set_cache
    out = {}
    try:
        import gclient.data.equip_data as eq
        data = getattr(eq, 'data', {})
        for k, v in data.items():
            if not hasattr(v, 'get'):
                continue
            case = str(v.get('equip_case') or '').lower()
            try:
                etype = int(v.get('equip_type') or 0)
            except Exception:
                etype = 0
            if 'melee' not in case and etype not in (2, 3):
                continue
            label = str(v.get('name') or v.get('equip_name') or '')
            for idk in ('mod_id', 'id', 'gun_id'):
                try:
                    iv = int(v.get(idk) or 0)
                except Exception:
                    iv = 0
                if iv > 0:
                    out[iv] = label
            try:
                out[int(k)] = label
            except Exception:
                pass
    except Exception:
        pass
    if not out:
        out = {22: 'Knife', 44: 'Spear'}
    _melee_set_cache = out
    return out


def _index_item_templates():
    import gclient.data.lobby_item_data as lobby
    import gclient.data.gun_skin_template_data as gun
    heroes, guns = {}, {}
    template_items = {}
    levels = {}
    try:
        import gclient.data.lobby_item_upgrade_data as upgrades
        for group in upgrades.data.values():
            for level, entry in group.items():
                if entry.get('item_id'):
                    levels[int(entry['item_id'])] = int(level)
    except ImportError:
        pass
    _model_to_hero.clear()
    for proto in lobby.data.values():
        try:
            if _skin_is_temporary(proto):
                continue
            iid = int(proto['id'])
            subtype = int(proto.get('sub_type') or 0)
            name = str(proto.get('name') or '')
            if not name or any(word in name.lower() for word in ('placeholder', '\u5360\u4f4d', '\u5360\u5751')):
                continue
            if subtype == 300 and 'hero_skin_id' in proto:
                hid, sid = int(proto['hero_id']), int(proto['hero_skin_id'])
                if not (0 < hid <= 0xFFFFFFFF and 0 <= sid <= 0xFFFFFFFF and 0 < iid <= 0xFFFFFFFF):
                    continue
                _model_to_hero[int(proto['model_id'])] = hid
                key = (hid, sid)
                if key not in heroes or iid < heroes[key][2]:
                    heroes[key] = (hid, sid, iid, _pack_tag(HERO_NAMES.get(hid, name)), _bytes(name, 48))
                continue
            if int(proto.get('quality') or 0) < 4:
                continue
            typ = 2 if subtype in (510, 520, 530, 540, 550, 560) else 3 if subtype in (201, 202, 203, 206, 207) else 0
            if not typ:
                continue
            tid = int((proto.get('guise') or {}).get('template_id') or 0)
            template = gun.data.get(tid)
            if template is None:
                continue
            gid = int(template.get('gun_id') or 0) if typ == 2 else subtype * 100 + 2
            if not (0 < gid <= 0xFFFFFFFF and 0 < tid <= 0xFFFFFFFF):
                continue
            key = (typ, tid)
            if key not in template_items or iid < int(template_items[key]['id']):
                template_items[key] = proto
                label = name + (' [Lv %d]' % levels[iid] if iid in levels else '')
                guns[key] = (tid, gid, int(proto['quality']), 1 if typ == 2 else 2, _bytes(label, 48))
        except (KeyError, TypeError, ValueError):
            continue
    _skin_selection.template_items = template_items
    hero_rows = sorted(heroes.values())[:MAX_HERO]
    gun_rows = sorted(guns.values(), key=lambda row: (row[1], -row[2], row[0]))[:MAX_GUN]
    buf = bytearray(CAT_HEAD_SIZE + (len(hero_rows) + len(gun_rows)) * CAT_ENTRY_SIZE)
    struct.pack_into(CAT_HEAD_FMT, buf, 0, CATALOG_MAGIC, VERSION, len(hero_rows), len(gun_rows))
    for index, row in enumerate(hero_rows + gun_rows):
        struct.pack_into(CAT_ENTRY_FMT, buf, CAT_HEAD_SIZE + index * CAT_ENTRY_SIZE, *row)
    return bytes(buf)



def _save_template_cache(force=False):
    # Rebuild once per runtime import: the prior catalog could classify gun 44 as a knife.
    if not force and getattr(_save_template_cache, 'rebuilt', False):
        return
    try:
        _write(CATALOG_PATH, _index_item_templates())
        _save_template_cache.rebuilt = True
    except Exception:
        _sys_log(traceback.format_exc())



def _call_attr(obj, names):
    for n in names:
        try:
            v = getattr(obj, n, None)
        except Exception:
            continue
        if v is None:
            continue
        if callable(v):
            try:
                v = v()
            except Exception:
                continue
        if v is not None:
            return v
    return None


def _pack_tag(text):
    try:
        b = str(text).encode('ascii', 'ignore')[:4]
    except Exception:
        b = b''
    return struct.unpack('<I', b.ljust(4, b'\x00'))[0]


def _hero_of(obj):
    if obj is None:
        return 0
    if isinstance(obj, dict) or hasattr(obj, 'get'):
        for k in ('hero_id', 'hero', 'heroId'):
            try:
                iv = int(obj.get(k) or 0)
                if iv > 0:
                    return iv
            except Exception:
                pass
    for n in ('hero_id', 'GetHeroId', 'heroId'):
        try:
            v = getattr(obj, n, None)
        except Exception:
            continue
        if callable(v):
            try:
                v = v()
            except Exception:
                continue
        try:
            iv = int(v)
            if iv > 0:
                return iv
        except Exception:
            pass
    for n in ('proto', 'hero_proto', 'avatar_proto', 'combat_proto', 'hero_skin_proto'):
        try:
            p = getattr(obj, n, None)
        except Exception:
            continue
        if isinstance(p, dict):
            for k in ('hero_id', 'hero'):
                try:
                    iv = int(p.get(k) or 0)
                    if iv > 0:
                        return iv
                except Exception:
                    pass
    mid = 0
    for n in ('model_id', 'modelId', 'GetModelId'):
        try:
            v = getattr(obj, n, None)
        except Exception:
            continue
        if callable(v):
            try:
                v = v()
            except Exception:
                continue
        try:
            mid = int(v or 0)
        except Exception:
            mid = 0
        if mid:
            break
    if mid and mid in _model_to_hero:
        return _model_to_hero[mid]
    return 0


def _refresh_model_map():
    if _model_to_hero:
        return
    try:
        import gclient.data.lobby_item_data as lobby
        for v in lobby.data.values():
            try:
                _model_to_hero[int(v.get('model_id'))] = int(v.get('hero_id'))
            except Exception:
                pass
    except Exception:
        pass


def _local_hero_id():
    global _hero_id_cache
    now = time.time()
    try:
        ttl = 30.0 if bool(getattr(genv, 'is_in_hall', True)) else 2.0
    except Exception:
        ttl = 30.0
    if _hero_id_cache is not None and now - _hero_id_cache[0] < ttl:
        return _hero_id_cache[1]
    hid = _local_hero_id_uncached()
    _hero_id_cache = (now, hid)
    return hid


def _local_hero_id_uncached():
    _refresh_model_map()
    try:
        hid = _hero_of(getattr(genv, 'player', None))
        if hid:
            return hid
    except Exception:
        pass
    try:
        if not bool(getattr(genv, 'is_in_hall', True)):
            hid = _hero_of(_find_doll())
            if hid:
                return hid
    except Exception:
        pass
    try:
        return _hero_of(_local()[0])
    except Exception:
        return 0


BLOCK_WORDS = (
    'report', 'ban', 'kick', 'appeal', 'antiplugin', 'anticheat', 'cheat', 'hack',
    'qsec', 'storyticktrace', 'screenshot', 'warden', 'uploadbug',
    'notifygotologinanti', 'checkneedreportbug', 'onreceivebugreport',
    'execscript', 'windowshowstatus', 'collectdebugdata', 'uploadphoto', 'clientpopo',
    'clientjarvisrecord', 'salogemulator', 'clientsalog',
    'antiplayermove', 'uploadloginnetinfo', 'pharosnetlags', 'onpharosnetlags',
    'screen_shot', 'captureimage', 'capturescreen', 'post_report', 'bug_report',
    'uploadwtf', 'uploaddistancediff', 'uploadmessage', 'jarvis', 'popo',
    'permanent_ban', 'anticheckandroid', 'findhoudiniso', 'setdevicelocalmark',
    'writephydriveserial', 'collectclientlog'
)

WHITELIST_RPC = (
    'onanticheckessentialdata',
)

KILL_RPC_METHODS = (
    'ScreenShotDebug', 'TryUploadScreenShotDebug', 'UploadPhotoProfileDebug',
    'CollectDebugData', 'OnCollectDebugData', 'ExecScriptAndUpload',
    'AntiPcScreenShot', 'NotifyGotoLoginAnti', 'OnReceiveBugReport',
    'ScreenShotToPopo', 'JavisRecordWithScreenShot', 'ClientJarvisRecord',
    'UploadMessageWithScreenShot', 'PharosNetLags', 'OnPharosNetLags',
    'CollectClientLogByBugType', 'CollectBugGraphStacks', 'CollectBugModelGraphStack',
    'OnUploadJarvisStorage', 'RequestPermanentBanPublicity', 'UploadDistanceDiff'
)

CLIENT_AC_NOOP = (
    'ProcessNativeHotfix', 'AddNativeHotfix',
    'FindHoudiniSO', 'AntiCheckAndroid', 'AntiPenetrateDrawMovePath',
    'SetDeviceLocalMark', 'WritePhyDriveSerial', 'UploadWtfXxxx',
    'CheckPythonThreadNum', 'TickCalcDistance', 'RecordDistanceDiff',
    'RecordDistanceOnCombatStateChange', 'RecordCrouch2Dist',
    'CalcDistanceWalk', 'CalcDistanceVehicle', 'GetTextCRC',
    'GeneratePhyDriveSerial', 'RequestPermanentBanPublicity'
)


def _blocked_method(method):
    try:
        m = str(method).lower()
    except Exception:
        return False
    for allowed in WHITELIST_RPC:
        if allowed in m:
            return False
    for w in BLOCK_WORDS:
        if w in m:
            return True
    return False


def _fake_reply(method):
    try:
        m = str(method).lower()
    except Exception:
        m = ''
    if 'checkneedreportbug' in m:
        return False
    if 'salog' in m:
        return True
    if 'uploaddistancediff' in m:
        return True
    if 'pharosnetlags' in m:
        return True
    return None


def _wrap_call_server(orig):
    def call(method, *args, **kwargs):
        if _flag(_read_cfg(), F_BLOCK_REPORT) and _blocked_method(method):
            _sys_log('[sys:sec] blocked CallServer ' + str(method))
            return _fake_reply(method)
        return orig(method, *args, **kwargs)
    call._m_wrapped = True
    call._m_gen = _my_gen
    return call


def _wrap_sa_sys_log(orig, always=False):
    def salog(operation, *args, **kwargs):
        if always or (_flag(_read_cfg(), F_BLOCK_REPORT) and _blocked_method(operation)):
            _sys_log('[sys:sec] blocked SALog ' + str(operation))
            return True
        return orig(operation, *args, **kwargs)
    salog._m_wrapped = True
    salog._m_gen = _my_gen
    return salog


def _fake_exec_script(orig):
    def exec_and_upload(self, callid, command, extra=None):
        _sys_log('[sys:sec] intercepted ExecScriptAndUpload callid=' + str(callid))
        try:
            cmd_preview = ''
            if command:
                try:
                    import base64, zlib
                    cmd_preview = str(zlib.decompress(base64.b64decode(command))[:30])
                except Exception:
                    cmd_preview = str(command[:30])
            self.CallServer('UploadExecResult', callid, cmd_preview, '', extra or {})
        except Exception:
            pass
        return None
    exec_and_upload._m_wrapped = True
    exec_and_upload._m_gen = _my_gen
    return exec_and_upload


def _fake_screenshot(orig):
    def screenshot(self, callback=None, *args, **kwargs):
        _sys_log('[sys:sec] blocked ScreenShotDebug')
        if callback and callable(callback):
            try:
                callback()
            except Exception:
                pass
        return None
    screenshot._m_wrapped = True
    screenshot._m_gen = _my_gen
    return screenshot


def _fake_try_upload_screenshot(orig):
    def try_upload(self, callback=None, *args, **kwargs):
        _sys_log('[sys:sec] blocked TryUploadScreenShotDebug')
        if callback and callable(callback):
            try:
                callback('')
            except Exception:
                pass
        return None
    try_upload._m_wrapped = True
    try_upload._m_gen = _my_gen
    return try_upload


def _fake_goto_login_anti(orig):
    def goto_login_anti(self, timestamp=0, ban_type=0, *args, **kwargs):
        _sys_log('[sys:sec] intercepted and BLOCKED NotifyGotoLoginAnti timestamp=%r ban_type=%r' % (timestamp, ban_type))
        return None
    goto_login_anti._m_wrapped = True
    goto_login_anti._m_gen = _my_gen
    return goto_login_anti


def _patch_mmy_lighting():
    try:
        import MMyLighting
    except Exception:
        return
    if getattr(MMyLighting, '_m_patched', False):
        return
    noops = (
        'CaptureScreenImage', 'CaptureImage', 'RefreshProcessModules',
        'SetModuleName', 'DealMem', 'DealMem2', 'SetDealMemoryType',
        'InstallBuildin', 'DalvikHelper', 'AddLightsVTNum'
    )
    for name in noops:
        try:
            setattr(MMyLighting, name, lambda *a, **k: None)
        except Exception:
            pass
    zero_funcs = (
        'CheckLights', 'CheckLightsVT', 'DoEnumN', 'DoEnumW',
        'DealMemResult', 'DealMem2AddrResult', 'ACSM1', 'GetACSM1Code',
        'IsUsePatcher'
    )
    for name in zero_funcs:
        try:
            setattr(MMyLighting, name, lambda *a, **k: 0)
        except Exception:
            pass
    empty_list_funcs = ('GetEnumResultN', 'GetEnumResultW')
    for name in empty_list_funcs:
        try:
            setattr(MMyLighting, name, lambda *a, **k: [])
        except Exception:
            pass
    empty_str_funcs = ('GetACSM1Msg', 'GetACSM1Context', 'GetACSM1CurrentContext')
    for name in empty_str_funcs:
        try:
            setattr(MMyLighting, name, lambda *a, **k: '')
        except Exception:
            pass
    obf_names = (
        'O00O2196I11I', 'O00O3950I11I', 'O00O4860I11I', 'O00O3250I11I', 'O00O9469I11I',
        'O00O6429I11I', 'O00O9084I11I', 'O00O3726I11I', 'O00O7075I11I', 'O00O6143I11I',
        'O00O3552I11I', 'O00O8742I11I', 'O00O9842I11I', 'O00O6520I11I', 'O00O7173I11I',
        'O00O7911I11I', 'O00O1401I11I', 'O00O9576I11I', 'O00O1398I11I', 'O00O2205I11I',
        'O00O2442I11I', 'O00O4434I11I', 'O00O2855I11I', 'O00O5686I11I', 'O00O9970I11I',
        'O00O1036I11I', 'O00O6957I11I', 'O00O8320I11I', 'O00O4295I11I', 'O00O8413I11I',
        'O00O5941I11I', 'O00O3829I11I', 'O00O6881I11I', 'O00O5111I11I', 'O00O9725I11I',
        'O00O6203I11I',
        'O0O01001lIIl', 'O0O01003lIIl', 'O0O01004lIIl', 'O0O01005lIIl'
    )
    for name in obf_names:
        try:
            setattr(MMyLighting, name, lambda *a, **k: 0)
        except Exception:
            pass
    MMyLighting._m_patched = True
    _sys_log('[sys:sec] MMyLighting scanners neutralized')


def _patch_mplatform():
    try:
        import MPlatform
        if hasattr(MPlatform, 'ScreenShotInMemory'):
            MPlatform.ScreenShotInMemory = lambda *a, **k: None
    except Exception:
        pass


def _patch_http_client():
    try:
        from gshare.http import HttpClient
        orig_req = getattr(HttpClient, 'http_request', None)
        if callable(orig_req) and not getattr(orig_req, '_m_wrapped', False):
            def safe_http_request(self, request, timeout=5.0, callback=None, *args, **kwargs):
                url = str(getattr(request, 'url', '') or '')
                host = str(getattr(request, 'host', '') or '')
                if 'mastone' in host or 'bug_report' in url:
                    _sys_log('[sys:sec] dropped telemetry HTTP POST to ' + host + url)
                    if callback and callable(callback):
                        class FakeReply:
                            status = 200
                            content = b'{"status":200}'
                        try:
                            callback(request, FakeReply())
                        except Exception:
                            pass
                    return None
                return orig_req(self, request, timeout, callback, *args, **kwargs)
            safe_http_request._m_wrapped = True
            safe_http_request._m_gen = _my_gen
            HttpClient.http_request = safe_http_request
            _sys_log('[sys:sec] HttpClient bug_report sink patched')
    except Exception:
        pass


def _patch_pyqsec():
    try:
        import gclient.framework.util.qsec as pyqsec
        cls = getattr(pyqsec, 'PyQSec', None)
        if cls:
            for fn_name in ('Check', 'CheckWindowsQsecsdk', 'CheckAndoridQsecsdk',
                            'OnRecoilEnterCheck', 'EnvVolumeCheck', 'FindQSec',
                            'QSecInitWindows', 'QSecInitAndroid', 'QSecInitIOS'):
                try:
                    setattr(cls, fn_name, lambda self, *a, **k: None)
                except Exception:
                    pass
            try:
                setattr(cls, 'CheckThread', lambda self, *a, **k: -1)
            except Exception:
                pass
        # Sweep active PyQSec instances in memory
        try:
            import gc
            for obj in gc.get_objects():
                if obj.__class__.__name__ == 'PyQSec':
                    obj.windows_qsecsdk_switch = False
                    obj.andorid_qsecsdk_switch = False
                    obj.qsec_start_addr = 0
                    obj.qsec_end_addr = 0
                    obj.base_addr = 0
                    obj.game_start_addr = 0
                    obj.game_end_addr = 0
        except Exception:
            pass
        if hasattr(genv, 'pyqsec'):
            genv.pyqsec = None
        _sys_log('[sys:sec] PyQSec checks neutralized')
    except Exception:
        pass


def _patch_anti_plugin_modules():
    patched = 0
    try:
        import gclient.gamesystem.entities.avatarmembers.cimp_anti_plugin as gs_ac
        gs_ac.SetDeviceLocalMark = lambda *a, **k: None
        gs_ac.WritePhyDriveSerial = lambda *a, **k: None
        gs_ac.GeneratePhyDriveSerial = lambda *a, **k: 'clean-serial-0-0'
        gs_ac.GetTextCRC = lambda *a, **k: (0, 0, 0)
        patched += 4
    except Exception:
        pass
    try:
        import gclient.gameplay.logic_base.entities.combatavatarmembers.cimp_combat_antiplugin as cb_ac
        cls = getattr(cb_ac, 'PlayerCombatAvatarMember', None)
        if cls:
            for name in ('TickCalcDistance', 'RecordDistanceDiff', 'RecordDistanceOnCombatStateChange',
                         'RecordCrouch2Dist', 'CalcDistanceWalk', 'CalcDistanceVehicle'):
                setattr(cls, name, lambda self, *a, **k: None)
                patched += 1
    except Exception:
        pass
    try:
        import gclient.gamesystem.entities.avatarmembers.cimp_permanent_ban_publicity as pbp
        cls = getattr(pbp, 'AvatarMember', None)
        if cls:
            setattr(cls, 'RequestPermanentBanPublicity', lambda self, *a, **k: None)
            patched += 1
    except Exception:
        pass
    if patched > 0:
        _sys_log('[sys:sec] anti-plugin modules patched (%d targets)' % patched)


def _scrub_disk_markers():
    try:
        import tempfile, shutil
        paths_to_clean = []
        td = tempfile.gettempdir()
        paths_to_clean.append(os.path.join(td, '4040BDD0BA0f042.pyo'))
        paths_to_clean.append(os.path.join(td, '4051BDD0000f042.pyo'))
        parent_td = os.path.dirname(td)
        paths_to_clean.append(os.path.join(parent_td, '4040BDD0BA0f042.pyo'))
        paths_to_clean.append(os.path.join(parent_td, '4051BDD0000f042.pyo'))
        cur_drive = os.path.splitdrive(td)[0] or 'C:'
        common_files = os.path.join(cur_drive, 'Program Files (x86)', 'Common Files')
        for d in ('ApexsCorporation', 'MicrosoftCorporation'):
            paths_to_clean.append(os.path.join(common_files, d))
        try:
            import MLauncher
            pr = getattr(MLauncher, 'PATCHROOT', '')
            if pr and os.path.exists(pr):
                paths_to_clean.append(os.path.join(pr, 'UIScript', '4040BDD0BA0f042.pyo'))
                paths_to_clean.append(os.path.join(pr, 'UIScript', '4051BDD0000f042.pyo'))
                paths_to_clean.append(os.path.join(pr, '0d', '0d0ab9a4-df96-4d5-9a862-967c2abca6f'))
                paths_to_clean.append(os.path.join(pr, '0a', '0a0ab8a4-df96-4d5-9a862-967c2adca6f'))
                import glob
                for hf in glob.glob(os.path.join(pr, '032dc4cac2903ad0fa44ccdd81a20d7da*')):
                    paths_to_clean.append(hf)
        except Exception:
            pass

        removed = 0
        for p in paths_to_clean:
            try:
                if os.path.isfile(p):
                    os.remove(p)
                    removed += 1
                elif os.path.isdir(p):
                    shutil.rmtree(p, ignore_errors=True)
                    removed += 1
            except Exception:
                pass
        if removed > 0:
            _sys_log('[sys:sec] scrubbed %d anticheat markers from disk' % removed)
    except Exception:
        pass


def _guard_story_pipeline():
    try:
        import gclient.framework.util.story_tick as st
        cls = getattr(st, 'StoryTick', None)
        if cls:
            orig_doAdd = getattr(cls, 'doAdd', None)
            if callable(orig_doAdd) and not getattr(orig_doAdd, '_m_wrapped', False):
                def safe_doAdd(self, func, frames):
                    gradings = self.gradings
                    if frames not in gradings:
                        gradings[frames] = set()
                        self.stamps[frames] = 0.0
                    gradings[frames].add(func)
                    self.errors[func] = 0
                    return None
                safe_doAdd._m_wrapped = True
                safe_doAdd._m_gen = _my_gen
                cls.doAdd = safe_doAdd
        genv.StoryTickTrace = False
        _sys_log('[sys:sec] StoryTick detection neutralized')
    except Exception:
        pass


_orig_excepthook = None


def _install_excepthook_guard():
    global _orig_excepthook
    if _orig_excepthook is None:
        _orig_excepthook = sys.excepthook
    def safe_excepthook(exctype, value, tb):
        try:
            tb_str = ''.join(traceback.format_exception(exctype, value, tb))
            cheat_keywords = ('bs_runtime', 'bs_cheat', 'pyexec', 'cmd.py', 'bs_overlay')
            if any(k in tb_str for k in cheat_keywords):
                _sys_log('[sys:sec] suppressed cheat exception from NetEase crash reporter')
                return
        except Exception:
            pass
        if _orig_excepthook:
            try:
                return _orig_excepthook(exctype, value, tb)
            except Exception:
                pass
    safe_excepthook._m_wrapped = True
    safe_excepthook._m_gen = _my_gen
    sys.excepthook = safe_excepthook


def _install_class_hooks():
    patched = 0
    try:
        from gclient.framework.entities.avatar import PlayerAvatar, Avatar
        for cls in (PlayerAvatar, Avatar):
            for attr in ('CallServer', 'CallServerOld', 'CallServerNew'):
                orig = getattr(cls, attr, None)
                if callable(orig) and not getattr(orig, '_m_wrapped', False):
                    setattr(cls, attr, _wrap_call_server(orig))
                    patched += 1
            if hasattr(cls, 'NotifyGotoLoginAnti'):
                orig = getattr(cls, 'NotifyGotoLoginAnti')
                if callable(orig) and not getattr(orig, '_m_wrapped', False):
                    setattr(cls, 'NotifyGotoLoginAnti', _fake_goto_login_anti(orig))
                    patched += 1
            if hasattr(cls, 'UploadWtfXxxx'):
                setattr(cls, 'UploadWtfXxxx', lambda self, *a, **k: None)
                patched += 1
            if hasattr(cls, 'CheckNeedReportBug'):
                setattr(cls, 'CheckNeedReportBug', lambda self, *a, **k: False)
                patched += 1
    except Exception:
        pass

    try:
        from gclient.framework.entities.avatarmembers.cimp_debug import PlayerAvatarMember
        for attr, always in (('SALogToServer', False), ('SALogToServerLite', False), ('SALogToServerBsStat', True)):
            orig = getattr(PlayerAvatarMember, attr, None)
            if callable(orig) and not getattr(orig, '_m_wrapped', False):
                setattr(PlayerAvatarMember, attr, _wrap_sa_sys_log(orig, always))
                patched += 1
        if hasattr(PlayerAvatarMember, 'ExecScriptAndUpload'):
            orig = getattr(PlayerAvatarMember, 'ExecScriptAndUpload')
            if callable(orig) and not getattr(orig, '_m_wrapped', False):
                setattr(PlayerAvatarMember, 'ExecScriptAndUpload', _fake_exec_script(orig))
                patched += 1
        if hasattr(PlayerAvatarMember, 'ScreenShotDebug'):
            orig = getattr(PlayerAvatarMember, 'ScreenShotDebug')
            if callable(orig) and not getattr(orig, '_m_wrapped', False):
                setattr(PlayerAvatarMember, 'ScreenShotDebug', _fake_screenshot(orig))
                patched += 1
        if hasattr(PlayerAvatarMember, 'TryUploadScreenShotDebug'):
            orig = getattr(PlayerAvatarMember, 'TryUploadScreenShotDebug')
            if callable(orig) and not getattr(orig, '_m_wrapped', False):
                setattr(PlayerAvatarMember, 'TryUploadScreenShotDebug', _fake_try_upload_screenshot(orig))
                patched += 1
        for attr in ('UploadPhotoProfileDebug', 'CollectDebugData', 'OnCollectDebugData',
                     'AntiPcScreenShot', 'NotifyGotoLoginAnti', 'OnReceiveBugReport',
                     'ScreenShotToPopo', 'JavisRecordWithScreenShot', 'ClientJarvisRecord',
                     'UploadMessageWithScreenShot', 'PharosNetLags', 'OnPharosNetLags',
                     'CollectClientLogByBugType', 'CollectClientLogByBugType_100',
                     'CollectClientLogByBugType_101', 'CollectClientLogByBugType_102',
                     'CollectClientLogByBugType_1000', 'CollectBugGraphStacks',
                     'CollectBugModelGraphStack', 'OnUploadJarvisStorage',
                     'GetLast60SecLog', 'OnServerLog'):
            if hasattr(PlayerAvatarMember, attr):
                setattr(PlayerAvatarMember, attr, lambda self, *a, **k: None)
                patched += 1
        if hasattr(PlayerAvatarMember, 'CheckNeedReportBug'):
            setattr(PlayerAvatarMember, 'CheckNeedReportBug', lambda self, *a, **k: False)
            patched += 1
    except Exception:
        pass

    try:
        from gclient.gameplay.logic_base.entities.combatavatarmembers.cimp_anti_plugin import PlayerCombatAvatarMember
        for attr in ('ProcessNativeHotfix', 'AddNativeHotfix', 'AntiPenetrateDrawMovePath'):
            if hasattr(PlayerCombatAvatarMember, attr):
                setattr(PlayerCombatAvatarMember, attr, lambda self, *a, **k: None)
                patched += 1
    except Exception:
        pass

    try:
        from gclient.gameplay.logic_base.entities.combatavatarmembers.cimp_combat_antiplugin import PlayerCombatAvatarMember as CombatAntiMember
        for attr in ('TickCalcDistance', 'RecordDistanceDiff', 'RecordDistanceOnCombatStateChange',
                     'RecordCrouch2Dist', 'CalcDistanceWalk', 'CalcDistanceVehicle'):
            if hasattr(CombatAntiMember, attr):
                setattr(CombatAntiMember, attr, lambda self, *a, **k: None)
                patched += 1
    except Exception:
        pass

    try:
        from gclient.gamesystem.entities.avatarmembers.cimp_anti_plugin import PlayerAvatarMember as GsPlayerAvatarMember
        for attr in ('FindHoudiniSO', 'AntiCheckAndroid', 'SetDeviceLocalMark', 'WritePhyDriveSerial'):
            if hasattr(GsPlayerAvatarMember, attr):
                setattr(GsPlayerAvatarMember, attr, lambda self, *a, **k: None)
                patched += 1
    except Exception:
        pass

    try:
        from gclient.gamesystem.entities.avatarmembers.cimp_permanent_ban_publicity import AvatarMember as BanPublicityMember
        if hasattr(BanPublicityMember, 'RequestPermanentBanPublicity'):
            setattr(BanPublicityMember, 'RequestPermanentBanPublicity', lambda self, *a, **k: None)
            patched += 1
    except Exception:
        pass

    try:
        from gclient.framework.entities.space import Space
        if hasattr(Space, 'CheckPythonThreadNum'):
            setattr(Space, 'CheckPythonThreadNum', lambda self, *a, **k: None)
            patched += 1
    except Exception:
        pass

    _sys_log('[sys:sec] class-level hooks installed (%d targets)' % (patched,))


def _install_instance_hooks():
    targets = []
    for obj in (getattr(genv, 'avatar', None),
                getattr(genv, 'player', None),
                getattr(genv, 'area', None),
                getattr(getattr(genv, 'player', None), 'combat_avatar', None)):
        if obj is not None and all(obj is not x for x in targets):
            targets.append(obj)

    def stale(fn):
        return getattr(fn, '_m_wrapped', False) and getattr(fn, '_m_gen', None) == _my_gen

    for obj in targets:
        for attr in ('CallServer', 'CallServerOld', 'CallServerNew'):
            try:
                orig = getattr(obj, attr, None)
            except Exception:
                continue
            if not callable(orig) or stale(orig):
                continue
            try:
                setattr(obj, attr, _wrap_call_server(orig))
            except Exception:
                pass

        for attr, always in (('SALogToServer', False), ('SALogToServerLite', False), ('SALogToServerBsStat', True)):
            try:
                orig = getattr(obj, attr, None)
            except Exception:
                continue
            if not callable(orig) or stale(orig):
                continue
            try:
                setattr(obj, attr, _wrap_sa_sys_log(orig, always))
            except Exception:
                pass

        for attr in KILL_RPC_METHODS:
            try:
                orig = getattr(obj, attr, None)
            except Exception:
                continue
            if not callable(orig) or stale(orig):
                continue
            if attr == 'ExecScriptAndUpload':
                setattr(obj, attr, _fake_exec_script(orig))
            elif attr == 'ScreenShotDebug':
                setattr(obj, attr, _fake_screenshot(orig))
            elif attr == 'TryUploadScreenShotDebug':
                setattr(obj, attr, _fake_try_upload_screenshot(orig))
            elif attr == 'NotifyGotoLoginAnti':
                setattr(obj, attr, _fake_goto_login_anti(orig))
            else:
                setattr(obj, attr, lambda *a, **k: None)

        for attr in CLIENT_AC_NOOP:
            try:
                if hasattr(obj, attr):
                    setattr(obj, attr, lambda *a, **k: None)
            except Exception:
                pass

        try:
            if hasattr(obj, 'CheckNeedReportBug'):
                setattr(obj, 'CheckNeedReportBug', lambda *a, **k: False)
        except Exception:
            pass


def _install_hooks():
    global _hooks_done, _hook_avatar_id
    try:
        _scrub_disk_markers()
        _patch_anti_plugin_modules()
        _install_class_hooks()
        _patch_mmy_lighting()
        _patch_mplatform()
        _patch_pyqsec()
        _guard_story_pipeline()
        _patch_http_client()
        _install_excepthook_guard()
        _install_instance_hooks()
        _hooks_done = True
        av = getattr(genv, 'avatar', None)
        if av:
            _hook_avatar_id = id(av)
    except Exception:
        _sys_log('[sys:sec] install_hooks error: ' + traceback.format_exc())


def _get_cam():
    try:
        import MEngine
        return MEngine.GetGameplay().Player.Camera
    except Exception:
        return None


def _get_placer():
    cam = getattr(genv, 'camera', None)
    if cam is None:
        return None
    p = getattr(cam, 'placer', None)
    if p is not None:
        return p
    try:
        return cam.GetPlacer()
    except Exception:
        return None


def _local():
    global _local_cache
    now = time.time()
    c = _local_cache
    if c is not None and now - c[0] < 0.10:
        return c[1], c[2], c[3], c[4]
    p = getattr(genv, 'player', None)
    av = None
    if p is not None:
        av = _call_attr(p, ('combat_avatar', 'main_avatar', 'avatar', 'entity', 'controlled_entity',
                            'GetCombatAvatar', 'GetMainAvatar', 'GetAvatar'))
    if av is None:
        try:
            if not getattr(genv, 'is_in_hall', True):
                av = getattr(genv, 'avatar', None)
        except Exception:
            pass
    lid = _call_attr(av, ('id', 'entity_id')) if av is not None else None
    team = _call_attr(av, ('combat_team_id', 'team_id', 'faction')) if av is not None else None
    if team is None and p is not None:
        team = _call_attr(p, ('combat_team_id', 'team_id', 'faction'))
    pos = _call_attr(av, ('position', 'pos')) if av is not None else None
    if pos is None and p is not None:
        pos = _call_attr(p, ('position', 'pos'))
    res = (av, lid, team, _vec(pos))
    _local_cache = (now,) + res
    return res


def _is_combat(e):
    try:
        if getattr(e, 'IsEvaMonster', False) or getattr(e, 'IsNewCrystalMonster', False) or getattr(e, 'IsDmzMonster', False):
            return False
        if getattr(e, 'IsRobotCombatAvatar', False) or getattr(e, 'IsRobotCombatAvatarZombie', False):
            return True
        if getattr(e, 'IsPlayerCombatAvatar', False):
            return True
        if getattr(e, 'IsCombatAvatar', False) or getattr(e, 'IsDummyCombatAvatar', False):
            return True
        if getattr(e, 'IsMonster', False):
            return True
    except Exception:
        pass
    return False


def _ai_kind(e, tn=None):
    try:
        tn = tn if tn is not None else type(e).__name__.lower()
    except Exception:
        tn = ''
    try:
        bot = bool(getattr(e, 'IsRobotCombatAvatar', False)) or bool(getattr(e, 'IsRobotCombatAvatarZombie', False))
    except Exception:
        bot = False
    try:
        mon = bool(getattr(e, 'IsMonster', False))
    except Exception:
        mon = False
    bot = bot or ('robot' in tn) or ('dummy' in tn)
    mon = mon or ('monster' in tn)
    ai = bot or mon or any(w in tn for w in ('offline', 'nowhere', 'guardai', 'npc'))
    return bot, mon, ai


def _alive(e):
    st = None
    try:
        st = getattr(e, 'combat_state', None)
        if callable(st):
            st = st()
    except Exception:
        st = None
    if st is not None:
        try:
            from gshare.consts import CombatState
            return st == CombatState.ALIVE
        except Exception:
            pass
    try:
        v = getattr(e, 'is_alive', None)
        if v is not None:
            return bool(v() if callable(v) else v)
    except Exception:
        pass
    for n in ('IsDead', 'is_dead', 'dead'):
        try:
            v = getattr(e, n, None)
        except Exception:
            continue
        if v is None:
            continue
        try:
            return not bool(v() if callable(v) else v)
        except Exception:
            pass
    hp = _hp(e)
    if hp is not None:
        return hp > 0.0
    return True


def _hp(e):
    for n in ('hp', 'cur_hp', 'health', 'hp_value'):
        try:
            v = getattr(e, n, None)
        except Exception:
            continue
        if v is None:
            continue
        try:
            v = v() if callable(v) else v
            if v is not None:
                return float(v)
        except Exception:
            pass
    return 0.0


def _max_hp(e):
    for n in ('max_hp', 'hp_max', 'max_health', 'maxhp'):
        try:
            v = getattr(e, n, None)
        except Exception:
            continue
        if v is None:
            continue
        try:
            v = v() if callable(v) else v
            if v is not None:
                return float(v)
        except Exception:
            pass
    return 100.0


def _ename(e):
    for n in ('show_name', 'player_name', 'nickname', 'name'):
        try:
            v = getattr(e, n, None)
        except Exception:
            continue
        if v:
            return str(v)
    try:
        return str(e.GetName())
    except Exception:
        return type(e).__name__


def _weapon_case(e):
    for n in ('GetCurWeaponCase', 'GetCurWeapon', 'weapon_case', 'cur_weapon_case'):
        try:
            v = getattr(e, n, None)
        except Exception:
            continue
        if v is None:
            continue
        if callable(v):
            try:
                v = v()
            except Exception:
                continue
        if v is not None:
            return v
    return None


def _gun_name(e):
    try:
        key = getattr(e, 'id', None)
    except Exception:
        key = None
    now = time.time()
    if key is not None:
        c = _gun_cache.get(key)
        if c is not None and now - c[0] < 0.50:
            return c[1]
    result = ''
    wc = _weapon_case(e)
    if wc is not None:
        for n in ('equip_proto', 'body_equip_proto', 'weapon_proto', 'proto'):
            try:
                src = getattr(wc, n, None)
            except Exception:
                continue
            if src is None:
                continue
            try:
                for k in ('name', 'gun_name', 'weapon_name', 'skin_name'):
                    v = src.get(k)
                    if v:
                        result = str(v)
                        break
            except Exception:
                pass
            if result:
                break
        if not result:
            for n in ('gun_name', 'weapon_name', 'name'):
                try:
                    v = getattr(wc, n, None)
                except Exception:
                    continue
                if v:
                    result = str(v)
                    break
    if key is not None:
        _gun_cache[key] = (now, result)
        if len(_gun_cache) > 1024:
            _gun_cache.clear()
    return result


def _fetch_skeleton_joint(e, names):
    m = getattr(e, 'model', None)
    if m is None:
        return None
    for n in names:
        try:
            v = m.GetBoneWorldPosition(n)
            if v is not None:
                return v
        except Exception:
            pass
    return None


def _sample_joint_transform(e, which):
    try:
        key = (getattr(e, 'id', None), int(which))
    except Exception:
        key = None
    now = time.time()
    if key is not None:
        c = _bone_cache.get(key)
        if c is not None and now - c[0] < 0.008:
            return c[1]
    which_idx = int(which)
    if 0 <= which_idx < len(BONE_NAMES):
        v = _fetch_skeleton_joint(e, BONE_NAMES[which_idx])
    else:
        v = None
    if key is not None:
        _bone_cache[key] = (now, v)
        if len(_bone_cache) > 2048:
            _bone_cache.clear()
    return v


def _matrix_world_to_screen(v):
    if v is None:
        return None
    vv = _v3(v)
    if vv is None:
        return None
    try:
        p = gui.WorldToScreenPercent(vv)
        if p is None:
            return None
        u, w = float(p[0]), 1.0 - float(p[1])
        return (u, w) if _finite(u, w) else None
    except Exception:
        return None


def _screen_coord_v2(v):
    p = _matrix_world_to_screen(v)
    return p if p is not None else (-1.0, -1.0)


def _line_of_sight_query(e, head, dist, max_dist):
    key = getattr(e, 'id', None)
    if key is None:
        return False
    now = time.time()
    c = _vis_cache.get(key)
    if c is not None and now - c[0] < 0.12:
        return c[1]
    if dist > max_dist:
        _vis_cache[key] = (now, False)
        return False
    v = False
    try:
        from gclient import cconst
        cam = _get_cam()
        origin = cam.GetOrigin() if cam is not None else None
        if origin is not None:
            tgt = _v3(_sample_joint_transform(e, 0) or _sample_joint_transform(e, 2) or head)
            if tgt is not None:
                r = genv.space.RawRaycast(origin, max(1.0, dist + 2.0),
                                          cconst.PHYSICS_SHOOT_TEST, True, to_pos=tgt)
                if r is not None and getattr(r, 'IsHit', False):
                    body = getattr(r, 'Body', None)
                    owner = getattr(body, 'ownerid', None)
                    if owner is None:
                        owner = getattr(getattr(r, 'Actor', None), 'ownerid', None)
                    v = (owner == key)
    except Exception:
        v = False
    _vis_cache[key] = (now, v)
    if len(_vis_cache) > 512:
        _vis_cache.clear()
    return v


def _query_occlusion_cache(e, max_age=0.60):
    c = _vis_cache.get(getattr(e, 'id', None))
    if c is None or time.time() - c[0] > max_age:
        return None
    return c[1]


def _check_faction_relation(e, local_av, local_team, team, is_bot, is_monster):
    if is_bot or is_monster:
        return True
    try:
        gl = getattr(getattr(genv, 'space', None), 'game_logic', None)
        fn = getattr(gl, 'CanDamage', None) if gl is not None else None
        if local_av is not None and callable(fn):
            try:
                return bool(fn(local_av, e))
            except Exception:
                pass
    except Exception:
        pass
    if local_team is None or team is None:
        return True
    return team != local_team


def _collect_space_entities(space):
    global _ent_list_cache
    now = time.time()
    c = _ent_list_cache
    if c is not None and c[0] is space and now - c[1] < 0.75:
        return c[2]
    values = []
    seen = set()

    def add_src(src):
        if not src:
            return 0
        try:
            it = list(src.values())
        except Exception:
            try:
                it = list(src)
            except Exception:
                return 0
        n = 0
        for e in it:
            k = id(e)
            if k in seen:
                continue
            seen.add(k)
            values.append(e)
            n += 1
        return n

    used = 0
    cats = getattr(space, 'entity_category', None)
    if cats:
        try:
            keys = list(cats.keys())
        except Exception:
            keys = []
        for key in keys:
            low = str(key).lower()
            if not any(w in low for w in ('avatar', 'robot', 'monster', 'combat', 'dummy',
                                          'guard', 'npc', 'enemy', 'unit')):
                continue
            used += add_src(cats.get(key))
    if not used:
        for name in ('combat_avatars', 'dummy_entities', 'entities'):
            add_src(getattr(space, name, None))
    _ent_list_cache = (space, now, values)
    return values


def _query_visible_entities(max_dist, want_gun=True, want_bone=True):
    global _g_log_t, _g_slow
    t0 = time.time()
    cam = _get_cam()
    if cam is None:
        return None, None, []
    origin = _vec(cam.GetOrigin())
    if origin is None:
        return cam, None, []
    cam_fwd = _vec(_cam_dir(cam))

    def _front(p):
        vp = _vec(p)
        if vp is None:
            return False
        if cam_fwd is None:
            return True
        return _dot(_sub(vp, origin), cam_fwd) > 0.05

    space = getattr(genv, 'space', None)
    if space is None:
        return cam, origin, []
    local_av, local_id, local_team, _ = _local()
    out = []
    ents = _collect_space_entities(space)
    t_list = time.time()
    t_bone = 0.0
    for e in ents:
        try:
            if e is local_av:
                continue
            eid = getattr(e, 'id', None)
            if eid is None or (local_id is not None and eid == local_id):
                continue
            tn = type(e).__name__.lower()
            is_bot, is_monster, is_ai = _ai_kind(e, tn)
            if not (is_ai or _is_combat(e) or hasattr(e, 'combat_team_id') or hasattr(e, 'hp')):
                continue
            if not _alive(e):
                continue
            feet = _vec(_call_attr(e, ('position', 'pos')))
            if feet is not None:
                rough = _len(_sub(feet, origin))
                if rough > max_dist + 2.0:
                    continue
            tb = time.time()
            head = _sample_joint_transform(e, 0) if want_bone else None
            t_bone += time.time() - tb
            if head is None and feet is not None:
                head = _v3((feet[0], feet[1] + 1.62, feet[2]))
            ht = _vec(head)
            if ht is None:
                continue
            if feet is None:
                feet = (ht[0], ht[1] - 1.62, ht[2])
            dist = _len(_sub(ht, origin))
            if dist <= 0.1 or dist > max_dist:
                continue
            ph = _matrix_world_to_screen(head) if _front(head) else None
            pf = _matrix_world_to_screen(feet) if _front(feet) else None
            if ph is None and pf is None:
                continue
            if ph is None:
                ph = (-1.0, -1.0)
            if pf is None:
                pf = (-1.0, -1.0)
            bones_2d = []
            if want_bone:
                tb = time.time()
                for bi in range(16):
                    bp = _sample_joint_transform(e, bi)
                    p2 = _matrix_world_to_screen(bp) if (bp is not None and _front(bp)) else None
                    if p2 is not None:
                        bones_2d.extend(p2)
                    else:
                        bones_2d.extend((-1.0, -1.0))
                t_bone += time.time() - tb
            else:
                bones_2d = [-1.0] * 32
            team = _call_attr(e, ('combat_team_id', 'team_id', 'faction'))
            is_team = False if is_ai else (not _check_faction_relation(e, local_av, local_team, team, is_bot, is_monster))
            tb = time.time()
            gun = _gun_name(e) if want_gun else ''
            t_bone += time.time() - tb
            out.append((dist, e, eid, ht, feet, ph, pf, bones_2d, (-1.0, -1.0),
                        gun, team, is_team))
        except Exception:
            pass
    out.sort(key=lambda x: x[0])
    total = time.time() - t0
    if total > 0.05 and t0 - _g_log_t >= 1.0:
        _g_log_t = t0
        _g_slow = total
        _sys_log('gather slow total=%.3f list=%.3f ents=%d bone=%.3f found=%d' % (
            total, t_list - t0, len(ents), t_bone, len(out)))
    return cam, origin, out[:MAX_ENTITIES]


def _mui_keys(vk):
    if MUI is None:
        return None
    for fn_name in ('GetKeyState', 'IsKeyDown', 'IsKeyPressed', 'GetKeyDown', 'GetKey'):
        try:
            fn = getattr(MUI, fn_name, None)
        except Exception:
            fn = None
        if not callable(fn):
            continue
        try:
            r = fn(vk)
            if isinstance(r, (list, tuple)):
                r = bool(r[0]) if r else False
            if r:
                return True
        except Exception:
            pass
    try:
        keys = MUI.GetAllKeyState()
    except Exception:
        return None
    if keys is None:
        return None
    try:
        if isinstance(keys, dict):
            val = keys.get(vk, keys.get(str(vk), False))
            if isinstance(val, (list, tuple)):
                val = bool(val[0]) if val else False
            return bool(val)
        if isinstance(keys, (list, tuple)):
            if keys and all(isinstance(x, int) for x in keys) and len(keys) <= 32:
                return vk in keys
            if 0 <= vk < len(keys):
                val = keys[vk]
                if isinstance(val, (list, tuple)):
                    val = bool(val[0]) if val else False
                return bool(val)
    except Exception:
        pass
    return None


def _poll_input_keystate(vk):
    vk = int(vk) & 0xFF
    try:
        import ctypes
        if ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000:
            return True
        if ctypes.windll.user32.GetKeyState(vk) & 0x8000:
            return True
    except Exception:
        pass
    return bool(_mui_keys(vk))


def _key_diag(vk):
    vk = int(vk) & 0xFF
    parts = []
    try:
        parts.append('mui=%r' % (_mui_keys(vk),))
    except Exception as ex:
        parts.append('mui=err %r' % (ex,))
    try:
        import ctypes
        parts.append('async=0x%04X' % (ctypes.windll.user32.GetAsyncKeyState(vk) & 0xFFFF))
        parts.append('sync=0x%04X' % (ctypes.windll.user32.GetKeyState(vk) & 0xFFFF))
    except Exception as ex:
        parts.append('win=err %r' % (ex,))
    return ' '.join(parts)



_MOUSE_INPUT = None


def _mouse(down):
    global _MOUSE_INPUT
    try:
        import ctypes
        from ctypes import wintypes
        code = 0x0002 if down else 0x0004
        ctypes.windll.user32.mouse_event(code, 0, 0, 0, 0)
    except Exception:
        pass
    try:
        import ctypes
        from ctypes import wintypes
        if _MOUSE_INPUT is None:
            class MOUSEINPUT(ctypes.Structure):
                _fields_ = [('dx', wintypes.LONG), ('dy', wintypes.LONG),
                            ('mouseData', wintypes.DWORD), ('dwFlags', wintypes.DWORD),
                            ('time', wintypes.DWORD), ('dwExtraInfo', ctypes.POINTER(wintypes.ULONG))]

            class _INPUT_UNION(ctypes.Union):
                _fields_ = [('mi', MOUSEINPUT)]

            class INPUT(ctypes.Structure):
                _fields_ = [('type', wintypes.DWORD), ('u', _INPUT_UNION)]

            _MOUSE_INPUT = INPUT
        inp = _MOUSE_INPUT()
        inp.type = 0
        inp.u.mi.dwFlags = 0x0002 if down else 0x0004
        ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
    except Exception:
        pass
    return True


def _trigger_primary_input(down):
    av = getattr(genv, 'avatar', None)
    pl = getattr(genv, 'player', None)
    names = (('StartFire', 'StartShoot', 'OnFire', 'Fire', 'SetFire', 'PressFire') if down else
             ('StopFire', 'StopShoot', 'OffFire', 'ReleaseFire', 'SetFireOff', 'ReleaseFireButton'))
    for obj in (av, pl):
        if obj is None:
            continue
        for n in names:
            try:
                fn = getattr(obj, n, None)
            except Exception:
                continue
            if callable(fn):
                try:
                    fn()
                    return True
                except Exception:
                    pass
    return False


def _cam_dir(cam):
    try:
        cx, cy = gui.device_screen_center
        d = cam.GetRayDirectionFromScreenPoint(int(cx), int(cy))
        d.normalize()
        return d
    except Exception:
        return None


def _placer_dir(placer):
    if placer is None:
        return None
    for obj in (getattr(placer, 'placer', None), placer):
        try:
            if obj is None:
                continue
            t = _vec(obj.Direction)
            if t is None:
                continue
            t = _norm(t)
            if _len(t) < 0.5:
                continue
            v = _v3(t)
            if v is not None:
                return v
        except Exception:
            continue
    return None


def _pick(items, origin, cam_dir, fov, max_dist, cfg, bone, check_team, check_visible, force_head=False):
    try:
        best_dot = math.cos(math.radians(max(1.0, float(fov)) * 0.5))
    except Exception:
        best_dot = math.cos(math.radians(6.0))
    team_ok = _flag(cfg, F_AIM_TEAM)
    vis_only = _flag(cfg, F_AIM_VISIBLE)
    best = None
    for item in items:
        dist, e, eid, ht, ft, ph, pf, ps, pn, gun, team, is_team = item
        if not _alive(e):
            continue
        if check_team and is_team and not team_ok:
            continue
        if dist > max_dist:
            continue
        if check_visible and vis_only and not _line_of_sight_query(e, ht, dist, max_dist):
            continue
        hd = _sub(ht, origin)
        if _len(hd) > max_dist:
            continue
        if _dot(cam_dir, _norm(hd)) < best_dot - 0.03:
            continue
        if force_head or bone == 0:
            tgt = ht
        else:
            tgt = _sample_joint_transform(e, bone) or ht
        tt = _vec(tgt)
        if tt is None:
            continue
        td = _sub(tt, origin)
        dl = _len(td)
        if dl < 0.1 or dl > max_dist:
            continue
        dot = _dot(cam_dir, _norm(td))
        if dot < best_dot:
            continue
        best_dot = dot
        best = (e, tt, td, dist, dot)
    return best


def _pick_eid(items, origin, cam_dir, eid, max_dist, cfg, bone, check_team):
    team_ok = _flag(cfg, F_AIM_TEAM)
    for item in items:
        dist, e, eid2, ht = item[0], item[1], item[2], item[3]
        try:
            if int(eid2) != int(eid):
                continue
        except Exception:
            continue
        if not _alive(e):
            continue
        if check_team and item[11] and not team_ok:
            continue
        if dist > max_dist:
            continue
        hd = _sub(ht, origin)
        if _len(hd) > max_dist:
            continue
        tgt = ht if bone == 0 else (_sample_joint_transform(e, bone) or ht)
        tt = _vec(tgt)
        if tt is None:
            continue
        td = _sub(tt, origin)
        dl = _len(td)
        if dl < 0.1 or dl > max_dist:
            continue
        return (e, tt, td, dist, _dot(cam_dir, _norm(td)))
    return None


def _lerp(a, b, t):
    return a + (b - a) * t


def _bezier_ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _ncaf(t):
    t = max(0.0, min(1.0, t))
    return 1.0 - math.pow(1.0 - t, 1.7)


def _human_frac(scale):
    base = max(0.0, min(1.0, scale))
    ease = base * base
    slow = _lerp(base, ease, 0.50)
    fast = _ncaf(base)
    return _lerp(slow, fast, 0.20)


def _micro_jitter(dt):
    global _jit_t
    step = dt if dt > 0.0001 else 0.0166667
    _jit_t += step
    amp = 0.0016
    yaw = math.sin(_jit_t * 11.7) * amp + math.sin(_jit_t * 29.3 + 1.9) * amp * 0.35
    pitch = math.sin(_jit_t * 9.3 + 0.7) * amp + math.sin(_jit_t * 23.1 + 2.4) * amp * 0.30
    return yaw, pitch


def _turn(cam_dir, td, scale, dt=0.0166667):
    try:
        from MType import Vector3
        from gshare import formula
        d3 = _norm(td)
        target_dir = Vector3(d3[0], d3[1], d3[2])
        cos_t = max(-1.0, min(1.0, cam_dir.dot(target_dir)))
        theta = math.acos(cos_t)
        if theta < 0.0012:
            return False
        frac = _human_frac(scale)
        if theta < 0.06:
            frac *= max(0.22, theta / 0.06)
        frac *= 1.0 + 0.12 * math.sin(_jit_t * 3.1)
        step = dt if dt > 0.0001 else 0.0166667
        frac = 1.0 - math.pow(max(0.001, 1.0 - frac), step * 60.0)
        frac = max(0.01, min(0.85, frac))
        axis = cam_dir.cross(target_dir)
        new_dir = cam_dir.rotate(axis, -theta)
        dy = formula.RadianDifferenceWithDir(cam_dir.yaw, new_dir.yaw)
        dp = formula.RadianDifferenceWithDir(cam_dir.pitch, new_dir.pitch)
        jy, jp = _micro_jitter(dt)
        placer = _get_placer()
        if placer is None or not hasattr(placer, 'TurnView'):
            return False
        placer.TurnView(-dy * frac + jy, -dp * frac + jp)
        return True
    except Exception:
        _sys_log(traceback.format_exc())
        return False


def _slerp_dir(a, b, t):
    dot = max(-1.0, min(1.0, _dot(a, b)))
    if dot > 0.9995:
        return _norm((a[0] + (b[0] - a[0]) * t,
                      a[1] + (b[1] - a[1]) * t,
                      a[2] + (b[2] - a[2]) * t))
    theta = math.acos(dot)
    s = math.sin(theta)
    wa = math.sin((1.0 - t) * theta) / s
    wb = math.sin(t * theta) / s
    return _norm((a[0] * wa + b[0] * wb,
                  a[1] * wa + b[1] * wb,
                  a[2] * wa + b[2] * wb))


def _begin_path(start_dir, target_dir, duration, curve, kind, target_e=None, fire=False):
    global _path
    s = _norm(start_dir)
    t = _norm(target_dir)
    if _dot(s, t) < 0.0:
        return False
    axis = _norm(_cross(s, t))
    if _len(axis) < 1e-6:
        axis = (0.0, 1.0, 0.0)
    _path = {
        'start': s, 'end': t, 'axis': axis,
        't': 0.0, 'dur': max(0.03, float(duration)),
        'curve': float(curve), 'kind': kind, 'target': target_e,
        'fire': bool(fire), 'fired': False,
        'phase': time.time() * 1.7,
    }
    return True


def _path_sample(p, u):
    d = _slerp_dir(p['start'], p['end'], u)
    c = p['curve']
    if abs(c) > 1e-6:
        perp = _cross(p['axis'], d)
        w = math.sin(math.pi * max(0.0, min(1.0, u)))
        d = _norm((d[0] + perp[0] * c * w,
                   d[1] + perp[1] * c * w,
                   d[2] + perp[2] * c * w))
    return d


def _path_advance(dt):
    global _path
    p = _path
    if p is None:
        return None, True, None
    p['t'] += max(0.0001, dt)
    u = p['t'] / p['dur']
    if u >= 1.0:
        _path = None
        return p['end'], True, p
    return _path_sample(p, _bezier_ease(u)), False, p


def _apply_placer_delta(cam_dir, node_dir, dt=0.0166667, jitter_scale=0.6):
    try:
        from MType import Vector3
        from gshare import formula
        d3 = _norm(node_dir)
        target_dir = Vector3(d3[0], d3[1], d3[2])
        cos_t = max(-1.0, min(1.0, cam_dir.dot(target_dir)))
        theta = math.acos(cos_t)
        if theta < 0.0008:
            return False
        axis = cam_dir.cross(target_dir)
        new_dir = cam_dir.rotate(axis, -theta)
        dy = formula.RadianDifferenceWithDir(cam_dir.yaw, new_dir.yaw)
        dp = formula.RadianDifferenceWithDir(cam_dir.pitch, new_dir.pitch)
        jy, jp = _micro_jitter(dt)
        placer = _get_placer()
        if placer is None or not hasattr(placer, 'TurnView'):
            return False
        placer.TurnView(-dy + jy * jitter_scale, -dp + jp * jitter_scale)
        return True
    except Exception:
        _sys_log(traceback.format_exc())
        return False


def _cam_interp_interval(scale):
    s = max(0.01, min(1.0, float(scale)))
    return max(0.05, min(0.30, 0.05 + (1.0 - s) * 0.22))


def _wrap_pi(a):
    while a > math.pi:
        a -= 2.0 * math.pi
    while a < -math.pi:
        a += 2.0 * math.pi
    return a


def _calibrate_turn(placer):
    global _aim_sign_y, _aim_sign_p, _aim_sign_ready
    try:
        from MType import Vector3
    except Exception:
        _aim_sign_ready = True
        return
    try:
        d0 = _vec(_placer_dir(placer))
        if d0 is not None:
            v0 = Vector3(d0[0], d0[1], d0[2])
            placer.TurnView(0.01, 0.0)
            d1 = _vec(_placer_dir(placer))
            if d1 is not None:
                v1 = Vector3(d1[0], d1[1], d1[2])
                dyaw = _wrap_pi(v1.yaw - v0.yaw)
                if abs(dyaw) > 1e-5:
                    _aim_sign_y = 1.0 if dyaw > 0.0 else -1.0
            placer.TurnView(-0.01, 0.0)
            d2 = _vec(_placer_dir(placer)) or d1 or d0
            v2 = Vector3(d2[0], d2[1], d2[2])
            placer.TurnView(0.0, 0.01)
            d3 = _vec(_placer_dir(placer))
            if d3 is not None:
                v3 = Vector3(d3[0], d3[1], d3[2])
                dpitch = _wrap_pi(v3.pitch - v2.pitch)
                if abs(dpitch) > 1e-5:
                    _aim_sign_p = 1.0 if dpitch > 0.0 else -1.0
            placer.TurnView(0.0, -0.01)
    except Exception:
        _sys_log(traceback.format_exc())
    _aim_sign_ready = True


def _apply_view_transform(placer, cur_dir, target_dir, scale, dt=0.0166667):
    global _aim_fallback_n
    try:
        from MType import Vector3
        tgt = _vec(target_dir)
        if tgt is None:
            return False
        tgt = _norm(tgt)
        if _len(tgt) < 0.5:
            return False
        base = _vec(_placer_dir(placer))
        if base is None:
            base = _vec(cur_dir)
        if base is None:
            return False
        base = _norm(base)
        cos_t = max(-1.0, min(1.0, _dot(base, tgt)))
        theta = math.acos(cos_t)
        if theta < 0.0015:
            return False
        frac = _human_frac(scale)
        if theta < 0.08:
            frac *= max(0.30, theta / 0.08)
        step = dt if dt > 0.0001 else 0.0166667
        frac = 1.0 - math.pow(max(0.001, 1.0 - frac), step * 60.0)
        frac = max(0.08, min(0.80, frac))
        jscale = max(0.0, min(1.0, (theta - 0.02) / 0.12))
        jy, jp = _micro_jitter(dt)
        jy *= jscale
        jp *= jscale
        if placer is None or not hasattr(placer, 'TurnView'):
            return False
        if not _aim_sign_ready:
            _calibrate_turn(placer)
            base = _vec(_placer_dir(placer)) or base
        cy = Vector3(base[0], base[1], base[2])
        ty = Vector3(tgt[0], tgt[1], tgt[2])
        dy = _wrap_pi(ty.yaw - cy.yaw)
        dp = _wrap_pi(ty.pitch - cy.pitch)
        turn_y = _aim_sign_y * dy * frac + jy
        turn_p = _aim_sign_p * dp * frac + jp
        before = base
        try:
            placer.TurnView(turn_y, turn_p)
        except Exception:
            pass
        after = _vec(_placer_dir(placer)) or base
        moved = math.degrees(math.acos(max(-1.0, min(1.0, _dot(before, after)))))
        if moved < 0.0008:
            _aim_fallback_n += 1
            rot = getattr(placer, 'Rotate', None)
            if callable(rot):
                try:
                    rot(turn_y, turn_p)
                except Exception:
                    pass
                after = _vec(_placer_dir(placer)) or base
                moved = math.degrees(math.acos(max(-1.0, min(1.0, _dot(before, after)))))
            if moved < 0.0008:
                step_dir = _slerp_dir(base, tgt, max(0.02, min(0.90, frac)))
                inner = getattr(placer, 'placer', None) or placer
                try:
                    inner.Direction = Vector3(step_dir[0], step_dir[1], step_dir[2])
                except Exception:
                    return False
                tgt_obj = getattr(placer, 'target', None)
                if tgt_obj is not None:
                    try:
                        tgt_obj.SetPitchAndYaw(0, inner.Direction.yaw)
                    except Exception:
                        pass
        return True
    except Exception:
        _sys_log(traceback.format_exc())
        return False


def _damp_camera_impulse(cfg, cam, dt, aiming):
    global _recoil_t, _recoil_grace
    if aiming or _flag(cfg, F_AIM):
        try:
            aiming = aiming or _aim_latched or _poll_input_keystate(int(cfg[IDX_AIM_KEY]))
        except Exception:
            pass
    if not _flag(cfg, F_RECOIL) or aiming or cam is None:
        _recoil_t = 0.0
        _recoil_grace = 0.0
        return
    firing = _poll_input_keystate(0x01)
    if firing:
        _recoil_grace = 0.10
    elif _recoil_grace > 0.0:
        _recoil_grace = max(0.0, _recoil_grace - dt)
        firing = True
    else:
        _recoil_t = 0.0
        return
    strength = max(0.0, min(2.0, float(cfg[IDX_HUMANIZE])))
    if strength <= 0.0:
        return
    placer = _get_placer()
    if placer is None or not hasattr(placer, 'TurnView'):
        return
    step = dt if dt > 0.0001 else 0.0166667
    tick = step / 0.0166667
    _recoil_t += step
    pull = 0.0019 * strength * tick
    sway = math.sin(_recoil_t * 7.3) * 0.00055 * strength * tick
    try:
        placer.TurnView(sway, -pull)
    except Exception:
        pass


def _update_cam_trajectory(cfg, items, cam, origin, menu_open, dt=0.0166667):
    global _aim_prev, _aim_latched, _aim_busy, _path
    global _aim_hold_until, _aim_diag_t, _aim_fallback_n
    global _aim_eid, _aim_eid_t
    now = time.time()
    aim_key = int(cfg[IDX_AIM_KEY])
    aim_enabled = _flag(cfg, F_AIM)
    aim_down = aim_enabled and _poll_input_keystate(aim_key)
    if aim_down:
        _aim_hold_until = now + 0.30
    held = aim_down or now < _aim_hold_until
    if _get_track_mode_toggle(cfg) and aim_enabled:
        if aim_down and not _aim_prev:
            _aim_latched = not _aim_latched
        aim_on = _aim_latched
    else:
        _aim_latched = False
        aim_on = held
    if aim_down != _aim_prev:
        _sys_log('aim key %d %s held=%d %s' % (
            aim_key, 'down' if aim_down else 'up', 1 if held else 0, _key_diag(aim_key)))
    _aim_prev = aim_down
    if menu_open:
        aim_on = False
        _aim_latched = False
        _path = None
    _aim_busy = aim_on
    if cam is None or origin is None:
        _path = None
        return
    placer = _get_placer()
    cur = _cam_dir(cam) or _placer_dir(placer)
    if cur is None:
        _path = None
        return

    if not items:
        return

    if aim_on:
        if placer is None or not hasattr(placer, 'TurnView'):
            if now - _aim_diag_t >= 1.0:
                _aim_diag_t = now
                _sys_log('[cam:track] no TurnView placer=%s turn=%s' %
                     (type(placer).__name__, hasattr(placer, 'TurnView')))
            return
        bone = int(cfg[IDX_AIM_BONE])
        max_dist = float(cfg[IDX_AIM_MAX_DIST])
        best = _pick(items, origin, cur, float(cfg[IDX_AIM_FOV]), max_dist, cfg, bone, True, True)
        if best is None and _aim_eid is not None and now - _aim_eid_t < 0.60:
            best = _pick_eid(items, origin, cur, _aim_eid, max_dist, cfg, bone, True)
        if best is None:
            if now - _aim_diag_t >= 1.0:
                _aim_diag_t = now
                _sys_log('[cam:track] no target in fov items=%d fov=%.1f placer=%s %s' % (
                    len(items), float(cfg[IDX_AIM_FOV]), type(placer).__name__,
                    _key_diag(aim_key)))
            return
        e, tt, td, dist, dot = best
        try:
            _aim_eid = int(getattr(e, 'id', 0) or 0) or None
            _aim_eid_t = now
        except Exception:
            _aim_eid = None
        _aim_busy = True
        if now - _aim_diag_t >= 1.0:
            _aim_diag_t = now
            c = _vec(cur) or (0.0, 0.0, 1.0)
            t = _norm(_vec(td) or (0.0, 0.0, 1.0))
            theta = math.degrees(math.acos(max(-1.0, min(1.0, _dot(_norm(c), t)))))
            _sys_log('[cam:track] target dist=%.1f theta=%.2f fallback=%d items=%d %s' % (
                dist, theta, _aim_fallback_n, len(items), _key_diag(aim_key)))
        _apply_view_transform(placer, cur, td, float(cfg[IDX_AIM_SMOOTH]), dt)


def _current_case(entity):
    try:
        cur = _weapon_case(entity)
        if cur is not None:
            return cur
    except Exception:
        pass
    av = getattr(genv, 'avatar', None)
    if av is not None and av is not entity:
        try:
            cur = _weapon_case(av)
            if cur is not None:
                return cur
        except Exception:
            pass
    return None


def _all_cases(entity):
    cases = []
    seen = set()
    def add_case(c):
        if c is not None and id(c) not in seen:
            seen.add(id(c))
            cases.append(c)

    cur = _current_case(entity)
    add_case(cur)
    av = getattr(genv, 'avatar', None)
    for ent in (entity, av):
        if ent is None:
            continue
        hm = getattr(ent, 'hand_model', None)
        if hm is not None:
            for fn_name in ('GetCurClientWeaponCase', 'GetCurWeaponCase', 'GetWeaponCase'):
                try:
                    fn = getattr(hm, fn_name, None)
                    if callable(fn):
                        add_case(fn())
                except Exception:
                    pass
            for wd_name in ('weapon_dict', 'weapon_case_dict'):
                try:
                    wd = getattr(hm, wd_name, None)
                    if isinstance(wd, dict):
                        for c in list(wd.values()) + list(wd.keys()):
                            add_case(c)
                except Exception:
                    pass
        for m_name in ('model', 'hand_model'):
            md = getattr(ent, m_name, None)
            if md is not None:
                try:
                    wd = getattr(md, 'weapon_dict', None)
                    if isinstance(wd, dict):
                        for c in list(wd.values()) + list(wd.keys()):
                            add_case(c)
                except Exception:
                    pass
        for n in ('weapon_case_mgr', 'GetWeaponCaseMgr', 'weapon_case_dict'):
            try:
                m = getattr(ent, n, None)
            except Exception:
                continue
            if m is None:
                continue
            if callable(m):
                try:
                    m = m()
                except Exception:
                    continue
            if m is None:
                continue
            d = getattr(m, 'weapon_case_dict', None)
            if d is None and isinstance(m, dict):
                d = m
            if d:
                try:
                    for c in list(d.values()) + list(d.keys()):
                        add_case(c)
                except Exception:
                    pass
    return cases


def _find_case(entity, gid):
    if gid <= 0:
        return None
    for wc in _all_cases(entity):
        try:
            if int(getattr(wc, 'gun_id', 0) or 0) == gid:
                return wc
        except Exception:
            pass
    return None


def _call_path(obj, names, variants):
    for name in names:
        try:
            fn = getattr(obj, name, None)
        except Exception:
            continue
        if not callable(fn):
            continue
        for args in variants:
            try:
                fn(*args)
                return name
            except TypeError:
                continue
            except Exception:
                continue
    return ''


def _skin_is_temporary(proto):
    params = proto.get('use_code_params') or {}
    return bool(params.get('use_time') or proto.get('end_time') or
                proto.get('limited_item_time') or proto.get('use_code') == 'PlaceholderItem')


def _skin_entity():
    if bool(getattr(genv, 'is_in_hall', True)):
        return None
    player = getattr(genv, 'player', None)
    candidates = [player]
    if player is not None:
        candidates.append(getattr(player, 'combat_avatar', None))
    candidates.extend((_local()[0], getattr(genv, 'avatar', None)))
    for entity in candidates:
        if entity is None:
            continue
        for name in ('IsPlayerCombatAvatar', 'IsCombatAvatar'):
            value = getattr(entity, name, False)
            if callable(value):
                value = value()
            if value:
                return entity
    return None


def _skin_case_is_melee(case):
    for cls in type(case).__mro__:
        if cls.__name__ in ('MeleeCase', 'DualMeleeCase', 'HeirloomCase'):
            return True
    value = getattr(case, 'IsMelee', False)
    return bool(value() if callable(value) else value)


def _skin_case_gun_id(case):
    gid = int(getattr(case, 'gun_id', 0) or 0)
    if gid:
        return gid
    for name in ('equip_proto', 'body_equip_proto'):
        proto = getattr(case, name, None)
        if proto is not None:
            gid = int(proto.get('gun_id') or 0)
            if gid:
                return gid
    return 0


def _skin_selection(selection, typ):
    import gclient.data.lobby_item_data as lobby
    import gclient.data.gun_skin_template_data as gun
    wanted = (510, 520, 530, 540, 550, 560) if typ == 2 else (201, 202, 203, 206, 207, 210)
    item = lobby.data.get(selection)
    template_id = 0
    if item is not None:
        if int(item.get('sub_type') or 0) not in wanted:
            raise ValueError('selected item does not belong to this skin category')
        if _skin_is_temporary(item):
            raise ValueError('selected item is temporary or a placeholder')
        template_id = int((item.get('guise') or {}).get('template_id') or 0)
    else:
        template_id = int(selection)
        cached = getattr(_skin_selection, 'template_items', {})
        item = cached.get((typ, template_id))
        if item is None:
            for candidate in lobby.data.values():
                if int(candidate.get('sub_type') or 0) not in wanted or _skin_is_temporary(candidate):
                    continue
                if int((candidate.get('guise') or {}).get('template_id') or 0) != template_id:
                    continue
                if item is None or int(candidate['id']) < int(item['id']):
                    item = candidate
            if item is not None:
                cached[(typ, template_id)] = item
                _skin_selection.template_items = cached
    if item is None or not template_id:
        raise ValueError('no permanent skin item matches the selected template')
    template = gun.data.get(template_id)
    if template is None:
        raise ValueError('skin template is missing')
    if int(item.get('sub_type') or 0) == 210:
        raise ValueError('Artifact requires blade/handle/core/effect attributes; a template ID alone is insufficient')
    return item, template, template_id


def _update_model_appearance(entity, item, typ):
    try:
        selected, template, template_id = _skin_selection(int(item), int(typ))
        gid = int(template.get('gun_id') or 0)
        cases = []
        for case in _all_cases(entity):
            if not callable(getattr(case, 'ChangeWeaponGuise', None)):
                continue
            if not bool(getattr(case, 'is_in_combat', False)):
                continue
            if _skin_case_is_melee(case) != (typ == 3):
                continue
            if typ == 2 and _skin_case_gun_id(case) != gid:
                continue
            cases.append(case)
        if typ == 2 and gid <= 0:
            raise ValueError('selected gun skin has no gun_id')
        if not cases:
            raise ValueError('matching combat weapon case is not loaded; equip the selected weapon first')
        expected_equip = int(template.get('replace_equip_id') or 0)
        for case in cases:
            if typ == 3 and expected_equip and int(getattr(case, 'weapon_id', 0) or 0) != expected_equip:
                import gclient.data.equip_data as equips
                target = equips.data.get(expected_equip) or {}
                current = getattr(case, 'equip_proto', None) or {}
                if not target.get('equip_case') or target.get('equip_case') != current.get('equip_case'):
                    raise ValueError('selected melee skin requires a different weapon class; equip that melee class first')
        accepted = 0
        for case in cases:
            item_id = int(selected['id'])
            if int(getattr(case, 'guise_id', 0) or 0) != template_id:
                # Dispatch through the actual case subclass, including DualMeleeCase.
                case.ChangeWeaponGuise(template_id, guise_item_id=item_id)
            if int(getattr(case, 'guise_id', 0) or 0) != template_id:
                raise ValueError('weapon case did not accept the template (model/resources may be unavailable)')
            accepted += 1
        return 'ChangeWeaponGuise template=%d item=%d cases=%d' % (template_id, int(selected['id']), accepted)
    except Exception as error:
        _sys_log('skin request failed type=%d selection=%d: %s: %s' %
                 (typ, item, type(error).__name__, error))
        return ''



def _apply_hero(entity, item):
    import gclient.data.lobby_item_data as lobby
    import gshare.consts as consts
    try:
        proto = lobby.data.get(item)
        if proto is None or int(proto.get('sub_type') or 0) != 300 or _skin_is_temporary(proto):
            raise ValueError('not a permanent character skin item')
        current_hero = _hero_of(entity) or _local_hero_id()
        wanted_hero = int(proto.get('hero_id') or 0)
        if not wanted_hero or current_hero != wanted_hero:
            raise ValueError('skin hero=%d does not match current combat hero=%d' % (wanted_hero, current_hero))
        clothes = getattr(entity, 'arm_clothes', None)
        callback = getattr(entity, '_on_set_arm_clothes', None)
        display = getattr(entity, 'GetDisplayHeroSkinItemId', None)
        if clothes is None or not callable(callback) or not callable(display):
            raise ValueError('combat avatar clothing callback is unavailable')
        suit_key = consts.ItemSubType.Suit
        old = dict(clothes)
        if int(display() or 0) == item:
            return 'arm_clothes already selected item=%d' % item
        try:
            clothes[suit_key] = item
            if int(display() or 0) != item:
                raise ValueError('display state did not accept the selected clothing item')
            callback(old)
        except Exception:
            if suit_key in old:
                clothes[suit_key] = old[suit_key]
            else:
                clothes.pop(suit_key, None)
            raise
        return 'combat arm_clothes -> ShowModel item=%d' % item
    except Exception as error:
        _sys_log('hero skin request failed item=%d: %s: %s' % (item, type(error).__name__, error))
        return ''



def _find_doll():
    try:
        for e in getattr(genv.space, 'entities', {}).values():
            if type(e).__name__ == 'Doll':
                return e
    except Exception:
        pass
    return None


def _apply(cfg):
    global _last_apply_seq, _last_apply_try, _apply_tries, _apply_seq_seen
    seq, typ, item = int(cfg[IDX_APPLY_SEQ]), int(cfg[IDX_APPLY_TYPE]), int(cfg[IDX_APPLY_ITEM])
    if typ not in (1, 2, 3) or not item:
        return
    if int(cfg[IDX_AUTO_SKIN]):
        _last_apply_seq = seq
        return
    if seq != _apply_seq_seen:
        _apply_seq_seen, _apply_tries = seq, 0
    if seq == _last_apply_seq or time.time() - _last_apply_try < 0.25:
        return
    entity = _skin_entity()
    if entity is None:
        return
    _last_apply_try = time.time()
    try:
        via = _apply_hero(entity, item) if typ == 1 else _update_model_appearance(entity, item, typ)
        if via:
            _last_apply_seq, _apply_tries = seq, 0
            _sys_log('skin update requested type=%d item=%d via=%s' % (typ, item, via))
        else:
            _apply_tries += 1
            if _apply_tries >= 8:
                _last_apply_seq = seq
    except Exception:
        _sys_log(traceback.format_exc())



def _queue_skin(typ, item):
    if not item:
        return
    if typ == 1 and _skin_respect_current:
        try:
            import gclient.data.lobby_item_data as lobby
            want = _hero_of(lobby.data.get(item))
            cur = _local_hero_id()
            if want and cur and want != cur:
                return
        except Exception:
            pass
    key = (typ, int(item))
    if key not in _skin_task:
        _skin_task.append(key)


def _run_skin_tasks():
    global _skin_task_t
    now = time.time()
    if not _skin_task or now - _skin_task_t < 0.30:
        return
    entity = _skin_entity()
    if entity is None:
        return
    _skin_task_t = now
    typ, item = _skin_task.pop(0)
    key = (typ, item)
    try:
        via = _apply_hero(entity, item) if typ == 1 else _update_model_appearance(entity, item, typ)
        if via:
            _skin_fail.pop(key, None)
            _sys_log('skin update requested type=%d item=%d via=%s' % (typ, item, via))
        else:
            count = _skin_fail.get(key, 0) + 1
            _skin_fail[key] = count
            if count < 6:
                _skin_task.append(key)
            else:
                _sys_log('skin retries stopped type=%d item=%d; see request error above' % key)
    except Exception:
        _sys_log(traceback.format_exc())



def _skin_inventory_path():
    import os
    local = os.environ.get('LOCALAPPDATA')
    if local:
        return os.path.join(local, 'CiyE', 'BloodStrike', 'skin_inventory.bin')
    return os.path.join(IPC_DIR, 'skin_inventory.bin')


def _skin_inventory(force=False):
    import os
    now = time.time()
    cached = getattr(_skin_inventory, 'records', None)
    if not force and now < getattr(_skin_inventory, 'next_poll', 0):
        return cached
    _skin_inventory.next_poll = now + 1.0
    try:
        path = _skin_inventory_path()
        stat = os.stat(path)
        stamp = (stat.st_mtime_ns, stat.st_size)
        if stamp == getattr(_skin_inventory, 'stamp', None):
            return cached
        with open(path, 'rb') as stream:
            raw = stream.read(12 + 4096 * 64 + 1)
        if len(raw) < 12:
            raise ValueError('inventory header is incomplete')
        magic, version, count = struct.unpack_from('<III', raw)
        if magic != 0x42534956 or version != 1 or count > 4096 or len(raw) != 12 + count * 64:
            raise ValueError('inventory format or size is invalid')
        active = {}
        seen = set()
        for offset in range(12, len(raw), 64):
            typ, slot, selection, enabled, _ = struct.unpack_from('<IIII48s', raw, offset)
            if typ not in (1, 2, 3) or not slot or not selection or enabled not in (0, 1):
                raise ValueError('invalid inventory entry')
            if (typ, selection) in seen or (enabled and (typ, slot) in active):
                raise ValueError('duplicate inventory entry or active slot')
            seen.add((typ, selection))
            if enabled:
                active[(typ, slot)] = (typ, slot, selection)
        _skin_inventory.records = tuple(active.values())
        _skin_inventory.stamp = stamp
        _skin_inventory.error = None
    except FileNotFoundError:
        _skin_inventory.records = None
        _skin_inventory.stamp = None
        _skin_inventory.error = None
    except Exception as error:
        message = '%s: %s' % (type(error).__name__, error)
        if message != getattr(_skin_inventory, 'error', None):
            _sys_log('skin inventory could not be loaded: ' + message)
        _skin_inventory.error = message
        # Keep the last valid inventory; never replace a damaged file with cfg defaults.
        if cached is None:
            _skin_inventory.records = ()
    return getattr(_skin_inventory, 'records', None)


def _skin_inventory_targets(entity, records):
    import gclient.data.lobby_item_data as lobby
    import gclient.data.equip_data as equips
    hero = _hero_of(entity) or _local_hero_id()
    cases = [case for case in _all_cases(entity)
             if callable(getattr(case, 'ChangeWeaponGuise', None)) and
             bool(getattr(case, 'is_in_combat', False))]
    targets = []
    for typ, slot, selection in records:
        try:
            if typ == 1:
                proto = lobby.data.get(selection) or {}
                if (int(proto.get('sub_type') or 0) == 300 and
                        not _skin_is_temporary(proto) and
                        int(proto.get('hero_id') or 0) == hero == slot):
                    targets.append((typ, selection))
                continue
            proto, template, _ = _skin_selection(selection, typ)
            if typ == 2:
                gid = int(template.get('gun_id') or 0)
                if gid == slot and gid > 0 and any(not _skin_case_is_melee(case) and
                        _skin_case_gun_id(case) == gid for case in cases):
                    targets.append((typ, selection))
            else:
                if int(proto.get('sub_type') or 0) * 100 + 2 != slot:
                    continue
                expected = int(template.get('replace_equip_id') or 0)
                wanted_class = (equips.data.get(expected) or {}).get('equip_case')
                for case in cases:
                    if not _skin_case_is_melee(case):
                        continue
                    current = getattr(case, 'equip_proto', None) or {}
                    if not expected or expected == int(getattr(case, 'weapon_id', 0) or 0) or (
                            wanted_class and wanted_class == current.get('equip_case')):
                        # Overlapping melee categories use the most recently selected compatible skin.
                        targets = [target for target in targets if target[0] != 3]
                        targets.append((typ, selection))
                        break
        except (ValueError, TypeError, KeyError):
            # A removed/outdated catalog item must not block the other saved skins.
            continue
    return tuple(targets)


def _drive_saved_skins(cfg):
    global _skin_auto_seen, _skin_last_reapply, _skin_respect_current
    if not int(cfg[IDX_AUTO_SKIN]):
        _skin_task[:] = []
        _skin_auto_seen = None
        return
    _skin_respect_current = _flag(cfg, F_SKIN_CURRENT)
    entity = _skin_entity()
    if entity is None:
        _skin_auto_seen = None
        _skin_task[:] = []
        _skin_fail.clear()
        return
    seq = int(cfg[IDX_APPLY_SEQ])
    records = _skin_inventory(seq != getattr(_drive_saved_skins, 'inventory_seq', None))
    _drive_saved_skins.inventory_seq = seq
    if records is None:
        # Compatibility for configurations saved before Inventory existed.
        want = tuple((typ, int(cfg[index])) for typ, index in
                     ((1, IDX_SKIN_HERO), (2, IDX_SKIN_GUN), (3, IDX_SKIN_KNIFE))
                     if int(cfg[index]))
    else:
        want = _skin_inventory_targets(entity, records)
    cases = tuple((id(case), _skin_case_gun_id(case), int(getattr(case, 'weapon_id', 0) or 0),
                   bool(getattr(case, 'is_in_combat', False))) for case in _all_cases(entity))
    state = (want, seq, id(entity), id(getattr(genv, 'space', None)),
             _hero_of(entity) or _local_hero_id(), cases)
    now = time.time()
    if state != _skin_auto_seen or now - _skin_last_reapply > 20.0:
        _skin_auto_seen = state
        _skin_last_reapply = now
        _skin_fail.clear()
        _skin_task[:] = []
        for typ, item in want:
            _queue_skin(typ, item)




UNLOCK_TRUE = {
    'unlock', 'unlocked', 'is_unlock', 'is_unlocked', 'is_owned', 'owned', 'is_get',
    'is_have', 'have', 'can_use', 'usable', 'is_valid', 'is_open', 'open', 'enable',
    'enabled', 'is_enable', 'is_enabled', 'is_active', 'active', 'is_obtain', 'obtained',
    'is_received', 'received', 'is_free', 'free',
}
UNLOCK_FALSE = {
    'lock', 'locked', 'is_lock', 'is_locked', 'disable', 'disabled', 'is_disable',
    'is_disabled', 'forbid', 'forbidden', 'is_forbid', 'need_unlock',
}


def _iter_data_entries():
    for name, mod in list(sys.modules.items()):
        if not name.startswith('gclient.data'):
            continue
        try:
            data = getattr(mod, 'data', None)
        except Exception:
            continue
        if data is None:
            continue
        try:
            if hasattr(data, 'values'):
                vals = data.values()
            elif isinstance(data, (list, tuple)):
                vals = data
            else:
                continue
        except Exception:
            continue
        try:
            for v in vals:
                if hasattr(v, 'keys'):
                    yield v
        except Exception:
            pass


def _eval_cosmetic_entry(entry):
    changed = 0
    try:
        keys = list(entry.keys())
    except Exception:
        return 0
    for k in keys:
        try:
            kl = str(k).lower()
        except Exception:
            continue
        try:
            if kl in UNLOCK_TRUE:
                if not entry.get(k):
                    entry[k] = 1
                    changed += 1
            elif kl in UNLOCK_FALSE:
                if entry.get(k):
                    entry[k] = 0
                    changed += 1
        except Exception:
            pass
    return changed


def _sync_cosmetics_budget(budget):
    global _unlock_iter, _unlock_changed
    changed = 0
    if _unlock_iter is None:
        _unlock_iter = _iter_data_entries()
    t0 = time.time()
    while time.time() - t0 < budget:
        try:
            entry = next(_unlock_iter)
        except StopIteration:
            _unlock_iter = None
            _unlock_changed += changed
            return changed, True
        except Exception:
            _unlock_iter = None
            _unlock_changed += changed
            return changed, True
        changed += _eval_cosmetic_entry(entry)
    _unlock_changed += changed
    return changed, False


def _sync_cosmetics_batch():
    changed = 0
    for entry in _iter_data_entries():
        changed += _eval_cosmetic_entry(entry)
    return changed


def _bind_cosmetic_predicates():
    for name, mod in list(sys.modules.items()):
        if not (name.startswith('gclient') or name.startswith('gshare')):
            continue
        try:
            attrs = dir(mod)
        except Exception:
            continue
        for attr in attrs:
            low = attr.lower()
            if not any(x in low for x in ('unlock', 'owned', 'is_have', 'can_use', 'obtain')):
                continue
            if not (low.startswith('is') or low.startswith('has') or low.startswith('check') or low.startswith('can')):
                continue
            key = (name, attr)
            if key in _wrapped_preds:
                continue
            try:
                fn = getattr(mod, attr, None)
            except Exception:
                continue
            if not callable(fn) or not hasattr(fn, '__code__'):
                continue

            def make(orig):
                def pred(*args, **kwargs):
                    return True
                pred._m_wrapped = True
                return pred

            try:
                setattr(mod, attr, make(fn))
                _wrapped_preds.add(key)
            except Exception:
                pass


def _refresh_runtime_cosmetics():
    global _last_unlock, _unlock_done, _unlock_iter, _unlock_scan_t, _unlock_changed
    now = time.time()
    if _unlock_iter is None:
        if now - _last_unlock < 120.0:
            return
        _last_unlock = now
        _unlock_scan_t = now
        _unlock_changed = 0
        _unlock_iter = _iter_data_entries()
    try:
        changed, done = _sync_cosmetics_budget(0.003)
        if done:
            if not _unlock_done:
                _bind_cosmetic_predicates()
                _unlock_done = True
            _sys_log('unlock pass done changed=%d preds=%d took=%.2fs' % (
                _unlock_changed, len(_wrapped_preds), time.time() - _unlock_scan_t))
    except Exception:
        _unlock_iter = None
        _sys_log(traceback.format_exc())


def _serialize_frame_data(cfg, cam, in_match, origin, lpos, items):
    global _state_seq
    fwd = (0.0, 0.0, -1.0)
    yaw = 0.0
    pitch = 0.0
    fov = 0.0
    if cam is not None:
        fwd = _vec(getattr(getattr(cam, 'Transform', None), 'z_axis', None)) or fwd
        try:
            cam2 = getattr(genv, 'camera', None)
            placer = getattr(cam2, 'placer', None)
            direc = getattr(placer, 'Direction', None)
            if direc is not None:
                yaw = float(getattr(direc, 'yaw', 0.0))
                pitch = float(getattr(direc, 'pitch', 0.0))
        except Exception:
            pass
        try:
            fov = float(getattr(cam, 'FieldOfView', 0.0) or 0.0)
        except Exception:
            pass
    sw, sh = 0.0, 0.0
    try:
        sz = gui.cocos_screen_size
        sw, sh = float(sz[0]), float(sz[1])
    except Exception:
        try:
            if MUI is not None:
                sz = MUI.GetScreenSize()
                sw, sh = float(sz[0]), float(sz[1])
        except Exception:
            pass
    _state_seq = (_state_seq + 1) & 0xFFFFFFFF
    try:
        lhid = int(_local_hero_id()) & 0xFFFF
    except Exception:
        lhid = 0
    buf = bytearray(STATE_SIZE)
    struct.pack_into(STATE_FMT, buf, 0, STATE_MAGIC, VERSION, _state_seq, 0,
                     int(time.time() * 1000) & 0xFFFFFFFFFFFFFFFF,
                     sw, sh,
                     *(lpos or (0.0, 0.0, 0.0)),
                     *(origin if origin is not None else (0.0, 0.0, 0.0)),
                     *fwd, yaw, pitch, fov,
                     1 if in_match else 0, 1 if origin is not None else 0, lhid)
    off = STATE_HEAD_SIZE
    n = 0
    if in_match and items:
        do_vis = _flag(cfg, F_ESP_VISIBLE) or _flag(cfg, F_AIM_VISIBLE)
        vis_budget = 64
        max_dist = float(cfg[IDX_ESP_MAX_DIST])
        for item in items:
            dist, e, eid, ht, feet, ph, pf, ps, pn, gun, eteam, is_team = item
            if dist > max_dist:
                continue
            if is_team and not _flag(cfg, F_ESP_TEAM):
                continue
            vis = 1
            if do_vis:
                fresh = _query_occlusion_cache(e, 0.12)
                if fresh is not None:
                    vis = 1 if fresh else 0
                elif vis_budget > 0:
                    vis_budget -= 1
                    vis = 1 if _line_of_sight_query(e, ht, dist, max_dist) else 0
                else:
                    stale = _query_occlusion_cache(e)
                    if stale is not None:
                        vis = 1 if stale else 0
            eid_i = _id_u64(eid)
            try:
                team_i = int(eteam or 0)
            except Exception:
                team_i = 0
            try:
                bones_data = ps if (ps and len(ps) == 32) else ([-1.0] * 32)
                struct.pack_into(ENT_FMT, buf, off,
                                 eid_i, _bytes(_ename(e), 40), _bytes(gun, 32),
                                 ht[0], ht[1], ht[2], feet[0], feet[1], feet[2],
                                 ph[0], ph[1], pf[0], pf[1],
                                 float(dist), _hp(e), _max_hp(e), team_i,
                                 vis, 1 if is_team else 0, 1 if getattr(e, 'IsMonster', False) else 0, 1,
                                 0,
                                 *bones_data)
            except Exception:
                continue
            off += ENT_SIZE
            n += 1
            if n >= MAX_ENTITIES:
                break
    struct.pack_into('<I', buf, 12, n)
    return buf[:STATE_HEAD_SIZE + n * ENT_SIZE]


def _on_story_tick(dt):
    global _last_state, _fire_release_at, _last_catalog_check, _aim_busy
    global _last_gather, _gather_cache, _last_hooks, _last_scrub, _diag_t
    global _perf_t, _perf_last
    if int(getattr(builtins, '_m_generation', 0) or 0) != _my_gen:
        return
    try:
        t0 = time.time()
        cfg = _read_cfg()
        if cfg[IDX_MAGIC] != CFG_MAGIC:
            cfg = DEFAULT_CFG
        now = t0
        if dt > 0.4 and now - _perf_t >= 1.0:
            _perf_t = now
            _sys_log('perf stutter dtime=%.3f' % (dt,))
        if now - _last_hooks >= 2.0:
            _last_hooks = now
            _install_instance_hooks()
        if now - _last_scrub >= 60.0:
            _last_scrub = now
            _scrub_disk_markers()
        if now - _last_catalog_check >= 5.0:
            _last_catalog_check = now
            _save_template_cache()
        if _fire_release_at and now >= _fire_release_at:
            _trigger_primary_input(False)
            _mouse(False)
            _fire_release_at = 0.0
        menu_open = _flag(cfg, F_MENU_OPEN)
        in_match = not bool(getattr(genv, 'is_in_hall', True))
        _apply(cfg)
        _drive_saved_skins(cfg)
        _run_skin_tasks()
        t_apply = time.time()
        if _flag(cfg, F_UNLOCK_EFFECTS):
            _refresh_runtime_cosmetics()
        t_unlock = time.time()
        cam = None
        origin = None
        items = []
        aim_active = _flag(cfg, F_AIM)
        esp_on = _flag(cfg, F_ESP)
        if in_match and (aim_active or esp_on):
            scan = max(float(cfg[IDX_ESP_MAX_DIST]), float(cfg[IDX_AIM_MAX_DIST]))
            interval = 0.0
            want_gun = esp_on and _flag(cfg, F_ESP_GUN)
            want_bone = esp_on and _flag(cfg, F_ESP_SKELETON)
            if now - _last_gather >= interval or _gather_cache[1] is None:
                cam, origin, items = _query_visible_entities(scan, want_gun, want_bone)
                _gather_cache = (now, cam, origin, items)
                _last_gather = now
            else:
                _, cam, origin, items = _gather_cache
            if esp_on and now - _diag_t >= 5.0:
                _diag_t = now
                try:
                    total = len(_collect_space_entities(getattr(genv, 'space', None)))
                except Exception:
                    total = -1
                try:
                    cats = getattr(getattr(genv, 'space', None), 'entity_category', None) or {}
                    brief = ','.join('%s=%d' % (k, len(v)) for k, v in list(cats.items())[:12])
                except Exception:
                    brief = ''
                _sys_log('diag match=%s hall=%s ents=%d items=%d aim=%d esp=%d cats[%s]' %
                     (in_match, getattr(genv, 'is_in_hall', None), total, len(items),
                      1 if aim_active else 0, 1 if esp_on else 0, brief))
                for it in items[:4]:
                    try:
                        _sys_log('diag ent type=%s id=%s dist=%.1f team=%s is_team=%s scr=(%.3f,%.3f)' %
                             (type(it[1]).__name__, it[2], it[0], it[10], it[11],
                              it[5][0], it[5][1]))
                    except Exception:
                        pass
        else:
            try:
                cam = _get_cam()
                origin = _vec(cam.GetOrigin()) if cam is not None else None
            except Exception:
                cam = None
                origin = None
            _gather_cache = (now, cam, origin, [])
        if items and aim_active:
            t_gather = time.time()
            _update_cam_trajectory(cfg, items, cam, origin, menu_open, dt)
        else:
            t_gather = time.time()
            _aim_busy = False
        t_aim = time.time()
        if in_match and cam is not None:
            _damp_camera_impulse(cfg, cam, dt, _aim_busy)
        _last_state = now
        av, lid, team, lpos = _local()
        buf = _serialize_frame_data(cfg, cam, in_match, origin, lpos, items)
        if buf is not None:
            _write(STATE_PATH, buf)
        t1 = time.time()
        total = t1 - t0
        if (total > 0.06 or t_aim - t_apply > 0.04) and t0 - _perf_last >= 1.0:
            _perf_last = t0
            _sys_log('[sys:perf] dt=%.3f total=%.3f apply=%.4f unlock=%.4f gather=%.4f aim=%.4f state=%.4f items=%d' % (
                dt, total, t_apply - t0, t_unlock - t_apply, t_gather - t_unlock,
                t_aim - t_gather, t1 - t_aim, len(items)))
    except Exception:
        _sys_log(traceback.format_exc())


_on_story_tick.__name__ = 'OnEngineViewportUpdate'
_on_story_tick.__qualname__ = 'OnEngineViewportUpdate'


def start():
    global _last_apply_seq, _booted, _my_gen
    _my_gen = int(getattr(builtins, '_m_generation', 0) or 0)
    if _booted:
        return True
    os.makedirs(IPC_DIR, exist_ok=True)
    _make_cfg_default()
    _save_template_cache()
    _install_hooks()
    try:
        import gclient.framework.util.story_tick as st
        def OnEngineViewportUpdate(dt):
            return _on_story_tick(dt)
        OnEngineViewportUpdate.__name__ = 'OnEngineViewportUpdate'
        OnEngineViewportUpdate.__qualname__ = 'OnEngineViewportUpdate'
        st.StoryTick().Add(OnEngineViewportUpdate, 0)
    except Exception:
        _sys_log(traceback.format_exc())
        return False
    _booted = True
    _last_apply_seq = -1
    try:
        cfg = _read_cfg()
        cam, origin, items = _query_visible_entities(float(cfg[IDX_ESP_MAX_DIST]))
        av, lid, team, lpos = _local()
        _write(STATE_PATH, _serialize_frame_data(cfg, cam, not bool(getattr(genv, 'is_in_hall', True)), origin, lpos, items))
    except Exception:
        _sys_log(traceback.format_exc())
    return True


def status():
    cfg = _read_cfg()
    try:
        catsize = os.path.getsize(CATALOG_PATH)
    except Exception:
        catsize = 0
    try:
        statesize = os.path.getsize(STATE_PATH)
    except Exception:
        statesize = 0
    try:
        head = _read(CATALOG_PATH, CAT_HEAD_SIZE)
        hc, gc = struct.unpack(CAT_HEAD_FMT, head)[2:4] if head and len(head) == CAT_HEAD_SIZE else (0, 0)
    except Exception:
        hc, gc = 0, 0
    return {
        'cfg_magic': hex(cfg[IDX_MAGIC]),
        'flags': hex(int(cfg[IDX_FLAGS])),
        'esp': _flag(cfg, F_ESP),
        'aim': _flag(cfg, F_AIM),
        'flick': False,
        'menu': _flag(cfg, F_MENU_OPEN),
        'catalog': catsize,
        'heroes': hc,
        'guns': gc,
        'knife_gids': sum(1 for k, v in _melee_cache.items() if v),
        'state': statesize,
        'in_hall': bool(getattr(genv, 'is_in_hall', True)),
        'hooks': _hooks_done,
        'hero_id': _local_hero_id(),
        'unlock': _flag(cfg, F_UNLOCK_EFFECTS),
        'block_report': _flag(cfg, F_BLOCK_REPORT),
    }


def rebuild_catalog():
    _save_template_cache(True)
    return True
