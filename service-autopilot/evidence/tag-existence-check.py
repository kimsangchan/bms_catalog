# -*- coding: utf-8 -*-
"""쓰려는 Haystack 태그가 NEUROS 사전(haystack-tags.json)에 실제 있는지 확인."""
import json, sys

P = r"D:\_solutions\Neuros\NEUROS\backend\src\main\resources\haystack-tags.json"
d = json.load(open(P, encoding="utf-8"))
keys = {c: set(d.get(c, {})) for c in ("equip", "property", "role")}
allk = {}
for c, ks in keys.items():
    for k in ks:
        allk.setdefault(k, []).append(c)

CAND = {
 "장비(equip)": ["ahu","mau","rtu","fcu","vav","cav","airTerminalUnit","unitVent","heatPump",
   "chiller","coolingTower","cooling-tower-fan","boiler","heatExchanger","heat-recovery",
   "pump","pump-motor","booster-pump","fan","fan-motor","supply-fan","return-fan","exhaust-fan",
   "vfd","motor","damper","damper-actuator","valve","two-way-valve","three-way-valve","valve-actuator",
   "coolingCoil","heatingCoil","humidifier","filter","elec-meter","flow-meter","meter",
   "chilled-water-plant","hot-water-plant","airHandlingEquip","evaporativeCooler","dxCooling"],
 "역할(role)": ["sensor","cmd","sp","point","computed"],
 "물리량·속성(property)": ["air","water","temp","humidity","pressure","flow","power","energy",
   "current","volt","freq","speed","co2","co","voc","level","position","valve","damper","fan","pump",
   "run","enable","alarm","fault","occ","unocc","cool","heat","cooling-mode","heating-mode",
   "discharge","return-air","exhaust","outside","zone","entering","leaving","mixed","supply",
   "chilled","condenser","hot-water","cool-water","steam","static","differential","delta",
   "elec-current","elec-energy","elec-power","dewPoint","enthalpy","filter","bypass","economizer",
   "free-cooling","minVal","maxVal","effective","writable","his","cur","unit","kind","enum",
   "heatWheel","preheat","reheat","stage","runtime","efficiency","load","capacity","setback"],
}

print("=" * 78)
for grp, cands in CAND.items():
    hit, miss = [], []
    for c in cands:
        if c in allk:
            hit.append(f"{c}[{'/'.join(allk[c])}]")
        else:
            miss.append(c)
    print(f"\n## {grp}  ({len(hit)}/{len(cands)} 존재)")
    print("  있음 :", ", ".join(hit))
    print("  없음 :", ", ".join(miss) if miss else "(없음)")

# 없는 것들에 대해 유사 후보 제시
print("\n" + "=" * 78)
print("## 결손 태그의 사전 내 유사 후보")
for grp, cands in CAND.items():
    for c in cands:
        if c in allk:
            continue
        base = c.replace("-", "").lower()
        sim = [f"{cat}:{k}" for k in allk for cat in allk[k]
               if base[:4] and base[:4] in k.replace("-", "").lower()]
        print(f"  {c:22s} -> {', '.join(sorted(set(sim))[:6]) or '(유사 없음)'}")
