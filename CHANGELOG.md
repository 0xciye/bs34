# Changelog

## v2.1.0-stable — 2026-11-05

Stable checkpoint, based on the user's confirmation that the current version works in game.

- Added Inventory next to Characters, Knives and Guns.
- Persist Apply selections, retain history, and select the latest skin per hero/weapon group.
- Requeue compatible saved skins as combat avatars, equipment and sessions change, including training sessions represented by combat avatars.
- Resolve overlapping melee selections by recency; preserve saved files on read/write errors.
- Refined the menu and loader to the supplied Roblox visual reference; omitted the sidebar status/footer as requested.
- Preserved separate main and dist runtime sources and added isolated cosmetic regression coverage.

Validation: 40 offline tests passed for each runtime. User-reported in-game success is recorded separately from the agent's tests. No new application build, binary release or independent in-game validation was performed by the agent.

Known scope: matching hero, compatible melee class and available model resources are required. Artifact cosmetics need more than a single ID. The old update_runtime.py generator may overwrite edited runtime functions from its .bak input if run manually.
