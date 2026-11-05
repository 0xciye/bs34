# bs34

Private Blood Strike source checkpoint: **v2.1.0-stable**.

Status: the user confirmed in-game operation on **2026-11-05 (Asia/Bangkok)**. This is the user's validation; the coding agent did not independently build or run the application in game.

This checkpoint includes the revised CiyE menu and loader presentation, permanent high-tier cosmetic selection, and the Inventory tab. Inventory shows equipped selections only. Clicking a skin name or Apply in Characters, Knives or Guns immediately replaces and saves its slot. Compatible saved skins are scheduled again when combat equipment or sessions change; inactive history from older files is removed.

Both main and dist runtime copies passed **40 offline tests each**. Tests extract only cosmetic functions and use mocked game objects. They do not start the full runtime or establish live-game compatibility.

The tag records source files. Generated binaries, drivers, local IPC state, logs, archives and credentials are excluded. Vendored source dependencies retain their upstream license files. No public license is granted for project code.

The separately cloned driver/kdmapper_src repository is excluded rather than recorded as an unresolved Git link. This checkpoint does not package external mapper/driver tools.

Details: [Inventory](docs/skin-inventory.md), [release notes](CHANGELOG.md), [design](DESIGN.md).

Run the isolated regression suite with `python tests/test_skin_flow.py`. To test the independently maintained dist copy, set `SKIN_RUNTIME_SOURCE` to `dist/pyexec/bs_runtime.py` before running the same suite.
