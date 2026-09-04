import json

with open('data/equip-templates.json', 'r', encoding='utf-8') as f:
    t = json.load(f)

t['profiles']['e5.pac'] = {
    "equipId": "e5",
    "points": []
}

with open('data/equip-templates.json', 'w', encoding='utf-8') as f:
    json.dump(t, f, ensure_ascii=False, indent=1)

print("Added stub for e5.pac to profiles")
