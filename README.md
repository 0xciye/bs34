# bs34

Private Blood Strike source and logic research repository.

The user confirmed operation and sufficient skin effects on **2026-11-05 (Asia/Bangkok)**. The earlier **v2.1.1-stable** tag remains a separate checkpoint; the current source includes subsequent runtime, effect and UI changes.

This checkpoint includes the revised CiyE menu and loader presentation, permanent high-tier cosmetic selection, and the Inventory tab. Inventory shows equipped selections only. Clicking a skin name or Apply in Characters, Knives or Guns immediately replaces and saves its slot. Compatible saved skins are scheduled again when combat equipment or sessions change; inactive history from older files is removed.

Validation details and measured limits are recorded with each logic report. Unit tests extract runtime functions with mocked game objects; they do not establish compatibility for every game mode or skin.

Git tracks source, tests, vendored source dependencies, and reports/evidence about game logic and functions. Generated binaries, distribution copies, build/packaging manifests, local IPC state, logs, archives and credentials are excluded. Vendored dependencies retain their upstream license files. No public license is granted for project code.

The separately cloned driver/kdmapper_src repository is excluded rather than recorded as an unresolved Git link. This checkpoint does not package external mapper/driver tools.

Details: [Inventory](docs/skin-inventory.md), [release notes](CHANGELOG.md), [design](DESIGN.md).

Run the isolated regression suite with `python -m unittest discover -s tests`.

Logic reports: [skin effects](reports/weapon-effects/2026-11-05_skin-effects-fix-report.md), [recoil](reports/recoil-probe/2026-11-05_recoil-report.md), [runtime performance](reports/performance/2026-11-05_runtime-lag-report.md), and [custom-room fields](reports/custom-room/2026-11-05_custom-room-report.md). The full weapon-effect mapping is in `reports/weapon-effects/weapon-effects.json` and `all-menu-guns.csv`.

Offset extraction: `tools/offset_dump.py`, with SDK/header inputs under `reference/offsets` and recorded results under `reports/offsets`.
