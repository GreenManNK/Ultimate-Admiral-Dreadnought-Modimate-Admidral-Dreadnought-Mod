from __future__ import annotations

import argparse
import csv
import io
import os
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

try:
    import UnityPy
    import lz4.block
    import msgpack
except Exception as exc:
    raise SystemExit(f"Missing dependency: {exc}")


DEFAULT_GAME_DATA = Path(
    r"F:\SteamLibrary\steamapps\common\Ultimate Admiral Dreadnoughts\Ultimate Admiral Dreadnoughts_Data"
)
DEFAULT_SAVE_ROOT = Path.home() / r"AppData/LocalLow/Game Labs/Ultimate Admiral Dreadnoughts"

ASSEMBLY_PATCH_OFFSET = 0x2D8243
ASSEMBLY_PATCH_BYTES = bytes.fromhex("3d d0 07 00 00")

PLAYER_SHIPYARD_MIN = 15_000_000.0
PLAYER_FUNDS_TARGET = 500_000_000_000.0
PLAYER_FUNDS_TRIGGER = 499_990_000_000.0
AI_SHIPYARD_CAP = 50_000.0
AI_FUNDS_CAP = 5_000_000_000.0
PLAYER_SURFACE_CREW_LEVEL = 4
PLAYER_SHIP_TRAINING_POINTS = 100.0
PLAYER_ACCURACY_TECH = {
    "aim_control_end": 14,
    "aim_rangefinder_end": 13,
    "tactics_tactics_end": 21,
    "tactics_comm_end": 24,
}

PARAM_VALUES = {
    "shipyard_start": "12500",
    "shipyard_start_increase": "250",
    "shipyard_dev_cost": "30000",
    "shipyard_dev_min_amount_tons": "500",
    "shipyard_dev_max_amount_tons": "4000",
    "shipyard_max_modifier": "6",
    "shipyard_build_amount_max_modifier": "8",
    "campaign_max_year": "1950",
    "cash_start_part": "0.0035",
    "cash_start_randomness": "0",
    "ai_difficulty_easy_income_multiplier": "0.2",
    "ai_difficulty_normal_income_multiplier": "0.25",
    "ai_difficulty_hard_income_multiplier": "0.35",
    "ai_difficulty_legendary_income_multiplier": "0.5",
    "ai_difficulty_easy_aggression_multiplier": "0.35",
    "ai_difficulty_normal_aggression_multiplier": "0.45",
    "ai_difficulty_hard_aggression_multiplier": "0.55",
    "ai_difficulty_legendary_aggression_multiplier": "0.65",
    "ai_difficulty_easy_tension_multiplier": "0.45",
    "ai_difficulty_normal_tension_multiplier": "0.55",
    "ai_difficulty_hard_tension_multiplier": "0.65",
    "ai_difficulty_legendary_tension_multiplier": "0.75",
    "ai_difficulty_hard_tech_multiplier": "0.75",
    "ai_difficulty_legendary_tech_multiplier": "0.85",
    "battle_avoid_threshold": "2",
    "general_retreat_threshold": "0.35",
    "ai_power_exp_factor": "0.25",
    "ai_risk_exp_factor": "5",
    "ai_aggressiveness_exp_factor": "0.2",
    "ai_opponent_replacement_money": "0.25",
    "ai_ship_gdp_ratio": "500000",
    "override_shipybuilding_limit": "0.2",
    "ai_shipyard_threshold_cost": "0.1",
    "ai_refit_base": "0.1",
    "ai_refit_simple": "0.12",
    "fleet_generation_chance": "5",
    "fleet_generation_years": "1",
    "fleet_generation_index_chance": "50",
    "fleet_generation_money_min": "0.5",
    "fleet_generation_money_max": "0.5",
    "ship_construction_time_modifier": "0.6",
    "repair_cost_mult": "0.5",
    "repair_time_mult": "0.45",
    "refit_time_mult": "0.3",
    "refit_time_modifier": "0.3",
    "suspend_cost_multiplier": "0.15",
    "ship_movement_cost_turn": "0.005",
    "price_steel": "0.000318",
    "price_nickel": "0.008406",
    "price_chrome": "0.00459",
    "price_molybdenum": "0.0588",
    "price_copper": "0.003498",
    "price_hull": "1070.706",
    "price_surv": "485.22825",
    "price_armor": "578.29668",
    "price_turret": "2055.87",
    "price_barrel": "3768.349005",
    "price_engine": "197.16",
    "price_anti_torp": "407.04",
    "price_fuel": "400",
    "price_ammo": "1550",
    "price_torpedoes": "2000",
    "mines_cost_mod": "8250",
    "minesweep_cost_mod": "11250",
    "ammunition_cost_mod": "5",
    "fuel_cost_mod": "0.04",
    "action_cooldown_time": "2",
    "armor_limit_multiplier_big_guns": "5",
    "citadel_offset_modifier": "7700",
    "conning_tower_armor_percent": "0.064",
    "w_armor_belt": "0.01100",
    "w_armor_belt_extended": "0.01000",
    "w_armor_deck": "0.01900",
    "w_armor_deck_extended": "0.01250",
    "w_conning_tower": "0.03",
    "w_conning_tower_threshold": "0.8",
    "w_superstructure": "0.11",
    "w_antitorpedo": "0.10000",
    "w_1st_belt": "0.00468164794",
    "w_1st_deck": "0.006578947368",
    "w_2nd_belt": "0.003745318352",
    "w_2nd_deck": "0.005263157895",
    "w_3rd_belt": "0.002808988764",
    "w_3rd_deck": "0.003947368421",
}

