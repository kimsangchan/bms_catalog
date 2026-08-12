# -*- coding: utf-8 -*-
"""평면 포인트 → point-schema 구조로 옮긴다 (별칭 표를 실제로 실행하는 코드).

무엇을 하나
  data/point-schema.json 의 aliases 는 "옛 이름 → 새 경로" 대응표다. 이 모듈이
  그 표를 읽어 실제 변환을 수행한다. 표가 코드 안에 흩어져 있으면 화면·CSV·
  시뮬레이터가 각자 다르게 해석해 어긋나므로, 규칙은 사전에 두고 실행만 여기서 한다.

  ⚠ **저장된 데이터를 고치지 않는다.** 읽어서 새 모양으로 만들어 줄 뿐이다.
     일괄 이관을 할지 읽을 때 해석할지는 아직 정하지 않았다(사전 openQuestions).

두 갈래
  auto=true  (14종)  이름만 바꾼다. bacOid → bacnet.oid
  auto=false ( 5종)  **값을 보고 갈라야 한다.** 가장 큰 것이 type 이다:
                       BACnet 타입 14종 14,258 → bacnet.objectType
                       MB          8,688       → 필드 없음 (Modbus 행 표식일 뿐)
                       NV·NCI      1,372       → lon.*
                       '—'           105       → gaps (타입 미상)
                     같은 필드인데 값에 따라 네 군데로 흩어진다.

실행
  PYTHONIOENCODING=utf-8 python pointmap.py --check     전 모델 변환해 통계만
  PYTHONIOENCODING=utf-8 python pointmap.py --sample 3  변환 전후 비교
"""
import argparse
import glob
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
sys.path.insert(0, HERE)
import schema as S  # noqa: E402

SCHEMA = None


def load_schema():
    global SCHEMA
    if SCHEMA is None:
        with open(os.path.join(DATA, "point-schema.json"), encoding="utf-8") as f:
            SCHEMA = json.load(f)
    return SCHEMA


def put(rec, path, value):
    """'bacnet.oid' 같은 경로에 값을 넣는다."""
    if value in (None, "", [], {}):
        return
    parts = path.split(".")
    if len(parts) == 1:
        rec.setdefault("common", {})[parts[0]] = value
        return
    rec.setdefault("blocks", {}).setdefault(parts[0], {})[parts[1]] = value


# 단위 어휘 → 단위계. 문서가 IP/SI 를 갈라 주지 않는 옛 데이터를 배치하려면 필요하다.
#
# ⚠ 같은 단위의 **철자 변형**이 많다 — 실측 121종 중 대부분이 그것이다
#   (degC · deg C · ℃ / degF · deg F · ℉ / percent · Percentage / l/s · Lps).
#   변형을 흡수하지 않으면 7,183건이 판정 불가로 남는다.
IP_UNITS = {"°F", "F", "psi", "psig", "in.wg", "inWC", "CFM", "GPM", "ft", "in",
            "lb", "lbs", "BTU", "Btu/h", "MBh", "HP", "sq ft", "gpm", "cfm",
            "ft/min", "fpm", "ft³", "gal", "ton", "tons"}
SI_UNITS = {"°C", "℃", "C", "kPa", "Pa", "bar", "m³/h", "m3/h", "m³/s", "L/s",
            "LPM", "mm", "kg", "kW", "kWh", "m/s", "m²", "l/min", "L/min",
            "m³", "m3", "cm", "g", "J", "kJ", "MJ"}
# 어느 쪽도 아닌 중립 단위 — 양쪽에 같은 값을 적는다
NEUTRAL = {"%", "%RH", "ppm", "PPM", "Hz", "V", "A", "rpm", "RPM", "dB", "dBA",
           "s", "sec", "min", "minutes", "h", "hours", "count", "steps",
           "W", "VA", "kVA", "VAC", "VDC", "mA", "K", "MWh", "Wh", "kVAr",
           "pF", "PF", "days", "day", "cycles"}

