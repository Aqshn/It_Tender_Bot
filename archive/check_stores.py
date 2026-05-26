import json

with open('grouped_output2.json', encoding='utf-8') as f:
    data = json.load(f)
    print("Available stores:")
    for store in data.get('magazalar', []):
        print(f"  - {store['magaza_adi']}: {len(store['mehsullar'])} products")
