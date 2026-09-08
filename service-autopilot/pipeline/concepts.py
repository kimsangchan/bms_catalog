# -*- coding: utf-8 -*-
"""개념 사전 손질 — data/point-concepts.json

  PYTHONIOENCODING=utf-8 python concepts.py            지금 상태를 본다
  PYTHONIOENCODING=utf-8 python concepts.py --sync      aliases·usedIn 을 되맞춘다

왜 있나
  게이트(test_concept_aliases_cover_the_names_rows_actually_use)만 있고 손질 도구가
  없으면 사람이 JSON 을 손으로 고치게 된다. aliases 와 usedIn 은 **템플릿에서 파생되는
  값**이라 기계가 맞춰야 한다 — 사전의 뜻(ko·group·기본 종류·Haystack)만 사람이 쓴다.

  ⚠ --sync 는 **덧붙이기만 한다.** 이름을 지우지 않는다 —
    '이 계열은 이렇게 부른다' 는 기록이고, 매칭 규칙이 그 이름에 매여 있다.
    행에서 사라진 표기는 `--sync --prune` 으로만 지운다(그때도 무엇을 지우는지 찍는다).
"""
import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CP = os.path.join(DATA, "point-concepts.json")
TP = os.path.join(DATA, "equip-templates.json")


def load():
    doc = json.load(io.open(CP, encoding="utf-8"),
                    object_pairs_hook=collections.OrderedDict)
    tpl = json.load(io.open(TP, encoding="utf-8"),
                    object_pairs_hook=collections.OrderedDict)
    return doc, tpl


def main(argv):
    doc, tpl = load()
    con = doc["concepts"]
    groups = set(doc["groups"])

    used = collections.defaultdict(list)   # cid → [pid]
    names = collections.defaultdict(list)  # cid → [표기]
    orphan, badgrp = [], []
    for pid, p in tpl["profiles"].items():
        for r in p.get("templatePoints") or []:
            cid = r.get("concept")
            if cid not in con:
                orphan.append("%s/%s → %r" % (pid, r.get("name"), cid))
                continue
            if r.get("group") not in groups:
                badgrp.append("%s/%s → %r" % (pid, r.get("name"), r.get("group")))
            if pid not in used[cid]:
                used[cid].append(pid)
            if r["name"] not in names[cid]:
                names[cid].append(r["name"])

    addA = addU = 0
    prune = "--prune" in argv
    dropped = []
    for cid, c in con.items():
        have = list(c.get("aliases") or [])
        for n in names.get(cid, []):
            if n not in have:
                have.append(n)
                addA += 1
        if prune:
            gone = [n for n in have if n not in names.get(cid, [])]
            if gone:
                dropped += ["%s: %s" % (cid, n) for n in gone]
                have = [n for n in have if n in names.get(cid, [])]
        c["aliases"] = have
        u = used.get(cid, [])
        if list(c.get("usedIn") or []) != u:
            c["usedIn"] = u
            addU += 1

    print("개념 %d · 묶음 %d" % (len(con), len(groups)))
    print("aliases 보탤 것 %d · usedIn 바뀔 것 %d" % (addA, addU))
    if orphan:
        print("⚠ 사전에 없는 개념을 가리키는 행 %d개:" % len(orphan))
        for x in orphan[:10]:
            print("    %s" % x)
        print("   → 사전에 **먼저 등재**하라(규칙 5.2). --sync 가 만들어 주지 않는다 —"
              " 뜻·묶음·근거는 사람이 정해야 한다.")
    if badgrp:
        print("⚠ 사전에 없는 묶음 %d개: %s" % (len(badgrp), badgrp[:5]))
    if dropped:
        print("지울 표기 %d개: %s" % (len(dropped), dropped[:10]))
    unused = [cid for cid in con if not used.get(cid)]
    if unused:
        print("· 아무 행도 안 쓰는 개념 %d개: %s" % (len(unused), unused[:8]))

    if "--sync" not in argv:
        print("(미리보기다. 되맞추려면 --sync)")
        return 1 if (orphan or badgrp) else 0
    if orphan or badgrp:
        print("→ 먼저 등재하지 않으면 되맞추지 않는다.")
        return 1
    with io.open(CP, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("→ %s" % os.path.relpath(CP, HERE))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
