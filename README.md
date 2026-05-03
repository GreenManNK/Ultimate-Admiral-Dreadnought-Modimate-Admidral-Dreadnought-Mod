# Ultimate Admiral Dreadnoughts - Codex Patch Snapshot

This repository is a lightweight patch ledger for the locally modified game install.
It intentionally does not track `resources.assets`, `GameAssembly.dll`, or campaign save binaries because those files are large/proprietary and unsuitable for normal Git hosting.

## Current live game targets

- Game data: `F:\SteamLibrary\steamapps\common\Ultimate Admiral Dreadnoughts\Ultimate Admiral Dreadnoughts_Data`
- Saves: `C:\Users\NITRO\AppData\LocalLow\Game Labs\Ultimate Admiral Dreadnoughts`

## Applied patch groups

- All hulls unlocked for all nations.
- Hull obsolete gates removed; campaign start max year kept at 1950.
- Campaign retirement/end byte patch in `GameAssembly.dll` kept at compare year 2000.
- Global new-campaign cash and shipyard start restored to vanilla-safe levels so AI no longer receives player-grade boosts.
- Existing saves hotfixed to player shipyard >= 15,000,000 and funds ~= 500B.
- Existing saves hotfixed to cap AI shipyard at 50,000 tons and AI funds at 5B.
- AI economy, aggression, tech, training, shipbuilding, invasion, refit, and research modifiers nerfed for campaign stability.
- AI `TechMod(...)` bonuses removed from personalities.
- Construction economy normalized: main build time kept vanilla-safe, repair cost reduced to vanilla, and distorted DIP material/weapon/ammo/fuel costs restored to stable baseline.
- Parts/equipment unlocks: `countries`, `needunlock`, `compTypes.shipTypes` cleared.
- Cross-hull towers/funnels: `need(...)` removed from `tower_main`, `tower_sec`, and `funnel`; mount points preserved.
- DIP-safe import: selected data tables and selected params merged while preserving local campaign/AI/player patches.

## Push note

To push this snapshot, add a remote manually:

```powershell
git remote add origin <repo-url>
git push -u origin main
```

Do not add raw game binaries unless using an appropriate private repo and large-file strategy.
