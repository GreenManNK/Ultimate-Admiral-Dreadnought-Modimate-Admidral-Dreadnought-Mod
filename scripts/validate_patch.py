from pathlib import Path
from collections import Counter
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
        "shipyard_start": "15000000",
        "campaign_max_year": "1950",
        "cash_start_part": "500",
        "cash_start_randomness": "0",
        "ai_difficulty_easy_income_multiplier": "0.2",
        "ai_difficulty_normal_income_multiplier": "0.25",
        "ai_difficulty_hard_income_multiplier": "0.35",
        "ai_difficulty_legendary_income_multiplier": "0.5",
        "ai_difficulty_hard_tech_multiplier": "1",
        "ai_difficulty_legendary_tech_multiplier": "1",
    }
    for key, expected in required.items():
        actual = pd.get(key)
        if actual != expected:
            raise AssertionError(f"param {key}: expected {expected}, got {actual}")

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

    comp = dict_rows(texts["compTypes"])
    if any(data_name(row) and (row.get("shipTypes") or "").strip() for row in comp):
        raise AssertionError("compTypes shipTypes locks remain")

    ai = dict_rows(texts["aiPersonalities"])
    max_training = max(float(row.get("aiTrainingMod") or 0) for row in ai if data_name(row))
    aim_mods = [row.get("@name") for row in ai if data_name(row) and ("TechMod(aim_control" in (row.get("aiParams") or "") or "TechMod(aim_rangefinder" in (row.get("aiParams") or ""))]
    if max_training > 0.02 or aim_mods:
        raise AssertionError({"max_training": max_training, "aim_mods": aim_mods})

    save_status = []
    for path in sorted(SAVE_ROOT.glob("save_*.bin")):
        obj = unpack_save(path)
        for row in obj[6]:
            if isinstance(row, list) and len(row) > 52 and row[1] in MAJORS and row[2] is True:
                if float(row[20]) < 15_000_000 or float(row[52]) < 499_990_000_000:
                    raise AssertionError(f"{path.name}: hotfix floor missing: {row[1]} {row[20]} {row[52]}")
                save_status.append((path.name, row[1], row[20], row[52]))
    print(json.dumps({"ok": True, "save_status": save_status}, indent=2))


if __name__ == "__main__":
    main()
