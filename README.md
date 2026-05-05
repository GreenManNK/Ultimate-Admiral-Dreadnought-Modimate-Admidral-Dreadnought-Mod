# Ultimate Admiral Dreadnoughts - Codex Patch Snapshot

This repository is a lightweight patch ledger and patcher for the locally modified game install.
It intentionally does not track `resources.assets`, `GameAssembly.dll`, or campaign save binaries because those files are large/proprietary and unsuitable for normal Git hosting. The script in `scripts/apply_codex_patch.py` reapplies the changes to a local game install instead.

## Current live game targets

- Game data: `F:\SteamLibrary\steamapps\common\Ultimate Admiral Dreadnoughts\Ultimate Admiral Dreadnoughts_Data`
- Saves: `C:\Users\NITRO\AppData\LocalLow\Game Labs\Ultimate Admiral Dreadnoughts`

## Applied patch groups

- All hulls unlocked for all nations.
- Hull obsolete gates removed; campaign start max year kept at 1950.
- Hull tonnage limits raised safely: all existing hull `tonnageMax` values raised again with a 400,000 ton cap; `tonnageMin` values left unchanged.
- Small TB/DD hull tonnage limits raised again to reduce random-ship generator weight failures and log spam.
- Campaign retirement/end byte patch in `GameAssembly.dll` kept at compare year 2000.
- Campaign battle/fleet generation reduced to lower turn-processing load.
- Global new-campaign cash and shipyard start restored to vanilla-safe levels so AI no longer receives player-grade boosts.
- Custom reserve ship-name pools added for USA and Japan so mass-built player fleets get names instead of falling back to numeric hull labels.
- Safe NAR ship-name rows added for Brazil, Argentina, and Chile; placeholder names are skipped and rows are marker-tagged to avoid duplicate additions.
- Existing saves hotfixed to player shipyard >= 15,000,000 and funds ~= 500B.
- Existing saves hotfixed to cap AI shipyard at 50,000 tons and AI funds at 5B.
- Existing saves hotfixed to move AI ships away from player-owned ports, preventing repeated `CRITICAL ERROR Move ... to port ...` log spam.
- Existing saves hotfixed to boost player-only gunnery: player aim/rangefinder/tactics tech gates raised and player ship/sub training points set to 100.
- Existing saves hotfixed so player ships under construction have at most 6 months remaining; AI build queues are not accelerated.
- Existing saves hotfixed to remove AI ships still under construction and clean their task-force route references, reducing turn-processing load without touching player ships.
- Existing saves normalized so player saved ship designs use their previous max-tonnage value plus a 35% margin, instead of stale underweight limits or an excessive 400k value.
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
