from pathlib import Path
from collections import Counter, defaultdict
import csv, io, re, json

try:
    import UnityPy
    import msgpack
    import lz4.block
except Exception as exc:
    raise SystemExit(f"Missing dependency: {exc}")

GAME_DATA = Path(r"F:\SteamLibrary\steamapps\common\Ultimate Admiral Dreadnoughts\Ultimate Admiral Dreadnoughts_Data")
SAVE_ROOT = Path.home() / r"AppData/LocalLow/Game Labs/Ultimate Admiral Dreadnoughts"
MAJORS = {"britain","france","germany","usa","russia","italy","austria","japan","spain","china"}
PLAYER_ACCURACY_TECH = {
    "aim_control_end": 14,
    "aim_rangefinder_end": 13,
    "tactics_tactics_end": 21,
    "tactics_comm_end": 24,
}


def get_text(d):
    s = d.m_Script
    return s.decode("utf-8-sig", "replace") if isinstance(s, bytes) else s


def dict_rows(text):
    lines = text.splitlines()
    idx = next(i for i, line in enumerate(lines) if line.startswith("@name,"))
    return list(csv.DictReader(io.StringIO("\n".join(lines[idx:]))))


def data_name(row):
    name = (row.get("@name") or "").strip()
    return bool(name) and not name.startswith("#") and name != "default"


def unpack_save(path):
    code, data = msgpack.unpackb(path.read_bytes(), raw=True, ext_hook=lambda c, d: (c, d))
    if code != 99 or data[0] != 0xD2:
        raise ValueError(f"{path.name}: unexpected wrapper")
    size = int.from_bytes(data[1:5], "big", signed=True)
    dec = lz4.block.decompress(data[5:], uncompressed_size=size)
    return msgpack.unpackb(dec, raw=False, strict_map_key=False)


def load_saved_hull_tonnage_targets():
    path = Path(__file__).resolve().parents[1] / "data" / "hull_tonnage_max_400k.csv"
    targets = defaultdict(float)
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            targets[row["name"]] = max(targets[row["name"]], float(row["tonnageMax"]))
    return targets


