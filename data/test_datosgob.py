import requests

url = "https://datos.gob.es/apidata/catalog/dataset.json"
params = {"_pageSize": 100, "_sort": "-modified"}
headers = {"Accept": "application/json", "User-Agent": "TFM-Investigation/1.0"}

r = requests.get(url, params=params, headers=headers, timeout=15)
print(f"Status: {r.status_code}")
items = r.json().get("result", {}).get("items", [])
print(f"Total datasets descargados: {len(items)}")

# Filtrado local por palabras clave
keywords = ["turismo", "hotel", "viajero", "pernoctaci", "alojamiento", "rural"]
turismo_items = []
for it in items:
    t = str(it.get("title", ""))
    d = str(it.get("description", ""))
    if any(kw in t.lower() or kw in d.lower() for kw in keywords):
        turismo_items.append(t)

print(f"Datasets de turismo encontrados en la muestra: {len(turismo_items)}")
for title in turismo_items[:5]:
    print(" -", title[:80])
