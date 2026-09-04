import json

with open('data/spec-map.json', 'r', encoding='utf-8') as f:
    mapping = json.load(f)

mapping['Samsung_DVM_S_Data_Book.pdf'] = ['samsung-dvm-s-outdoor-unit']
mapping['LG_Multi_V_5_Engineering_Data_Book.pdf'] = ['lg-multi-v-5-outdoor-unit']

with open('data/spec-map.json', 'w', encoding='utf-8') as f:
    json.dump(mapping, f, indent=1, ensure_ascii=False)
print('Mapping updated!')