PLAYER_BASELINES = {
    "britain": ("13500", "6250000000", ""),
    "france": ("12500", "5500000000", "1, 1, 1, 0.8, 0.75, 0.8"),
    "germany": ("12000", "6000000000", "1.05, 1.125, 1.2, 0.7, 0.85, 1"),
    "usa": ("8500", "5750000000", "0.8, 0.9, 1, 1.2, 1.05, 1.5"),
    "russia": ("13000", "5000000000", "1, 0.95, 0.9, 0.95, 1.25 1.5"),
    "italy": ("9500", "4500000000", "0.8, 0.9, 0.9, 0.85, 0.95, 1"),
    "austria": ("10500", "4400000000", "0.95, 1.05, 1.15, 0.45, 0.55, 0.6"),
    "japan": ("11000", "4000000000", "1, 1, 1, 1.1, 1.2, 1.3"),
    "spain": ("8500", "3800000000", "1, 0.9, 0.8, 0.8, 0.8, 0.8"),
    "china": ("8800", "3800000000", "1.2, 0.5, 0.9, 1, 1.05, 1.1"),
}

AI_CAPS = {
    "aiTechMod": 0.2,
    "aiPlayerCounter": 0.2,
    "aiTrainingMod": 0.02,
    "aiShipyardMod": 0.05,
    "aiTrMod": 0.05,
    "aiOffense": 0.5,
    "aiDefense": 0.6,
    "seaControlProbability": 0.35,
    "invadeProbability": 0.1,
    "protectProbability": 0.35,
    "aiShipbuilding": 0.25,
    "aiRefit": 0.2,
    "aiAction": 0.5,
    "aiNavalnvasion": 0.1,
}


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def get_script_root() -> Path:
    return Path(__file__).resolve().parents[1]


def backup_file(path: Path, backup_dir: Path, dry_run: bool) -> None:
    if not path.exists():
        return
    if dry_run:
        print(f"DRY backup {path} -> {backup_dir}")
        return
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup_dir / path.name)


def read_text_asset(data) -> str:
    script = data.m_Script
    return script.decode("utf-8-sig", "replace") if isinstance(script, bytes) else script


def split_table(text: str):
    lines = text.splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.startswith("@name"))
    prefix = lines[:header_index]
    rows = list(csv.reader(io.StringIO("\n".join(lines[header_index:])), delimiter=","))
    return prefix, rows, text.endswith("\n")


def join_table(prefix, rows, final_newline: bool) -> str:
    out = io.StringIO()
    writer = csv.writer(out, delimiter=",", lineterminator="\n")
    writer.writerows(rows)
    text = ("\n".join(prefix) + "\n" if prefix else "") + out.getvalue()
    return text if final_newline else text.rstrip("\n")


def colmap(header):
    return {name: i for i, name in enumerate(header)}


