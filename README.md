# Ultimate Admiral Dreadnoughts - Codex Patch Snapshot

This repository is a lightweight patch ledger and patcher for the locally modified game install.
It intentionally does not track `resources.assets`, `GameAssembly.dll`, or campaign save binaries because those files are large/proprietary and unsuitable for normal Git hosting. The script in `scripts/apply_codex_patch.py` reapplies the changes to a local game install instead.

## Current live game targets

- Game data: `F:\SteamLibrary\steamapps\common\Ultimate Admiral Dreadnoughts\Ultimate Admiral Dreadnoughts_Data`
- Saves: `C:\Users\NITRO\AppData\LocalLow\Game Labs\Ultimate Admiral Dreadnoughts`

## Applied patch groups

- All hulls unlocked for all nations.
- Hull obsolete gates removed; campaign start max year kept at 1950.
- Hull tonnage limits rebalanced: BB/BC/CA/CL/DD/TB/TR caps are class-based instead of the previous 400,000 ton super-cap; `tonnageMin` values are left unchanged.
- Small TB/DD/CL hull floors are kept high enough to reduce random-ship generator weight failures and log spam.
- Campaign retirement/end byte patch in `GameAssembly.dll` kept at compare year 2000.
- Campaign battle/fleet generation reduced to lower turn-processing load.
- Mission challenge tech references sanitized so obsolete `gun_small`/`gun_large` style tech types no longer spam errors during game data load.
- Global new-campaign cash and shipyard start restored to vanilla-safe levels so AI no longer receives player-grade boosts.
- Custom reserve ship-name pools added for USA and Japan so mass-built player fleets get names instead of falling back to numeric hull labels.
- Safe NAR ship-name rows added for Brazil, Argentina, and Chile; placeholder names are skipped and rows are marker-tagged to avoid duplicate additions.
- Famous-people ship-name pool added for the ten major campaign nations across all ship classes, using a curated deceased/historical/public-figure list and duplicate-safe marker tags.
- Existing saves hotfixed to player shipyard >= 15,000,000 and funds ~= 500B.
- Existing saves hotfixed to cap AI shipyard at 50,000 tons and AI funds at 5B.
- Existing saves hotfixed to move AI ships away from player-owned ports, preventing repeated `CRITICAL ERROR Move ... to port ...` log spam.
- Existing saves hotfixed to boost player-only gunnery: player aim/rangefinder/tactics tech gates raised and player ship/sub training points set to 100.
- Existing saves hotfixed so player ships under construction have at most 6 months remaining; AI build queues are not accelerated.
- Existing saves hotfixed to remove AI ships still under construction and clean their task-force route references, reducing turn-processing load without touching player ships.
- Existing saves hotfixed to sanitize task-force routes by removing stale or duplicate ship references without deleting valid ships.
- Existing saves keep already-built ships intact; the balanced hull caps affect new/refit design limits instead of deleting player ships.
- AI economy, aggression, tech, training, shipbuilding, invasion, refit, and research modifiers nerfed for campaign stability.
- AI `TechMod(...)` bonuses removed from personalities.
- Construction economy normalized: new-build time reduced further for visibility, repair cost reduced to vanilla, and distorted DIP material/weapon/ammo/fuel costs restored to stable baseline.
- Parts/equipment unlocks: `countries`, `needunlock`, `compTypes.shipTypes` cleared.
- Cross-nation gun/model availability: `partModels.countries` cleared while `shipTypes` and model references are preserved.
- Cross-hull towers/funnels: `need(...)` removed from `tower_main`, `tower_sec`, and `funnel`; mount points preserved.
- DIP-safe import: selected data tables and selected params merged while preserving local campaign/AI/player patches.
- NAR alpha review: full table replacement is intentionally avoided because several campaign/world tables are older or schema-incompatible; safe ship-name rows and the cross-nation model-unlock idea are folded into the local patcher.

## Apply

Install dependencies, then run the patcher:

```powershell
pip install -r requirements.txt
python .\scripts\apply_codex_patch.py
```

Use `--dry-run` to inspect what it would change. The patcher creates backups under the save folder before writing.

Do not add raw game binaries or campaign saves to this repo.

## Diagnostics

Scan recent game logs for known campaign/performance errors:

```powershell
python .\scripts\scan_uad_logs.py
```
