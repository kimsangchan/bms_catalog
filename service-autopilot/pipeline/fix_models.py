import json

samsung = {
 "id": "samsung-dvm-s-outdoor-unit",
 "equipId": "e5",
 "vendor": "Samsung",
 "model": "DVM S",
 "name": "DVM S Outdoor Unit",
 "cat": "HVAC.AIR.VRF",
 "tag": "vrf",
 "status": "active",
 "summary": "Samsung DVM S Outdoor Unit",
 "has": {
  "spec": False,
  "points": False
 },
 "ede": False,
 "spec": [],
 "io": [],
 "elec": None,
 "comm": []
}

lg = {
 "id": "lg-multi-v-5-outdoor-unit",
 "equipId": "e5",
 "vendor": "LG",
 "model": "Multi V 5",
 "name": "Multi V 5 Outdoor Unit",
 "cat": "HVAC.AIR.VRF",
 "tag": "vrf",
 "status": "active",
 "summary": "LG Multi V 5 Outdoor Unit",
 "has": {
  "spec": False,
  "points": False
 },
 "ede": False,
 "spec": [],
 "io": [],
 "elec": None,
 "comm": []
}

with open('data/models/samsung-dvm-s-outdoor-unit.json', 'w', encoding='utf-8') as f:
    json.dump(samsung, f, ensure_ascii=False, indent=1)

with open('data/models/lg-multi-v-5-outdoor-unit.json', 'w', encoding='utf-8') as f:
    json.dump(lg, f, ensure_ascii=False, indent=1)

print("Models fixed!")
