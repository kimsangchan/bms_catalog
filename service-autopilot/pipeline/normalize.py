# -*- coding: utf-8 -*-
"""정규화 — 추출 직후 데이터를 다듬는다. (추출 → 정규화 → 검증 → 적재)

검증 게이트가 잡아낸 것을 자동으로 고치는 자리다. 고칠 수 없는 건 그대로 두고
검증이 다시 걸리게 한다 — 조용히 감추지 않는다.

  1) 표 머리글·이어짐 행이 포인트로 섞인 것 제거
  2) 한 모델 안에 서로 다른 장치(실내기/실외기 등)가 섞여 인스턴스가 중복되면 분리
  3) 이름 공백 정리
"""
import json, os, re, sys, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
sys.path.insert(0, HERE)
import schema as S  # noqa: E402

# 포인트가 아니라 표 구조물인 행.
# **줄 전체가 그 머리글일 때만** 지운다. 접두 일치로 두었더니 'Unit Average Line
# Current'·'Unit Power Consumption'이 머리글 'Units'로 오인돼 지워졌다. 실제 포인트
# 이름에는 Description·Configuration 같은 단어가 얼마든지 들어갈 수 있다.
JUNK = re.compile(
    r"^\s*(\(continued\)|object\s*name|objectname|description|register\s*type|"
    r"register\s*(value|address)|valid\s*range|object\s*(identifier|states)|configuration|"
    r"dependency|analog\s+(inputs?|outputs?|values?)|binary\s+(inputs?|outputs?|values?)|"
    r"multi-?state\s+\w+|holding\s+registers?|modbus|units?|point\s*name|"
    r"network\s+variable\s+\w+|snvt\w*|nv\s*#|diagnostic\s+name)"
    r"(\s*\(continued\))?\s*$", re.I)
SPLITMARK = re.compile(r"^──|^─{2,}|이하 실외기|이하 ODU", re.U)


def clean_points(pts):
    out, dropped = [], []
    for p in pts:
        n = re.sub(r"\s+", " ", (p.get("name") or "")).strip()
        if not n or JUNK.match(n) or SPLITMARK.search(n) or len(n) < 3:
            dropped.append(p)
            continue
        p = dict(p, name=n)
        # 상태 설명이 단위 자리에 들어온 경우 — 비고로 옮기고 단위는 비운다
        if S.is_state_text(p.get("unitRaw")):
            note = p.get("note") or ""
            st = str(p["unitRaw"]).strip()
            p["note"] = (note if st in note else (note + " · " + st if note else st))[:240]
            p["unitRaw"], p["unit"] = None, None
        out.append(p)
    return out, dropped


def split_devices(m):
    """인스턴스가 중복되면 원본 순서상의 구분 표식으로 장치를 나눈다."""
    pts = m.get("points", [])
    keys = collections.Counter((p["type"], p.get("inst")) for p in pts)
    if not any(v > 1 for v in keys.values()):
        return None
    # 구분 표식(── …) 위치로 자른다
    cut = None
    for i, p in enumerate(m.get("_rawPoints", pts)):
        if SPLITMARK.search(p.get("name") or ""):
            cut = i
            break
    if cut is None:
        return None
    raw = m.get("_rawPoints", pts)
    a, _ = clean_points(raw[:cut])
    b, _ = clean_points(raw[cut + 1:])
    if not a or not b:
        return None
    return a, b


def run():
    changed, report = [], []
    for f in sorted(glob.glob(os.path.join(DATA, "models", "*.json"))):
        m = json.load(open(f, encoding="utf-8"))
        before = len(m.get("points", []))
        m.setdefault("_rawPoints", list(m.get("points", [])))
        sp = split_devices(m)
        if sp:
            a, b = sp
            # 실내기 / 실외기로 분리 — 두 번째 모델 파일을 새로 만든다
            base = dict(m)
            base["points"] = a
            base["name"] = m["name"] + " — 실내기(IDU)"
            base["id"] = m["id"] + "-idu"
            sub = dict(m)
            sub["points"] = b
            sub["name"] = m["name"] + " — 실외기(ODU)"
            sub["id"] = m["id"] + "-odu"
            sub["summary"] = m.get("summary", "") + " (실외기 오브젝트)"
            for r in (base, sub):
                r.pop("_rawPoints", None)
                json.dump(r, open(os.path.join(DATA, "models", r["id"] + ".json"),
                                  "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            os.remove(f)
            report.append("분리  %s → %s(%d점) + %s(%d점)  [인스턴스 중복 해소]"
                          % (m["id"], base["id"], len(a), sub["id"], len(b)))
            changed.append(m["id"])
            continue
        pts, dropped = clean_points(m.get("points", []))
        moved = sum(1 for a, b in zip(m.get("points", []), pts)
                    if a.get("unitRaw") != b.get("unitRaw"))
        m["points"] = pts
        m.pop("_rawPoints", None)
        json.dump(m, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        if len(pts) != before or moved:
            bits = []
            if dropped:
                bits.append("표 구조물 %d행 제거" % len(dropped))
            if moved:
                bits.append("상태 설명 %d건을 단위→비고로" % moved)
            report.append("정리  %-42s %d점 → %d점 (%s)"
                          % (m["id"], before, len(pts), ", ".join(bits)))
            changed.append(m["id"])
    return report


if __name__ == "__main__":
    rep = run()
    print("\n".join(rep) if rep else "바꿀 것 없음")
    print("─" * 72)
    print("정규화 완료 — %d건 변경" % len(rep))