def fmt_number(value: float) -> str:
    if abs(value - round(value)) < 1e-6:
        return str(int(round(value)))
    return ("%.6f" % value).rstrip("0").rstrip(".")


def remove_function_tokens(value: str, names: set[str]) -> str:
    if not value:
        return value
    tokens = [token.strip() for token in value.split(",") if token.strip()]
    kept = []
    removed = False
    pattern = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\(")
    for token in tokens:
        match = pattern.match(token)
        if match and match.group(1) in names:
            removed = True
            continue
        kept.append(token)
    return ", ".join(kept) if removed else value


def load_hull_targets() -> dict[tuple[str, int], str]:
    path = get_script_root() / "data" / "hull_tonnage_max_400k.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    targets = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            targets[(row["name"], int(row["occurrence"]))] = row["tonnageMax"]
    return targets


def patch_params(text: str) -> tuple[str, int]:
    prefix, rows, final_newline = split_table(text)
    columns = colmap(rows[0])
    changed = 0
    for row in rows[1:]:
        if len(row) <= max(columns["@name"], columns["value"]):
            continue
        key = row[columns["@name"]]
        if key in PARAM_VALUES and row[columns["value"]] != PARAM_VALUES[key]:
            row[columns["value"]] = PARAM_VALUES[key]
            changed += 1
    return join_table(prefix, rows, final_newline), changed


def patch_players(text: str) -> tuple[str, int]:
    prefix, rows, final_newline = split_table(text)
    columns = colmap(rows[0])
    changed = 0
    for row in rows[1:]:
        if len(row) <= max(columns["@name"], columns["shipyardStart"], columns["nation_base_income"]):
            continue
        name = row[columns["@name"]]
        if name not in PLAYER_BASELINES:
            continue
        shipyard, income, income_mod = PLAYER_BASELINES[name]
        updates = {
            "shipyardStart": shipyard,
            "nation_base_income": income,
            "startingyear_income_mod": income_mod,
        }
        for column, value in updates.items():
            if column in columns and len(row) > columns[column] and row[columns[column]] != value:
                row[columns[column]] = value
                changed += 1
    return join_table(prefix, rows, final_newline), changed


def patch_parts(text: str) -> tuple[str, int]:
    hull_targets = load_hull_targets()
    prefix, rows, final_newline = split_table(text)
    columns = colmap(rows[0])
    changed = 0
    occurrence = defaultdict(int)
    for row in rows[1:]:
        if len(row) <= max(columns["@name"], columns["type"]):
            continue
        name = row[columns["@name"]].strip()
        if not name or name.startswith("#"):
            continue
        part_type = row[columns["type"]].strip()
        if "countries" in columns and len(row) > columns["countries"] and row[columns["countries"]].strip():
            row[columns["countries"]] = ""
            changed += 1
        if "param" in columns and len(row) > columns["param"]:
            original = row[columns["param"]]
            blocked = {"needunlock"}
            if part_type in {"tower_main", "tower_sec", "funnel"}:
                blocked.add("need")
            updated = remove_function_tokens(original, blocked)
            if updated != original:
                row[columns["param"]] = updated
                changed += 1
        if part_type == "hull" and "tonnageMax" in columns:
            occ = occurrence[name]
            occurrence[name] += 1
            target = hull_targets.get((name, occ))
            if target is not None and len(row) > columns["tonnageMax"] and row[columns["tonnageMax"]] != target:
                row[columns["tonnageMax"]] = target
                changed += 1
    return join_table(prefix, rows, final_newline), changed


def patch_comp_types(text: str) -> tuple[str, int]:
    prefix, rows, final_newline = split_table(text)
    columns = colmap(rows[0])
    changed = 0
    if "shipTypes" not in columns:
        return text, changed
    for row in rows[1:]:
        if len(row) > columns["shipTypes"] and row[columns["shipTypes"]].strip():
            row[columns["shipTypes"]] = ""
            changed += 1
    return join_table(prefix, rows, final_newline), changed


def patch_technologies(text: str) -> tuple[str, int]:
    prefix, rows, final_newline = split_table(text)
    changed = 0
    for row in rows[1:]:
        for index, cell in enumerate(row):
            if "obsolete(" in cell:
                updated = remove_function_tokens(cell, {"obsolete"})
                if updated != cell:
                    row[index] = updated
                    changed += 1
    return join_table(prefix, rows, final_newline), changed


def patch_ai_personalities(text: str) -> tuple[str, int]:
    prefix, rows, final_newline = split_table(text)
    columns = colmap(rows[0])
    changed = 0
    for row in rows[1:]:
        for column, cap in AI_CAPS.items():
            if column not in columns or len(row) <= columns[column] or row[columns[column]] == "":
                continue
            try:
                value = float(row[columns[column]])
            except ValueError:
                continue
            if value > cap:
                row[columns[column]] = fmt_number(cap)
                changed += 1
        if "aiParams" in columns and len(row) > columns["aiParams"]:
            original = row[columns["aiParams"]]
            updated = remove_function_tokens(original, {"TechMod"})
            if updated != original:
                row[columns["aiParams"]] = updated
                changed += 1
    return join_table(prefix, rows, final_newline), changed


def patch_resources(game_data: Path, dry_run: bool) -> dict[str, int]:
    asset = game_data / "resources.assets"
    if not asset.exists():
        raise FileNotFoundError(asset)
    env = UnityPy.load(str(asset))
    patches = {
        "params": patch_params,
        "players": patch_players,
        "parts": patch_parts,
        "compTypes": patch_comp_types,
        "technologies": patch_technologies,
        "aiPersonalities": patch_ai_personalities,
    }
    report = {}
    for obj in env.objects:
        if obj.type.name != "TextAsset":
            continue
        data = obj.read()
        patcher = patches.get(data.m_Name)
        if not patcher:
            continue
        original = read_text_asset(data)
        updated, count = patcher(original)
        report[data.m_Name] = count
        if count and not dry_run:
            data.m_Script = updated
            data.save()
    if not dry_run:
        tmp = asset.with_suffix(".assets.codex.tmp")
        tmp.write_bytes(env.file.save())
        os.replace(tmp, asset)
    return report


def patch_gameassembly(game_root: Path, dry_run: bool) -> bool:
    assembly = game_root / "GameAssembly.dll"
    if not assembly.exists():
        raise FileNotFoundError(assembly)
    data = bytearray(assembly.read_bytes())
    end = ASSEMBLY_PATCH_OFFSET + len(ASSEMBLY_PATCH_BYTES)
    if len(data) < end:
        raise ValueError(f"{assembly} is smaller than expected")
    if bytes(data[ASSEMBLY_PATCH_OFFSET:end]) == ASSEMBLY_PATCH_BYTES:
        return False
    if not dry_run:
        data[ASSEMBLY_PATCH_OFFSET:end] = ASSEMBLY_PATCH_BYTES
        assembly.write_bytes(data)
    return True


def unpack_save(path: Path):
    top = msgpack.unpackb(
        path.read_bytes(),
        raw=False,
        strict_map_key=False,
        ext_hook=lambda code, payload: msgpack.ExtType(code, payload),
    )
    if not isinstance(top, msgpack.ExtType) or top.code != 99:
        raise ValueError(f"{path.name}: unsupported save wrapper")
    payload = top.data
    if not payload or payload[0] != 0xD2:
        raise ValueError(f"{path.name}: unexpected save payload")
    size = int.from_bytes(payload[1:5], "big", signed=True)
    decoded = lz4.block.decompress(payload[5:], uncompressed_size=size)
    return msgpack.unpackb(decoded, raw=False, strict_map_key=False)


def pack_save(obj) -> bytes:
    decoded = msgpack.packb(obj, use_bin_type=False, strict_types=False, use_single_float=True)
    payload = b"\xD2" + len(decoded).to_bytes(4, "big", signed=True) + lz4.block.compress(
        decoded, store_size=False
    )
    return msgpack.packb(msgpack.ExtType(99, payload), use_bin_type=False, strict_types=False, use_single_float=True)


def patch_save_object(obj) -> int:
    if not isinstance(obj, list) or len(obj) <= 14 or not isinstance(obj[6], list):
        return 0
    changed = 0
    players = obj[6]
    human_nations = {row[1] for row in players if isinstance(row, list) and len(row) > 52 and row[2] is True}
    hull_targets = defaultdict(float)
    for (name, _occurrence), value in load_hull_targets().items():
        hull_targets[name] = max(hull_targets[name], float(value))
    for row in players:
        if not isinstance(row, list) or len(row) <= 52:
            continue
        if row[2] is True:
            if float(row[20]) < PLAYER_SHIPYARD_MIN:
                row[20] = PLAYER_SHIPYARD_MIN
                changed += 1
            if float(row[52]) < PLAYER_FUNDS_TRIGGER:
                row[52] = PLAYER_FUNDS_TARGET
                changed += 1
            if len(row) > 41 and isinstance(row[41], dict):
                for key, expected in PLAYER_ACCURACY_TECH.items():
                    if row[41].get(key, -1) < expected:
                        row[41][key] = expected
                        changed += 1
            if len(row) > 59 and isinstance(row[59], (int, float)) and float(row[59]) < 100:
                row[59] = 100.0
                changed += 1
        else:
            if float(row[20]) > AI_SHIPYARD_CAP:
                row[20] = AI_SHIPYARD_CAP
                changed += 1
            if float(row[52]) > AI_FUNDS_CAP:
                row[52] = AI_FUNDS_CAP
                changed += 1
    for ship_list_index in (13, 14):
        if len(obj) <= ship_list_index or not isinstance(obj[ship_list_index], list):
            continue
        for ship in obj[ship_list_index]:
            if not (isinstance(ship, list) and len(ship) > 77 and len(ship) > 62 and ship[62] in human_nations):
                continue
            if ship_list_index == 13 and len(ship) > 15:
                target = hull_targets.get(ship[10])
                if target and isinstance(ship[15], (int, float)) and float(ship[15]) < target:
                    ship[15] = float(target)
                    changed += 1
            if float(ship[77]) < PLAYER_SHIP_TRAINING_POINTS:
                ship[77] = PLAYER_SHIP_TRAINING_POINTS
                changed += 1
            if (
                ship_list_index == 13
                and len(ship) > 28
                and isinstance(ship[28], int)
                and ship[28] < PLAYER_SURFACE_CREW_LEVEL
            ):
                ship[28] = PLAYER_SURFACE_CREW_LEVEL
                changed += 1
    names = [row[1] for row in players if isinstance(row, list) and len(row) > 2]
    duplicates = [name for name, count in Counter(names).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate player rows after patch: {duplicates}")
    return changed


def patch_saves(save_root: Path, dry_run: bool) -> dict[str, int]:
    report = {}
    for path in sorted(save_root.glob("save_*.bin")):
        obj = unpack_save(path)
        changed = patch_save_object(obj)
        report[path.name] = changed
        if changed and not dry_run:
            tmp = path.with_suffix(path.suffix + ".codex.tmp")
            tmp.write_bytes(pack_save(obj))
            os.replace(tmp, path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply the Codex UAD patch without redistributing game binaries.")
    parser.add_argument("--game-data", type=Path, default=DEFAULT_GAME_DATA)
    parser.add_argument("--save-root", type=Path, default=DEFAULT_SAVE_ROOT)
    parser.add_argument("--skip-assets", action="store_true")
    parser.add_argument("--skip-assembly", action="store_true")
    parser.add_argument("--skip-saves", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    game_data = args.game_data.resolve()
    game_root = game_data.parent
    save_root = args.save_root.resolve()
    backup_root = save_root / f"codex_patch_backup_{timestamp()}"

    if not args.skip_assets:
        backup_file(game_data / "resources.assets", backup_root / "game", args.dry_run)
    if not args.skip_assembly:
        backup_file(game_root / "GameAssembly.dll", backup_root / "game", args.dry_run)
    if not args.skip_saves and save_root.exists():
        for save in sorted(save_root.glob("save_*.bin")):
            backup_file(save, backup_root / "saves", args.dry_run)

    if not args.skip_assets:
        print("resources.assets", patch_resources(game_data, args.dry_run))
    if not args.skip_assembly:
        print("GameAssembly.dll patched", patch_gameassembly(game_root, args.dry_run))
    if not args.skip_saves:
        print("saves", patch_saves(save_root, args.dry_run))
    print(f"backup: {backup_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
