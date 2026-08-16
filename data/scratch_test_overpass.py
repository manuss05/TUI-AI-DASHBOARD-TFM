import time
import requests

SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter"
]

# Test 1: Around coordinates (Toledo: 39.8628, -4.0273)
def test_around(lat, lon, server):
    t0 = time.time()
    q = f"""
    [out:json][timeout:15];
    (
      node["tourism"="hotel"](around:8000, {lat}, {lon});
      node["amenity"="restaurant"](around:8000, {lat}, {lon});
      node["tourism"="attraction"](around:8000, {lat}, {lon});
      node["tourism"="museum"](around:8000, {lat}, {lon});
    );
    out count;
    """
    try:
        r = requests.post(server, data={"data": q}, headers={"User-Agent": "TFM-Data/1.0"}, timeout=15)
        dt = time.time() - t0
        print(f"Around ({lat},{lon}) -> {server} -> Status {r.status_code} in {dt:.2f}s | Result: {r.json().get('elements')}")
    except Exception as e:
        print(f"Around ({lat},{lon}) -> {server} -> Error: {e}")

# Test 2: Area filtered by Spain
def test_spain_area(city, server):
    t0 = time.time()
    q = f"""
    [out:json][timeout:15];
    area["ISO3166-1"="ES"]->.spain;
    area["name"="{city}"](area.spain)->.a;
    (
      node["tourism"="hotel"](area.a);
      node["amenity"="restaurant"](area.a);
      node["tourism"="attraction"](area.a);
      node["tourism"="museum"](area.a);
    );
    out count;
    """
    try:
        r = requests.post(server, data={"data": q}, headers={"User-Agent": "TFM-Data/1.0"}, timeout=15)
        dt = time.time() - t0
        print(f"Spain Area ({city}) -> {server} -> Status {r.status_code} in {dt:.2f}s | Result: {r.json().get('elements')}")
    except Exception as e:
        print(f"Spain Area ({city}) -> {server} -> Error: {e}")

print("--- Testing Around Coordinates ---")
for s in SERVERS:
    test_around(39.8628, -4.0273, s) # Toledo

print("\n--- Testing Spain Area Filter ---")
for s in SERVERS:
    test_spain_area("Toledo", s)
