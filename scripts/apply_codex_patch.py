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
PLAYER_BUILD_STATUS = 2
PLAYER_BUILD_REMAINING_FACTOR = 0.25
PLAYER_BUILD_REMAINING_CAP_MONTHS = 6.0
PLAYER_BUILD_REMAINING_MIN_MONTHS = 1.0
AI_BUILD_STATUS = 2
SAVE_SURFACE_SHIPS_INDEX = 13
SAVE_SUBMARINES_INDEX = 14
SAVE_TASK_FORCES_INDEX = 22
SHIP_PORT_FIELDS = (73, 74, 81)
PLAYER_ACCURACY_TECH = {
    "aim_control_end": 14,
    "aim_rangefinder_end": 13,
    "tactics_tactics_end": 21,
    "tactics_comm_end": 24,
}
CUSTOM_NAME_MARKER = "codex_custom_name_pool"
NAR_SAFE_NAME_MARKER = "codex_nar_safe_ship_name_pool"
FAMOUS_NAME_MARKER = "codex_famous_people_ship_name_pool"
CUSTOM_NAME_COUNTRIES = ("usa", "japan")
FAMOUS_NAME_COUNTRIES = ("britain", "france", "germany", "usa", "russia", "italy", "austria", "japan", "spain", "china")
FAMOUS_NAME_SHIP_TYPES = ("bb", "bc", "ca", "cl", "dd", "tb", "ss")
INVALID_MISSION_TECH_TYPES = {"gun_small", "gun_medium", "gun_large", "gun_verylarge", "gun_xlarge"}
CUSTOM_NAME_COUNTS = {
    "bb": 240,
    "bc": 160,
    "ca": 360,
    "cl": 280,
    "dd": 500,
    "tb": 250,
    "ss": 160,
}
CUSTOM_NAME_PREFIXES = (
    "Aegis",
    "Anvil",
    "Arc",
    "Argent",
    "Ash",
    "Atlas",
    "Beacon",
    "Boreal",
    "Cinder",
    "Citadel",
    "Comet",
    "Crown",
    "Dawn",
    "Eclipse",
    "Ember",
    "Falcon",
    "Frontier",
    "Granite",
    "Harbor",
    "Horizon",
    "Iron",
    "Keystone",
    "Liberty",
    "Meridian",
    "Nova",
    "Onyx",
    "Orion",
    "Pioneer",
    "Prairie",
    "Radiant",
    "Ranger",
    "Resolute",
    "Sable",
    "Sentinel",
    "Sierra",
    "Sovereign",
    "Summit",
    "Tempest",
    "Titan",
    "Valor",
)
CUSTOM_NAME_SUFFIXES = (
    "Vanguard",
    "Sentinel",
    "Defiance",
    "Endeavor",
    "Guardian",
    "Ranger",
    "Reliance",
    "Victory",
    "Protector",
    "Challenger",
    "Pathfinder",
    "Watchman",
    "Bulwark",
    "Mariner",
    "Voyager",
    "Executor",
    "Thunder",
    "Arrow",
    "Falchion",
    "Haven",
)

PARAM_VALUES = {
    "shipyard_start": "15000000",
    "shipyard_start_increase": "250",
    "shipyard_dev_cost": "30000",
    "shipyard_dev_min_amount_tons": "500",
    "shipyard_dev_max_amount_tons": "4000",
    "shipyard_max_modifier": "6",
    "shipyard_build_amount_max_modifier": "8",
    "campaign_max_year": "1950",
    "cash_start_part": "1",
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
    "fleet_generation_chance": "0",
    "fleet_generation_years": "99",
    "fleet_generation_index_chance": "0",
    "fleet_generation_money_min": "0",
    "fleet_generation_money_max": "0",
    "ship_construction_time_modifier": "0.15",
    "Max_Battles": "2",
    "battle_chance": "250",
    "key_battle_chance": "100",
    "rebattle_chance": "0",
    "battle_tonnage_mod": "0.8",
    "battle_ships_mod": "0.25",
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
    "engine_hp_to_fcap": "0.00075",
    "engine_weight_coef_mod": "0.00000075",
    "speed_mult_1": "1.095",
    "speed_mult_2": "1.0685",
    "speed_mult_3": "1.08",
    "speed_mult_4": "1.1",
    "speed_mult_5": "1.125",
    "speed_mult_6": "1.15",
    "speed_mult_7": "1.1625",
    "speed_mult_8": "1.175",
    "armor_limit_multiplier_big_guns": "5",
    "citadel_offset_modifier": "7700",
    "conning_tower_armor_percent": "0.064",
    "w_armor_belt": "0.00880",
    "w_armor_belt_extended": "0.00800",
    "w_armor_deck": "0.01520",
    "w_armor_deck_extended": "0.01000",
    "w_conning_tower": "0.024",
    "w_conning_tower_threshold": "0.8",
    "w_superstructure": "0.095",
    "w_antitorpedo": "0.08500",
    "w_1st_belt": "0.003745318352",
    "w_1st_deck": "0.005263157895",
    "w_2nd_belt": "0.002996254682",
    "w_2nd_deck": "0.004210526316",
    "w_3rd_belt": "0.002247191011",
    "w_3rd_deck": "0.003157894737",
}