def main():
    env = UnityPy.load(str(GAME_DATA / "resources.assets"))
    texts = {}
    for obj in env.objects:
        if obj.type.name == "TextAsset":
            d = obj.read()
            if d.m_Name in {"params", "parts", "players", "compTypes", "technologies", "aiPersonalities"}:
                texts[d.m_Name] = get_text(d)

    params = dict_rows(texts["params"])
    pd = {row.get("@name"): row.get("value") for row in params if row.get("@name")}
    required = {
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
        "fleet_generation_chance": "5",
    }
    for key, expected in required.items():
        actual = pd.get(key)
        if actual != expected:
            raise AssertionError(f"param {key}: expected {expected}, got {actual}")

    economy_required = {
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
    }
    for key, expected in economy_required.items():
        actual = pd.get(key)
        if actual != expected:
            raise AssertionError(f"economy param {key}: expected {expected}, got {actual}")

    parts = dict_rows(texts["parts"])
    country_locked = 0
    needunlock = 0
    need = Counter()
    ids = []
    for row in parts:
        if not data_name(row):
            continue
        ids.append(row.get("@name"))
        typ = (row.get("type") or "").strip()
        param = row.get("param") or ""
        if (row.get("countries") or "").strip():
            country_locked += 1
        needunlock += param.count("needunlock(")
        need[typ] += len(re.findall(r"(?<![A-Za-z_])need\(", param))
    if country_locked or needunlock or need["tower_main"] or need["tower_sec"] or need["funnel"]:
        raise AssertionError({"country_locked": country_locked, "needunlock": needunlock, "need": dict(need)})

    hulls = [row for row in parts if data_name(row) and (row.get("type") or "").strip() == "hull"]
    hull_bad_tonnage = []
    hull_values = {}
    for row in hulls:
        try:
            ton_min = float(row.get("tonnageMin") or 0)
            ton_max = float(row.get("tonnageMax") or 0)
        except ValueError:
            hull_bad_tonnage.append((row.get("@name"), row.get("tonnageMin"), row.get("tonnageMax")))
            continue
        if ton_max < ton_min:
            hull_bad_tonnage.append((row.get("@name"), ton_min, ton_max))
        hull_values.setdefault(row.get("@name"), []).append(ton_max)
    if len(hulls) != 518 or hull_bad_tonnage:
        raise AssertionError({"hull_count": len(hulls), "bad_tonnage": hull_bad_tonnage[:10]})
    representative_hull_values = {
        "bb_7_bismarck": [400000.0],
        "bb_6": [400000.0],
        "bb_6_iowa": [392400.0],
        "bb_5": [345600.0],
        "dd_1": [3960.0],
        "tb_lowbow": [1800.0],
        "tr": [72000.0],
    }
    for name, expected in representative_hull_values.items():
        actual = hull_values.get(name)
        if actual != expected:
            raise AssertionError(f"hull tonnage {name}: expected {expected}, got {actual}")

    comp = dict_rows(texts["compTypes"])
    if any(data_name(row) and (row.get("shipTypes") or "").strip() for row in comp):
        raise AssertionError("compTypes shipTypes locks remain")

    ai = dict_rows(texts["aiPersonalities"])
    ai_caps = {
        "aiTechMod": 0.2,
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
    ai_failures = {}
    for col, cap in ai_caps.items():
        values = [float(row.get(col) or 0) for row in ai if data_name(row)]
        actual = max(values or [0])
        if actual > cap:
            ai_failures[col] = actual
    tech_mods = [row.get("@name") for row in ai if data_name(row) and "TechMod(" in (row.get("aiParams") or "")]
    if ai_failures or tech_mods:
        raise AssertionError({"ai_caps": ai_failures, "tech_mods": tech_mods})

    save_status = []
    saved_hull_targets = load_saved_hull_tonnage_targets()
    for path in sorted(SAVE_ROOT.glob("save_*.bin")):
        obj = unpack_save(path)
        player_rows = [row for row in obj[6] if isinstance(row, list) and len(row) > 52]
        names = [row[1] for row in player_rows]
        duplicate_nations = [name for name, count in Counter(names).items() if count > 1]
        if duplicate_nations:
            raise AssertionError(f"{path.name}: duplicate player rows: {duplicate_nations}")
        for row in obj[6]:
            if isinstance(row, list) and len(row) > 52 and row[1] in MAJORS and row[2] is True:
                if float(row[20]) < 15_000_000 or float(row[52]) < 499_990_000_000:
                    raise AssertionError(f"{path.name}: hotfix floor missing: {row[1]} {row[20]} {row[52]}")
                tech = row[41] if len(row) > 41 and isinstance(row[41], dict) else {}
                for key, expected in PLAYER_ACCURACY_TECH.items():
                    if tech.get(key, -1) < expected:
                        raise AssertionError(f"{path.name}: player accuracy tech missing: {row[1]} {key}={tech.get(key)}")
                save_status.append((path.name, row[1], row[20], row[52]))
            elif isinstance(row, list) and len(row) > 52 and row[2] is not True:
                if float(row[20]) > 50_000 or float(row[52]) > 5_000_000_000:
                    raise AssertionError(f"{path.name}: AI cap exceeded: {row[1]} {row[20]} {row[52]}")
        player_nations = {row[1] for row in obj[6] if isinstance(row, list) and len(row) > 52 and row[2] is True}
        for ship_list_index in (13, 14):
            for ship in obj[ship_list_index]:
                if not (isinstance(ship, list) and len(ship) > 77 and len(ship) > 62):
                    continue
                if ship_list_index == 13 and ship[62] in player_nations and len(ship) > 15:
                    target = saved_hull_targets.get(ship[10])
                    if target and float(ship[15]) + 1e-3 < target:
                        raise AssertionError(f"{path.name}: player saved hull tonnage low: {ship[62]} {ship[60] if len(ship) > 60 else ship[1]} {ship[10]} {ship[15]} < {target}")
                if ship[62] in player_nations and float(ship[77]) < 100:
                    raise AssertionError(f"{path.name}: player ship training below 100: {ship[62]} {ship[60] if len(ship) > 60 else ship[1]} {ship[77]}")
                if ship_list_index == 13 and ship[62] in player_nations and isinstance(ship[28], int) and ship[28] < 4:
                    raise AssertionError(f"{path.name}: player surface crew level below 4: {ship[62]} {ship[60] if len(ship) > 60 else ship[1]} {ship[28]}")
    print(json.dumps({"ok": True, "save_status": save_status}, indent=2))


if __name__ == "__main__":
    main()