# 철자 변형 → 대표 표기. 척도가 다른 단위는 절대 섞지 않는다(unit-schema 의 원칙 그대로).
SPELLING = {
    "degc": "°C", "deg c": "°C", "℃": "°C", "deg. c": "°C", "celsius": "°C",
    "degf": "°F", "deg f": "°F", "℉": "°F", "deg. f": "°F", "fahrenheit": "°F",
    "percent": "%", "percentage": "%", "pct": "%",
    "percentrh": "%RH", "% rh": "%RH", "%rh": "%RH", "rh%": "%RH",
    "lps": "L/s", "l/s": "L/s", "lpm": "LPM",
    "hr": "h", "hrs": "h", "hour": "h", "seconds": "s", "second": "s",
    "voltage": "V", "current": "A", "a ac": "A", "v ac": "VAC", "a dc": "A", "v dc": "VDC",
}

# 단위가 아니라 **단위 그룹명**만 적힌 것 — 문서가 실제 단위를 안 밝힌 경우다.
# kPa 인지 psi 인지 알 수 없으므로 지어내지 않는다(README 「단위 그룹명」 항목).
UNIT_GROUP = {"pressure, fluidic", "temperature, delta", "power, electrical",
              "generic", "none", "temperature", "pressure", "flow", "enthalpy",
              "power", "energy", "frequency", "—", "–", "-", "t"}


def unit_side(u):
    """단위 문자열 → 'IP' | 'SI' | 'both' | None (판정 불가)

    None 은 두 가지다 — 문서가 단위 그룹명만 준 경우(정상)와 처음 보는 표기
    (사전 보강 대상). 둘을 가르려면 unit_group() 을 함께 본다.
    """
    if not u:
        return None
    t = str(u).strip()
    t = SPELLING.get(t.lower(), t)
    if t in IP_UNITS:
        return "IP"
    if t in SI_UNITS:
        return "SI"
    if t in NEUTRAL:
        return "both"
    return None


def unit_group(u):
    """단위 그룹명만 적힌 것인가 — 그렇다면 '판정 불가'가 아니라 문서 한계다."""
    return bool(u) and str(u).strip().lower() in UNIT_GROUP


def convert(point, family=None):
    """평면 포인트 하나 → 스키마 구조. (레코드, 미해결 메모) 를 돌려준다."""
    sch = load_schema()
    aliases = sch.get("aliases") or {}
    rec = {"common": {}, "blocks": {}, "provenance": {}}
    gaps = []
    raw = {}

    ty = point.get("type")
    inst = point.get("inst")

    # ── type · inst : 값 라우팅 (auto=false) ─────────────────────────────
    if ty in S.BACNET_TYPES:
        canon = S.TYPE_ALIAS.get(ty, ty)
        put(rec, "bacnet.objectType", canon)
        if canon != ty:
            raw["type"] = ty          # 원문 표기 보존
        put(rec, "bacnet.instance", inst)
    elif ty in S.LON_TYPES:            # NV · NCI
        put(rec, "lon.direction", ty)
        put(rec, "lon.nvIndex", inst)
    elif ty in S.MODBUS_TYPES:         # MB — 행 표식이었을 뿐, 타입이 아니다
        put(rec, "modbus.address", inst)
        raw["type"] = ty
    else:                              # '—' 등 타입 미상
        gaps.append("타입 미상(원문 %r)" % ty)
        raw["type"] = ty
        if inst is not None:
            raw["inst"] = inst

    # ── 단위 : 단위계 판정 (auto=false) ──────────────────────────────────
    for src, ip_f, si_f in (("unit", "unitIP", "unitSI"),
                            ("unitRaw", "unitIPRaw", "unitSIRaw")):
        u = point.get(src)
        if not u:
            continue
        side = unit_side(u)
        if side == "IP":
            put(rec, ip_f, u)
        elif side == "SI":
            put(rec, si_f, u)
        elif side == "both":
            put(rec, ip_f, u)
            put(rec, si_f, u)
        elif unit_group(u):
            # 문서가 단위 그룹명만 줬다 — 실제 단위를 지어내지 않는다
            raw[src] = u
            gaps.append("문서가 단위 그룹명만 밝힘(%r)" % u)
        else:
            raw[src] = u
            gaps.append("단위계 판정 불가(%r)" % u)

    # ── name : LON 문서는 name 이 NV 이름이다 (auto=false) ────────────────
    nm = point.get("name")
    if nm:
        if ty in S.LON_TYPES:
            put(rec, "lon.nvName", nm)
        else:
            put(rec, "name", nm)

    # ── 나머지는 이름만 바꾼다 (auto=true) ───────────────────────────────
    for old, spec in aliases.items():
        if old in ("type", "inst", "name", "unit", "unitRaw"):
            continue
        if not isinstance(spec, dict) or not spec.get("auto"):
            continue
        v = point.get(old)
        if v in (None, "", [], {}):
            continue
        put(rec, spec["new"].split(" (")[0], v)

    # auto=false 로 남은 것 (modbusSignedFlag 등) — 정규화 후 배치
    dt = point.get("modbusSignedFlag")
    if dt:
        norm = ((sch["blocks"]["modbus"]["fields"]["dataType"].get("normalize")) or {})
        val = norm.get(str(dt), dt)
        if val in (sch["blocks"]["modbus"]["fields"]["dataType"].get("values") or []):
            put(rec, "modbus.dataType", val)
        else:
            raw["modbusSignedFlag"] = dt
            gaps.append("Modbus 데이터형 미상(%r)" % dt)

    for k in ("sourceFile", "sourcePage"):
        if point.get(k):
            rec["provenance"][k] = point[k]
    if family:
        rec["provenance"]["family"] = family
    if raw:
        rec["provenance"]["sourceColumns"] = raw
    if gaps:
        rec["provenance"]["gaps"] = gaps
    for k in ("common", "blocks", "provenance"):
        if not rec[k]:
            del rec[k]
    return rec, gaps