PLAYER_BASELINES = {
    "britain": ("15000000", "500000000000", ""),
    "france": ("15000000", "500000000000", "1, 1, 1, 0.8, 0.75, 0.8"),
    "germany": ("15000000", "500000000000", "1.05, 1.125, 1.2, 0.7, 0.85, 1"),
    "usa": ("15000000", "500000000000", "0.8, 0.9, 1, 1.2, 1.05, 1.5"),
    "russia": ("15000000", "500000000000", "1, 0.95, 0.9, 0.95, 1.25 1.5"),
    "italy": ("15000000", "500000000000", "0.8, 0.9, 0.9, 0.85, 0.95, 1"),
    "austria": ("15000000", "500000000000", "0.95, 1.05, 1.15, 0.45, 0.55, 0.6"),
    "japan": ("15000000", "500000000000", "1, 1, 1, 1.1, 1.2, 1.3"),
    "spain": ("15000000", "500000000000", "1, 0.9, 0.8, 0.8, 0.8, 0.8"),
    "china": ("15000000", "500000000000", "1.2, 0.5, 0.9, 1, 1.05, 1.1"),
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


def remove_tech_tokens_by_type(value: str, invalid_types: set[str]) -> str:
    if not value:
        return value
    tokens = [token.strip() for token in value.split(",") if token.strip()]
    kept = []
    removed = False
    pattern = re.compile(r"^tech\s*\(\s*([^;\)\s]+)")
    for token in tokens:
        match = pattern.match(token)
        if match and match.group(1) in invalid_types:
            removed = True
            continue
        kept.append(token)
    return ", ".join(kept) if removed else value


def load_hull_targets() -> dict[tuple[str, int], str]:
    path = get_script_root() / "data" / "hull_tonnage_vanilla.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    targets = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            targets[(row["name"], int(row["occurrence"]))] = row["tonnageMax"]
    return targets


def load_part_weight_targets() -> dict[tuple[str, str, int], str]:
    path = get_script_root() / "data" / "part_weight_reduced_75.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    targets = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            targets[(row["name"], row["type"], int(row["occurrence"]))] = row["weight"]
    return targets


def load_technology_tonnage_targets() -> dict[str, str]:
    path = get_script_root() / "data" / "technology_tonnage_limit_250pct.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {row["name"]: row["effect"] for row in csv.DictReader(handle)}


def load_nar_safe_ship_names() -> list[dict[str, str]]:
    path = get_script_root() / "data" / "nar_safe_ship_names.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [
            {
                "country": row["country"].strip(),
                "shipType": row["shipType"].strip(),
                "nameUi": row["nameUi"].strip(),
            }
            for row in csv.DictReader(handle)
            if row.get("country") and row.get("shipType") and row.get("nameUi")
        ]


