# -*- coding: utf-8 -*-
"""재추출 — 원문이 있는 모델의 포인트를 다시 뽑아 갈아끼운다.

추출기·정규화 규칙을 고치면 이미 만들어둔 모델은 옛 규칙으로 만들어진 채 남는다.
그때 이걸 돌린다. 모델의 이름·계열·분류 같은 사람이 정한 부분은 그대로 두고
포인트와 교차 대조 결과만 새로 채운다.

원문(data/raw/)이 없는 모델은 건드리지 않는다 — 지우면 복구할 수 없다.

실행
  python rebuild.py            무엇이 어떻게 바뀌는지만 보여준다
  python rebuild.py --run      실제로 갈아끼운다
"""
import collections
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
RAW = os.path.join(DATA, "raw")
sys.path.insert(0, HERE)
import crosscheck as C  # noqa: E402
import register as R  # noqa: E402
import extract as E  # noqa: E402
import schema as S  # noqa: E402


def points_of(pdf, model_id):
    """문서에서 이 모델 몫의 포인트를 가져온다.

    한 문서를 여러 모델이 나눠 쓰는 경우(-scc/-dac, -idu/-odu) 접미사로 구간을 고른다.
    """
    rows, xc, _fam = R.read(pdf)
    segs = E.split_profiles(rows)
    order = ["-scc", "-idu", "pahcmr000"], ["-dac", "-odu", "pahcms000"]
    if len(segs) == 2:
        if any(model_id.endswith(s) for s in order[0]):
            return segs[0], xc
        if any(model_id.endswith(s) for s in order[1]):
            return segs[1], xc
    return [p for s in segs for p in s], xc


def main(argv):
    run = "--run" in argv
    print("%-46s %8s → %-8s %s" % ("모델", "기존", "재추출", "교차대조"))
    print("─" * 88)
    n = 0
    for f in sorted(glob.glob(os.path.join(DATA, "models", "*.json"))):
        m = json.load(open(f, encoding="utf-8"))
        src = m.get("sourceDoc")
        pdf = os.path.join(RAW, src) if src else None
        if not pdf or not os.path.exists(pdf):
            print("%-46s %8d    원문 없음 — 건드리지 않는다" % (m["id"], len(m.get("points", []))))
            continue
        pts, xc = points_of(pdf, m["id"])
        before = len(m.get("points", []))
        mark = "" if len(pts) == before else "  ← %+d" % (len(pts) - before)
        print("%-46s %8d → %-8d %5.1f%% (%d점)%s"
              % (m["id"], before, len(pts), xc["rate"] * 100, xc["both"], mark))
        if run:
            m["points"] = [{k: p.get(k) for k in
                            ("type", "inst", "name", "unitRaw", "unit", "note",
                             "sourceFile", "sourcePage", "bacOid", "modbusRegister",
                             "modbusScaleFactor", "modbusBooleanFlag",
                             "modbusSignedFlag", "modbusOffset",
                             "modbusWritableFlag")} for p in pts]
            # 소스가 '교차 대조 불가'로 표시한 문서는 그 표시를 유지한다 —
            # 등록기와 같은 규칙을 써야 재추출이 표시를 지우지 않는다.
            why = R.unreliable_reason(src)
            m["crosscheck"] = ({"unverifiable": why} if why else
                               {"rate": xc["rate"], "both": xc["both"],
                                "diff": [[str(k[0]), k[1], a, b]
                                         for _, k, a, b in xc["diff"][:20]]})
            proto = collections.Counter(S.protocol_of(p["type"]) for p in pts)
            m["comm"] = [[k, "통합 포인트 리스트 공개", "—", "Points List"] for k in proto]
            json.dump(m, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            n += 1
    print("\n%s" % ("모델 %d건 재추출" % n if run else "(--run 을 주면 실제로 갈아끼운다)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