def run_check(sample=0):
    sch = load_schema()
    n = 0
    dest = Counter()
    gapc = Counter()
    lost = Counter()
    known = set()
    for b, spec in (sch.get("blocks") or {}).items():
        for f in (spec.get("fields") or {}):
            known.add("%s.%s" % (b, f))
    for f in (sch.get("common") or {}):
        known.add(f)

    shown = 0
    for path in sorted(glob.glob(os.path.join(DATA, "models", "*.json"))):
        with open(path, encoding="utf-8") as fp:
            m = json.load(fp)
        for p in (m.get("points") or []):
            n += 1
            rec, gaps = convert(p)
            for blk, fields in (rec.get("blocks") or {}).items():
                for k in fields:
                    dest["%s.%s" % (blk, k)] += 1
            for k in (rec.get("common") or {}):
                dest[k] += 1
            for g in gaps:
                gapc[g.split("(")[0].strip()] += 1
            # 원본에 있었는데 어디에도 안 들어간 필드
            placed = set()
            for blk, fields in (rec.get("blocks") or {}).items():
                placed |= {"%s.%s" % (blk, k) for k in fields}
            placed |= set((rec.get("common") or {}))
            placed |= set((rec.get("provenance") or {}))
            for k, v in p.items():
                if v in (None, "", [], {}):
                    continue
                if k in ("type", "inst", "name", "unit", "unitRaw"):
                    continue
                spec = (sch.get("aliases") or {}).get(k)
                if not spec:
                    lost[k] += 1
            if sample and shown < sample and rec.get("blocks"):
                print("\n── 변환 예 %d ──" % (shown + 1))
                print("  전: %s" % json.dumps(p, ensure_ascii=False)[:200])
                print("  후: %s" % json.dumps(rec, ensure_ascii=False, indent=1)[:600])
                shown += 1

    print("\n포인트 %d건 변환" % n)
    print("\n들어간 자리 (상위 20)")
    for k, v in dest.most_common(20):
        print("   %-26s %6d" % (k, v))
    if gapc:
        print("\n미해결 (gaps 로 기록)")
        for k, v in gapc.most_common():
            print("   %-26s %6d" % (k, v))
    if lost:
        print("\n⚠ 별칭 표에 없어 갈 곳이 없는 필드")
        for k, v in lost.most_common():
            print("   %-26s %6d" % (k, v))
    else:
        print("\n별칭 표에 없어 유실되는 필드: 없음")
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description="평면 포인트 → point-schema 구조")
    ap.add_argument("--check", action="store_true", help="전 모델 변환해 통계")
    ap.add_argument("--sample", type=int, default=0, help="변환 전후 예 N건")
    a = ap.parse_args(argv)
    if a.check or a.sample:
        return run_check(a.sample)
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