def load_famous_people_ship_names() -> list[str]:
    path = get_script_root() / "data" / "famous_people_ship_names.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [
            row["nameUi"].strip()
            for row in csv.DictReader(handle)
            if row.get("nameUi") and row["nameUi"].strip()
        ]


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
    part_weight_targets = load_part_weight_targets()
    prefix, rows, final_newline = split_table(text)
    columns = colmap(rows[0])
    changed = 0
    hull_occurrence = defaultdict(int)
    part_weight_occurrence = defaultdict(int)
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
            occ = hull_occurrence[name]
            hull_occurrence[name] += 1
            target = hull_targets.get((name, occ))
            if target is not None and len(row) > columns["tonnageMax"] and row[columns["tonnageMax"]] != target:
                row[columns["tonnageMax"]] = target
                changed += 1
        elif "weight" in columns and len(row) > columns["weight"]:
            key = (name, part_type)
            occ = part_weight_occurrence[key]
            target = part_weight_targets.get((name, part_type, occ))
            if target is not None:
                part_weight_occurrence[key] += 1
                if row[columns["weight"]] != target:
                    row[columns["weight"]] = target
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


def patch_part_models(text: str) -> tuple[str, int]:
    # Steam 1.7.0 asserts in GameData.PostProcessAll if partModels country
    # restrictions are blanket-cleared. Keep model rows intact and unlock via
    # the safer parts/compTypes tables instead.
    return text, 0


def patch_technologies(text: str) -> tuple[str, int]:
    tonnage_targets = load_technology_tonnage_targets()
    prefix, rows, final_newline = split_table(text)
    columns = colmap(rows[0])
    changed = 0
    for row in rows[1:]:
        for index, cell in enumerate(row):
            if "obsolete(" in cell:
                updated = remove_function_tokens(cell, {"obsolete"})
                if updated != cell:
                    row[index] = updated
                    changed += 1
        if "effect" in columns and len(row) > max(columns["@name"], columns["effect"]):
            target_effect = tonnage_targets.get(row[columns["@name"]].strip())
            if target_effect is not None and row[columns["effect"]] != target_effect:
                row[columns["effect"]] = target_effect
                changed += 1
    return join_table(prefix, rows, final_newline), changed


def patch_missions(text: str) -> tuple[str, int]:
    prefix, rows, final_newline = split_table(text)
    columns = colmap(rows[0])
    challenge_columns = [columns[name] for name in ("ch1", "ch2", "ch3", "ch4") if name in columns]
    changed = 0
    for row in rows[1:]:
        for index in challenge_columns:
            if len(row) <= index or "tech(gun_" not in row[index]:
                continue
            updated = remove_tech_tokens_by_type(row[index], INVALID_MISSION_TECH_TYPES)
            if updated != row[index]:
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


def patch_ship_names(text: str) -> tuple[str, int]:
    prefix, rows, final_newline = split_table(text)
    columns = colmap(rows[0])
    changed = 0
    if "country" not in columns or "enabled" not in columns:
        return text, changed
    max_id = max((int(row[0]) for row in rows[1:] if row and row[0].isdigit()), default=7000)
    existing = set()
    for row in rows[1:]:
        if len(row) <= max(columns["country"], columns["enabled"]):
            continue
        if row[columns["country"]].strip() == "scandinavia" and row[columns["enabled"]] != "0":
            row[columns["enabled"]] = "0"
            changed += 1
        if len(row) > max(columns["country"], columns["shipType"], columns["nameUi"]):
            existing.add(
                (
                    row[columns["country"]].strip(),
                    row[columns["shipType"]].strip(),
                    row[columns["nameUi"]].strip(),
                )
            )
    header_len = len(rows[0])
    marker_index = columns.get("#infoLink")
    for country in CUSTOM_NAME_COUNTRIES:
        for ship_type, count in CUSTOM_NAME_COUNTS.items():
            for index in range(1, count + 1):
                name = custom_ship_name(ship_type, index)
                key = (country, ship_type, name)
                if key in existing:
                    continue
                max_id += 1
                row = [""] * header_len
                row[columns["@name"]] = str(max_id)
                row[columns["nameUi"]] = name
                row[columns["country"]] = country
                row[columns["shipType"]] = ship_type
                if marker_index is not None:
                    row[marker_index] = CUSTOM_NAME_MARKER
                rows.append(row)
                existing.add(key)
                changed += 1
    for name_row in load_nar_safe_ship_names():
        key = (name_row["country"], name_row["shipType"], name_row["nameUi"])
        if key in existing:
            continue
        max_id += 1
        row = [""] * header_len
        row[columns["@name"]] = str(max_id)
        row[columns["nameUi"]] = name_row["nameUi"]
        row[columns["country"]] = name_row["country"]
        row[columns["shipType"]] = name_row["shipType"]
        if marker_index is not None:
            row[marker_index] = NAR_SAFE_NAME_MARKER
        rows.append(row)
        existing.add(key)
        changed += 1
    for famous_name in load_famous_people_ship_names():
        for country in FAMOUS_NAME_COUNTRIES:
            for ship_type in FAMOUS_NAME_SHIP_TYPES:
                key = (country, ship_type, famous_name)
                if key in existing:
                    continue
                max_id += 1
                row = [""] * header_len
                row[columns["@name"]] = str(max_id)
                row[columns["nameUi"]] = famous_name
                row[columns["country"]] = country
                row[columns["shipType"]] = ship_type
                if marker_index is not None:
                    row[marker_index] = FAMOUS_NAME_MARKER
                rows.append(row)
                existing.add(key)
                changed += 1
    return join_table(prefix, rows, final_newline), changed


