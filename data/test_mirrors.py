import time
import requests

SERVER = "https://overpass.kumi.systems/api/interpreter"

cities = [
    ("Madrid", 40.4168, -3.7038),
    ("Barcelona", 41.3851, 2.1734),
    ("Sevilla", 37.3891, -5.9845),
    ("Valencia", 39.4699, -0.3763),
    ("Bilbao", 43.2630, -2.9350),
    ("Toledo", 39.8628, -4.0273),
]

for name, lat, lon in cities:
    t0 = time.time()
    q = f"""
    [out:json][timeout:15];
    (
      node["tourism"="hotel"](around:7000, {lat}, {lon});
      node["amenity"="restaurant"](around:7000, {lat}, {lon});
      node["tourism"="attraction"](around:7000, {lat}, {lon});
      node["tourism"="museum"](around:7000, {lat}, {lon});
    );
    out count;
    """
    try:
        r = requests.post(SERVER, data={"data": q}, headers={"User-Agent": "TFM-Data/1.0"}, timeout=20)
        dt = time.time() - t0
        print(f"OK {name} -> 200 in {dt:.2f}s | Result: {r.json().get('elements')}")
    except Exception as e:
        print(f"FAIL {name} -> {e}")
    time.sleep(1.0)
