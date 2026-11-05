"""Offline tests: compile only skin functions, never import or start the game runtime."""
import ast, os, struct, sys, time, traceback, types, unittest, tempfile
from pathlib import Path
from unittest.mock import patch

REPLACEMENTS = {'_skin_is_temporary', '_skin_entity', '_skin_case_is_melee', '_skin_case_gun_id',
                 '_skin_selection', '_update_model_appearance', '_apply_hero', '_index_item_templates',
                 '_save_template_cache', '_apply', '_run_skin_tasks', '_drive_saved_skins',
                 '_skin_inventory_path', '_skin_inventory', '_skin_inventory_targets'}

class WeaponCase:
    def __init__(self, gid=1, accepts=True):
        self.gun_id, self.guise_id, self.is_in_combat = gid, 0, True
        self.calls, self.accepts = [], accepts
    def ChangeWeaponGuise(self, tid, guise_item_id=None):
        self.calls.append((tid, guise_item_id))
        if self.accepts: self.guise_id = tid
    def ChangeWeaponSkin(self, *args):
        raise AssertionError('model skins must not be routed to the camo method')

class MeleeCase(WeaponCase):
    def __init__(self):
        super().__init__(0); self.weapon_id = 33; self.equip_proto = {'equip_case': 'Melee'}

class DualMeleeCase(MeleeCase):
    pass

class SkinFlowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        env_patch = patch.dict(os.environ, {'LOCALAPPDATA': self.directory.name})
        env_patch.start(); self.addCleanup(env_patch.stop)
        source = Path(os.environ.get('SKIN_RUNTIME_SOURCE', str(Path(__file__).resolve().parents[1] / 'pyexec/bs_runtime.py')))
        tree = ast.parse(source.read_text(encoding='utf-8-sig'))
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in REPLACEMENTS]
        self.assertEqual({n.name for n in nodes}, REPLACEMENTS)
        self.logs = []
        self.entity = types.SimpleNamespace(IsCombatAvatar=True, hero_id=113, arm_clothes={300: 3000000020}, cases=[])
        self.entity.GetDisplayHeroSkinItemId = lambda: self.entity.arm_clothes.get(300)
        self.entity._on_set_arm_clothes = lambda old: self.logs.append(('reload', old.copy()))
        self.genv = types.SimpleNamespace(player=self.entity, avatar=types.SimpleNamespace(), is_in_hall=False)
        self.ns = {'genv': self.genv, 'time': time, 'struct': struct, 'traceback': traceback,
                   '_sys_log': self.logs.append, '_local': lambda: (None, None, None, None),
                   '_all_cases': lambda ent: ent.cases, '_current_case': lambda ent: ent.cases[0] if ent.cases else None,
                   '_hero_of': lambda ent: int(getattr(ent, 'hero_id', 0) or 0), '_local_hero_id': lambda: 113,
                   '_model_to_hero': {}, '_pack_tag': lambda _: 0,
                   '_bytes': lambda text, size: text.encode('utf-8')[:size].ljust(size, b'\0'),
                   'HERO_NAMES': {113: 'ZERO'}, 'MAX_HERO': 4096, 'MAX_GUN': 65536,
                   'CAT_HEAD_FMT': '<IIII', 'CAT_ENTRY_FMT': '<IIII48s', 'CAT_HEAD_SIZE': 16,
                   'CAT_ENTRY_SIZE': 64, 'CATALOG_MAGIC': 0x42534354, 'VERSION': 6,
                   'CATALOG_PATH': 'unused', 'IPC_DIR': self.directory.name, '_write': lambda *args: None,
                   '_skin_task': [], '_skin_fail': {}, '_skin_task_t': 0., '_skin_auto_seen': None,
                   '_skin_last_reapply': 0., '_skin_respect_current': False,
                   '_last_apply_seq': -1, '_last_apply_try': 0., '_apply_tries': 0, '_apply_seq_seen': -1,
                   'IDX_APPLY_SEQ': 0, 'IDX_APPLY_TYPE': 1, 'IDX_APPLY_ITEM': 2, 'IDX_AUTO_SKIN': 3,
                   'IDX_SKIN_HERO': 4, 'IDX_SKIN_GUN': 5, 'IDX_SKIN_KNIFE': 6,
                   'F_SKIN_CURRENT': 1, '_flag': lambda cfg, flag: False}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), self.ns)
        self.ns['_queue_skin'] = lambda typ, item: self.ns['_skin_task'].append((typ, item)) if item else None
        self.items = {
            510010010: {'id': 510010010, 'name': 'M4A1 - Lava', 'quality': 4, 'sub_type': 510, 'guise': {'template_id': 11199001}},
            2010000240: {'id': 2010000240, 'name': 'Talon Knife - Scythe', 'quality': 5, 'sub_type': 201, 'guise': {'template_id': 11000008}},
            3001130002: {'id': 3001130002, 'name': 'ZERO - Scarlet', 'quality': 3, 'sub_type': 300, 'hero_id': 113, 'hero_skin_id': 3, 'model_id': 1}}
        self.templates = {11199001: {'id': 11199001, 'gun_id': 1, 'gun_skin_type': 1},
                          11000008: {'id': 11000008, 'replace_equip_id': 99, 'gun_skin_type': 1}}
        self.equips = {99: {'equip_case': 'Melee'}}
        modules = {}
        for name in ['gclient', 'gclient.data', 'gshare']:
            modules[name] = types.ModuleType(name); modules[name].__path__ = []
        for name, data in [('gclient.data.lobby_item_data', self.items), ('gclient.data.gun_skin_template_data', self.templates), ('gclient.data.equip_data', self.equips)]:
            module = types.ModuleType(name); module.data = data; modules[name] = module
        consts = types.ModuleType('gshare.consts'); consts.ItemSubType = types.SimpleNamespace(Suit=300); modules[consts.__name__] = consts
        self.module_patch = patch.dict(sys.modules, modules); self.module_patch.start(); self.addCleanup(self.module_patch.stop)
    def call(self, name, *args): return self.ns[name](*args)
    def test_resolves_item_to_template(self):
        row, _, tid = self.call('_skin_selection', 510010010, 2)
        self.assertEqual((row['id'], tid), (510010010, 11199001))
    def test_accepts_legacy_template_selection(self):
        self.assertEqual(self.call('_skin_selection', 11199001, 2)[0]['id'], 510010010)
    def test_rejects_gun_as_knife(self):
        with self.assertRaises(ValueError): self.call('_skin_selection', 11199001, 3)
    def test_rejects_trial_items(self):
        self.items[9] = {**self.items[510010010], 'id': 9, 'use_code_params': {'use_time': 3600}}
        with self.assertRaises(ValueError): self.call('_skin_selection', 9, 2)
    def test_uses_matching_gun_and_all_views(self):
        right, wrong, third = WeaponCase(1), WeaponCase(10), WeaponCase(1)
        self.entity.cases = [17, wrong, right, third]
        self.assertTrue(self.call('_update_model_appearance', self.entity, 11199001, 2))
        self.assertEqual(right.calls, [(11199001, 510010010)]); self.assertEqual(third.calls, right.calls); self.assertFalse(wrong.calls)
    def test_does_not_claim_success_on_rejected_change(self):
        self.entity.cases = [WeaponCase(1, False)]
        self.assertEqual(self.call('_update_model_appearance', self.entity, 11199001, 2), '')
        self.assertTrue(any('did not accept' in str(x) for x in self.logs))
    def test_skips_showroom_cases(self):
        case = WeaponCase(); case.is_in_combat = False; self.entity.cases = [case]
        self.assertEqual(self.call('_update_model_appearance', self.entity, 11199001, 2), ''); self.assertFalse(case.calls)
    def test_dispatches_dual_melee_override(self):
        case = DualMeleeCase(); self.entity.cases = [case]
        self.assertTrue(self.call('_update_model_appearance', self.entity, 2010000240, 3))
        self.assertEqual(case.calls, [(11000008, 2010000240)])
    def test_rejects_wrong_melee_class(self):
        self.equips[99]['equip_case'] = 'DualMelee'; self.entity.cases = [MeleeCase()]
        self.assertEqual(self.call('_update_model_appearance', self.entity, 2010000240, 3), '')
        self.assertFalse(self.entity.cases[0].calls)
    def test_hero_changes_clothes_and_uses_callback(self):
        self.assertTrue(self.call('_apply_hero', self.entity, 3001130002))
        self.assertEqual(self.entity.arm_clothes[300], 3001130002)
        self.assertIn(('reload', {300: 3000000020}), self.logs)
    def test_hero_failure_restores_clothes(self):
        def fail(old): raise RuntimeError('resources unavailable')
        self.entity._on_set_arm_clothes = fail
        self.assertEqual(self.call('_apply_hero', self.entity, 3001130002), '')
        self.assertEqual(self.entity.arm_clothes, {300: 3000000020})
    def test_wrong_hero_is_rejected(self):
        self.entity.hero_id = 101
        self.assertEqual(self.call('_apply_hero', self.entity, 3001130002), '')
        self.assertEqual(self.entity.arm_clothes, {300: 3000000020})
    def test_prefers_actual_combat_player(self):
        self.assertIs(self.call('_skin_entity'), self.entity)
        self.genv.is_in_hall = True; self.assertIsNone(self.call('_skin_entity'))
    def test_catalog_uses_real_items_and_omits_low_tiers(self):
        self.items[10] = {**self.items[510010010], 'id': 10, 'quality': 3}
        self.items[11] = {**self.items[510010010], 'id': 11, 'sub_type': 110, 'quality': 4}
        buf = self.call('_index_item_templates'); magic, version, heroes, guns = struct.unpack_from('<IIII', buf)
        self.assertEqual((heroes, guns), (1, 2)); self.assertEqual(len(buf), 16 + 3 * 64)
        entries = [struct.unpack_from('<IIII48s', buf, 16 + (heroes+i)*64) for i in range(guns)]
        self.assertEqual({row[0] for row in entries}, {11199001, 11000008})
        self.assertEqual({row[3] for row in entries}, {1, 2})
        self.assertEqual({row[2] for row in entries}, {4, 5})
    def catalog_guns(self):
        buf = self.call('_index_item_templates')
        _, _, heroes, guns = struct.unpack_from('<IIII', buf)
        return [struct.unpack_from('<IIII48s', buf, 16 + (heroes+i)*64) for i in range(guns)]

    def install_upgrade_fixture(self):
        module = types.ModuleType('gclient.data.lobby_item_upgrade_data')
        module.data = {510010010: {}}
        sys.modules[module.__name__] = module
        for level in (5, 1, 3, 2, 4):
            iid, tid = 510010010 + level, 11199000 + level
            self.items[iid] = {**self.items[510010010], 'id': iid, 'guise': {'template_id': tid}}
            self.templates[tid] = {'id': tid, 'gun_id': 1}
            module.data[510010010][level] = {'item_id': iid}
        module.data[510010010][0] = {'item_id': 510010010}

    def test_catalog_keeps_only_highest_gun_level_and_resolves_saved_lower_level(self):
        self.install_upgrade_fixture()
        rows = [r for r in self.catalog_guns() if r[3] == 1]
        self.assertEqual([r[0] for r in rows], [11199005])
        self.assertIn(b'[Lv 5]', rows[0][4])
        self.assertEqual(self.call('_skin_selection', 11199002, 2)[0]['id'], 510010012)

    def test_catalog_resolves_highest_level_when_levels_share_a_template(self):
        self.install_upgrade_fixture()
        for level in range(1, 6):
            self.items[510010010 + level]['guise'] = {'template_id': 11199001}
        rows = [r for r in self.catalog_guns() if r[3] == 1]
        self.assertEqual(len(rows), 1)
        self.assertIn(b'[Lv 5]', rows[0][4])
        self.assertEqual(self.call('_skin_selection', 11199001, 2)[0]['id'], 510010015)

    def test_catalog_keeps_distinct_gun_skin_with_same_name(self):
        self.install_upgrade_fixture()
        self.items[510020010] = {**self.items[510010010], 'id': 510020010, 'guise': {'template_id': 11299001}}
        self.templates[11299001] = {'id': 11299001, 'gun_id': 1}
        self.assertEqual({r[0] for r in self.catalog_guns() if r[3] == 1}, {11199005, 11299001})

    def test_catalog_uses_highest_valid_permanent_level(self):
        self.install_upgrade_fixture()
        self.items[510010015]['use_code_params'] = {'use_time': 3600}
        self.assertEqual([r[0] for r in self.catalog_guns() if r[3] == 1], [11199004])

    def test_catalog_includes_four_artifacts_without_generic_weapon_templates(self):
        for iid, tid, name in [(2000000030, 91000003, 'Fireborn'), (2000000020, 91000002, 'Nexus'),
                               (2000000010, 91000001, 'Pivot'), (2000000050, 91000004, 'RAZE')]:
            self.items[iid] = {'id': iid, 'name': name, 'quality': 7, 'sub_type': 210,
                               'guise': {'template_id': tid}}
        rows = [r for r in self.catalog_guns() if r[1] == 21002]
        self.assertEqual({r[0] for r in rows}, {91000001, 91000002, 91000003, 91000004})
        self.assertTrue(all(r[3] == 2 for r in rows))

    def test_catalog_skips_negative_character_selector(self):
        self.items[12] = {**self.items[3001130002], 'id': 12, 'hero_skin_id': -1}
        buf = self.call('_index_item_templates')
        self.assertEqual(struct.unpack_from('<IIII', buf)[2], 1)
    def test_catalog_skips_template_outside_wire_range(self):
        tid = 1 << 40
        self.items[13] = {**self.items[510010010], 'id': 13, 'guise': {'template_id': tid}}
        self.templates[tid] = {'id': tid, 'gun_id': 1}
        buf = self.call('_index_item_templates')
        self.assertEqual(struct.unpack_from('<IIII', buf)[3], 2)
    def test_auto_off_clears_pending_work(self):
        self.ns['_skin_task'] = [(1, 3001130002)]
        self.call('_drive_saved_skins', [0, 0, 0, 0, 0, 0, 0]); self.assertEqual(self.ns['_skin_task'], [])
    def test_manual_uses_real_player(self):
        self.entity.cases = [WeaponCase()]
        self.call('_apply', [1, 2, 11199001, 0, 0, 0, 0])
        self.assertEqual(self.ns['_last_apply_seq'], 1)
    def test_auto_requeues_when_weapon_case_changes(self):
        self.entity.cases = [WeaponCase()]
        cfg = [1, 2, 11199001, 1, 0, 11199001, 0]
        self.call('_drive_saved_skins', cfg); self.ns['_skin_task'].clear()
        self.call('_drive_saved_skins', cfg); self.assertEqual(self.ns['_skin_task'], [])
        self.entity.cases = [WeaponCase()]; self.call('_drive_saved_skins', cfg)
        self.assertEqual(self.ns['_skin_task'], [(2, 11199001)])
    def test_catalog_cache_rebuilt_once(self):
        writes=[]; self.ns['_write']=lambda *args: writes.append(args)
        self.call('_save_template_cache'); self.call('_save_template_cache'); self.assertEqual(len(writes),1)
        self.call('_save_template_cache',True); self.assertEqual(len(writes),2)

    def write_inventory(self, entries):
        path = Path(self.call('_skin_inventory_path'))
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = struct.pack('<III', 0x42534956, 1, len(entries))
        for typ, slot, selection, enabled in entries:
            raw += struct.pack('<IIII48s', typ, slot, selection, enabled, b'Saved skin')
        path.write_bytes(raw)
        return path

    def test_inventory_uses_stable_user_directory(self):
        expected = Path(self.directory.name) / 'CiyE/BloodStrike/skin_inventory.bin'
        self.assertEqual(Path(self.call('_skin_inventory_path')), expected)
        with patch.dict(os.environ):
            os.environ.pop('LOCALAPPDATA')
            self.assertEqual(Path(self.call('_skin_inventory_path')), Path(self.directory.name) / 'skin_inventory.bin')

    def test_inventory_loads_active_entries_and_keeps_history_in_file(self):
        path = self.write_inventory([(2, 1, 11199001, 1), (2, 1, 11199002, 0), (1, 113, 3001130002, 1)])
        self.assertEqual(self.call('_skin_inventory', True), ((2, 1, 11199001), (1, 113, 3001130002)))
        self.assertEqual(path.stat().st_size, 12 + 3 * 64)

    def test_inventory_persists_across_reader_restart(self):
        self.write_inventory([(3, 20102, 11000008, 1)])
        first = self.call('_skin_inventory', True)
        self.ns['_skin_inventory'].__dict__.clear()
        self.assertEqual(self.call('_skin_inventory', True), first)

    def test_inventory_rejects_two_active_skins_for_one_slot(self):
        self.write_inventory([(2, 1, 11199001, 1), (2, 1, 11199002, 1)])
        self.assertEqual(self.call('_skin_inventory', True), ())
        self.assertTrue(any('duplicate' in log for log in self.logs))

    def test_inventory_rejects_duplicate_history_selection(self):
        self.write_inventory([(2, 1, 11199001, 0), (2, 1, 11199001, 0)])
        self.assertEqual(self.call('_skin_inventory', True), ())

    def test_inventory_corruption_retains_last_valid_data_without_writing(self):
        path = self.write_inventory([(2, 1, 11199001, 1)])
        expected = self.call('_skin_inventory', True)
        path.write_bytes(b'broken')
        self.assertEqual(self.call('_skin_inventory', True), expected)
        self.assertEqual(path.read_bytes(), b'broken')

    def test_empty_inventory_does_not_resurrect_legacy_cfg(self):
        self.write_inventory([])
        self.entity.cases = [WeaponCase()]
        self.call('_drive_saved_skins', [1, 2, 11199001, 1, 3001130002, 11199001, 11000008])
        self.assertEqual(self.ns['_skin_task'], [])

    def test_inventory_invalid_file_does_not_fall_back_to_cfg(self):
        path = self.write_inventory([]); path.write_bytes(b'broken')
        self.entity.cases = [WeaponCase()]
        self.call('_drive_saved_skins', [1, 2, 11199001, 1, 0, 11199001, 0])
        self.assertEqual(self.ns['_skin_task'], [])

    def test_inventory_filters_unloaded_weapons_and_wrong_hero(self):
        self.entity.cases = [WeaponCase(1)]
        records = ((2, 1, 11199001), (1, 101, 3001130002), (3, 20102, 11000008))
        self.assertEqual(self.call('_skin_inventory_targets', self.entity, records), ((2, 11199001),))

    def test_inventory_targets_loaded_melee_class_and_current_character(self):
        self.entity.cases = [DualMeleeCase()]
        records = ((1, 113, 3001130002), (3, 20102, 11000008))
        self.assertEqual(self.call('_skin_inventory_targets', self.entity, records),
                         ((1, 3001130002), (3, 11000008)))
        self.equips[99]['equip_case'] = 'OtherClass'
        self.assertEqual(self.call('_skin_inventory_targets', self.entity, records), ((1, 3001130002),))

    def test_inventory_rejects_mismatched_saved_group(self):
        self.entity.cases = [WeaponCase(), MeleeCase()]
        records = ((2, 99, 11199001), (3, 20202, 11000008))
        self.assertEqual(self.call('_skin_inventory_targets', self.entity, records), ())

    def test_inventory_ignores_outdated_selection_without_blocking_valid_one(self):
        self.entity.cases = [WeaponCase()]
        self.assertEqual(self.call('_skin_inventory_targets', self.entity,
            ((2, 1, 123), (2, 1, 11199001))), ((2, 11199001),))

    def test_inventory_requeues_after_match_hall_training_transitions(self):
        self.write_inventory([(2, 1, 11199001, 1)])
        self.entity.cases = [WeaponCase()]
        cfg = [1, 2, 11199001, 1, 0, 0, 0]
        self.call('_drive_saved_skins', cfg)
        self.assertEqual(self.ns['_skin_task'], [(2, 11199001)])
        self.genv.is_in_hall = True
        self.call('_drive_saved_skins', cfg)
        self.assertEqual(self.ns['_skin_task'], [])
        self.genv.is_in_hall = False
        self.call('_drive_saved_skins', cfg)
        self.assertEqual(self.ns['_skin_task'], [(2, 11199001)])

    def test_inventory_waits_for_equipment_then_requeues_on_second_view_load(self):
        self.write_inventory([(2, 1, 11199001, 1)])
        cfg = [1, 2, 11199001, 1, 0, 0, 0]
        self.call('_drive_saved_skins', cfg)
        self.assertEqual(self.ns['_skin_task'], [])
        first = WeaponCase(); self.entity.cases = [first]
        self.call('_drive_saved_skins', cfg)
        self.assertEqual(self.ns['_skin_task'], [(2, 11199001)])
        self.ns['_skin_task'].clear()
        self.entity.cases.append(WeaponCase())
        self.call('_drive_saved_skins', cfg)
        self.assertEqual(self.ns['_skin_task'], [(2, 11199001)])

    def test_inventory_auto_off_on_requeues_immediately(self):
        self.write_inventory([(2, 1, 11199001, 1)])
        self.entity.cases = [WeaponCase()]
        cfg = [1, 2, 11199001, 1, 0, 0, 0]
        self.call('_drive_saved_skins', cfg)
        cfg[3] = 0; self.call('_drive_saved_skins', cfg)
        self.assertEqual(self.ns['_skin_task'], [])
        cfg[3] = 1; self.call('_drive_saved_skins', cfg)
        self.assertEqual(self.ns['_skin_task'], [(2, 11199001)])

    def test_inventory_apply_event_refreshes_file_without_waiting_for_poll(self):
        self.write_inventory([])
        self.entity.cases = [WeaponCase()]
        cfg = [1, 2, 11199001, 1, 0, 0, 0]
        self.call('_drive_saved_skins', cfg)
        self.write_inventory([(2, 1, 11199001, 1)])
        cfg[0] = 2
        self.call('_drive_saved_skins', cfg)
        self.assertEqual(self.ns['_skin_task'], [(2, 11199001)])

    def test_inventory_reapplies_for_new_space_with_reused_avatar(self):
        self.write_inventory([(2, 1, 11199001, 1)])
        self.entity.cases = [WeaponCase()]
        cfg = [1, 2, 11199001, 1, 0, 0, 0]
        self.call('_drive_saved_skins', cfg); self.ns['_skin_task'].clear()
        self.genv.space = object()
        self.call('_drive_saved_skins', cfg)
        self.assertEqual(self.ns['_skin_task'], [(2, 11199001)])

    def test_inventory_restores_multiple_guns_and_character_through_queue(self):
        self.items[510100010] = {**self.items[510010010], 'id': 510100010,
            'guise': {'template_id': 12199001}}
        self.templates[12199001] = {'id': 12199001, 'gun_id': 10, 'gun_skin_type': 1}
        self.write_inventory([(1, 113, 3001130002, 1), (2, 1, 11199001, 1), (2, 10, 12199001, 1)])
        first, second = WeaponCase(1), WeaponCase(10)
        self.entity.cases = [first, second]
        self.call('_drive_saved_skins', [1, 2, 11199001, 1, 0, 0, 0])
        self.assertEqual(len(self.ns['_skin_task']), 3)
        for _ in range(3):
            self.ns['_skin_task_t'] = 0
            self.call('_run_skin_tasks')
        self.assertEqual(self.entity.arm_clothes[300], 3001130002)
        self.assertEqual(first.calls, [(11199001, 510010010)])
        self.assertEqual(second.calls, [(12199001, 510100010)])
        self.assertEqual(self.ns['_skin_task'], [])

    def test_inventory_rejects_unsupported_version_trailing_bytes_and_invalid_values(self):
        path = self.write_inventory([])
        for raw in [struct.pack('<III', 0x42534956, 2, 0),
                    struct.pack('<III', 0x42534956, 1, 4097),
                    struct.pack('<III', 0x42534956, 1, 0) + b'extra']:
            with self.subTest(raw=raw):
                path.write_bytes(raw)
                self.ns['_skin_inventory'].__dict__.clear()
                self.assertEqual(self.call('_skin_inventory', True), ())
        for entry in [(4, 1, 1, 1), (2, 0, 1, 1), (2, 1, 0, 1), (2, 1, 1, 2)]:
            with self.subTest(entry=entry):
                self.write_inventory([entry])
                self.ns['_skin_inventory'].__dict__.clear()
                self.assertEqual(self.call('_skin_inventory', True), ())

    def test_inventory_overlapping_knife_categories_use_latest_compatible_selection(self):
        self.items[2020000240] = {**self.items[2010000240], 'id': 2020000240,
            'sub_type': 202, 'guise': {'template_id': 11000009}}
        self.templates[11000009] = {'id': 11000009, 'replace_equip_id': 99, 'gun_skin_type': 1}
        self.entity.cases = [MeleeCase()]
        older = (3, 20102, 11000008)
        newer = (3, 20202, 11000009)
        self.assertEqual(self.call('_skin_inventory_targets', self.entity, (older, newer)), ((3, 11000009),))
        self.assertEqual(self.call('_skin_inventory_targets', self.entity, (newer, older)), ((3, 11000008),))

if __name__ == '__main__': unittest.main()