def custom_ship_name(ship_type: str, index: int) -> str:
    prefix = CUSTOM_NAME_PREFIXES[(index - 1) % len(CUSTOM_NAME_PREFIXES)]
    suffix = CUSTOM_NAME_SUFFIXES[((index - 1) // len(CUSTOM_NAME_PREFIXES)) % len(CUSTOM_NAME_SUFFIXES)]
    return f"{prefix} {suffix} {ship_type.upper()}{index:03d}"


def patch_resources(game_data: Path, dry_run: bool) -> dict[str, int]:
    asset = game_data / "resources.assets"
    if not asset.exists():
        raise FileNotFoundError(asset)
    env = UnityPy.load(str(asset))
    patches = {
        "params": patch_params,
        "players": patch_players,
        "parts": patch_parts,
        "partModels": patch_part_models,
        "compTypes": patch_comp_types,
        "technologies": patch_technologies,
        "missions": patch_missions,
        "aiPersonalities": patch_ai_personalities,
        "shipNames": patch_ship_names,
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
        try:
            os.replace(tmp, asset)
        except PermissionError:
            shutil.copy2(tmp, asset)
            tmp.unlink()
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


def save_port_owner_map(obj) -> dict[str, str]:
    port_owner = {}
    for province_list_index in (9, 10, 11):
        if len(obj) <= province_list_index or not isinstance(obj[province_list_index], list):
            continue
        for province in obj[province_list_index]:
            if not (isinstance(province, list) and len(province) > 12 and isinstance(province[12], list)):
                continue
            owner = province[4] if len(province) > 4 else None
            for port in province[12]:
                if isinstance(port, str) and port:
                    port_owner[port] = owner
    return port_owner


def fallback_port_for_nation(nation: str, port_owner: dict[str, str]) -> str:
    if not nation:
        return ""
    for port, owner in port_owner.items():
        if owner == nation:
            return port
    return ""


def remove_ai_build_queue_ships(obj, human_nations: set[str]) -> tuple[int, set[str]]:
    if not human_nations:
        return 0, set()
    changed = 0
    removed_ship_ids = set()
    for ship_list_index in (SAVE_SURFACE_SHIPS_INDEX, SAVE_SUBMARINES_INDEX):
        if len(obj) <= ship_list_index or not isinstance(obj[ship_list_index], list):
            continue
        kept_ships = []
        for ship in obj[ship_list_index]:
            remove_ship = (
                isinstance(ship, list)
                and len(ship) > 66
                and isinstance(ship[1], str)
                and ship[62] not in human_nations
                and ship[66] == AI_BUILD_STATUS
            )
            if remove_ship:
                removed_ship_ids.add(ship[1])
                changed += 1
            else:
                kept_ships.append(ship)
        obj[ship_list_index] = kept_ships
    return changed, removed_ship_ids


def clean_task_force_ship_refs(obj, removed_ship_ids: set[str]) -> int:
    if not removed_ship_ids or len(obj) <= SAVE_TASK_FORCES_INDEX or not isinstance(obj[SAVE_TASK_FORCES_INDEX], list):
        return 0
    changed = 0
    kept_routes = []
    for route in obj[SAVE_TASK_FORCES_INDEX]:
        if not (isinstance(route, list) and len(route) > 1 and isinstance(route[1], list)):
            kept_routes.append(route)
            continue
        original_count = len(route[1])
        route[1] = [ship_id for ship_id in route[1] if ship_id not in removed_ship_ids]
        changed += original_count - len(route[1])
        if route[1]:
            kept_routes.append(route)
        else:
            changed += 1
    obj[SAVE_TASK_FORCES_INDEX] = kept_routes
    return changed


def sanitize_task_force_routes(obj) -> int:
    if len(obj) <= SAVE_TASK_FORCES_INDEX or not isinstance(obj[SAVE_TASK_FORCES_INDEX], list):
        return 0
    known_ship_ids = set()
    for ship_list_index in (SAVE_SURFACE_SHIPS_INDEX, SAVE_SUBMARINES_INDEX):
        if len(obj) <= ship_list_index or not isinstance(obj[ship_list_index], list):
            continue
        for ship in obj[ship_list_index]:
            if isinstance(ship, list) and len(ship) > 1 and isinstance(ship[1], str):
                known_ship_ids.add(ship[1])
    changed = 0
    kept_routes = []
    for route in obj[SAVE_TASK_FORCES_INDEX]:
        if not (isinstance(route, list) and len(route) > 1 and isinstance(route[1], list)):
            kept_routes.append(route)
            continue
        original_count = len(route[1])
        seen = set()
        cleaned_ship_ids = []
        for ship_id in route[1]:
            if ship_id not in known_ship_ids or ship_id in seen:
                continue
            seen.add(ship_id)
            cleaned_ship_ids.append(ship_id)
        route[1] = cleaned_ship_ids
        changed += original_count - len(route[1])
        if route[1]:
            kept_routes.append(route)
        else:
            changed += 1
    obj[SAVE_TASK_FORCES_INDEX] = kept_routes
    return changed


def patch_save_object(obj) -> int:
    if not isinstance(obj, list) or len(obj) <= 14 or not isinstance(obj[6], list):
        return 0
    changed = 0
    players = obj[6]
    human_nations = {row[1] for row in players if isinstance(row, list) and len(row) > 52 and row[2] is True}
    port_owner = save_port_owner_map(obj)
    fallback_ports = {}
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
    queue_changes, removed_ship_ids = remove_ai_build_queue_ships(obj, human_nations)
    changed += queue_changes
    changed += clean_task_force_ship_refs(obj, removed_ship_ids)
    changed += sanitize_task_force_routes(obj)
    for ship_list_index in (SAVE_SURFACE_SHIPS_INDEX, SAVE_SUBMARINES_INDEX):
        if len(obj) <= ship_list_index or not isinstance(obj[ship_list_index], list):
            continue
        for ship in obj[ship_list_index]:
            if not (isinstance(ship, list) and len(ship) > 62):
                continue
            nation = ship[62]
            if nation not in human_nations:
                fallback = fallback_ports.get(nation)
                if fallback is None:
                    fallback = fallback_port_for_nation(nation, port_owner)
                    fallback_ports[nation] = fallback
                for field_index in SHIP_PORT_FIELDS:
                    if len(ship) <= field_index:
                        continue
                    port = ship[field_index]
                    if isinstance(port, str) and port and port_owner.get(port) in human_nations:
                        ship[field_index] = fallback
                        changed += 1
                continue
            if not (len(ship) > 77):
                continue
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
            if (
                ship_list_index == 13
                and len(ship) > 67
                and ship[66] == PLAYER_BUILD_STATUS
                and isinstance(ship[67], (int, float))
                and float(ship[67]) > PLAYER_BUILD_REMAINING_CAP_MONTHS
            ):
                old_remaining = float(ship[67])
                new_remaining = max(
                    PLAYER_BUILD_REMAINING_MIN_MONTHS,
                    min(old_remaining * PLAYER_BUILD_REMAINING_FACTOR, PLAYER_BUILD_REMAINING_CAP_MONTHS),
                )
                if new_remaining < old_remaining:
                    ship[67] = new_remaining
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
