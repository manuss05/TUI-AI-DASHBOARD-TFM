import time

import requests

MIRRORS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
]

def query_pois(city, lat=None, lon=None):
    if lat and lon and lat != 0.0 and lon != 0.0:
        q = f"""
        [out:json][timeout:10];
        (
          node["tourism"="hotel"](around:7000, {lat}, {lon});
          node["amenity"="restaurant"](around:7000, {lat}, {lon});
          node["tourism"="attraction"](around:7000, {lat}, {lon});
          node["tourism"="museum"](around:7000, {lat}, {lon});
        );
        out count;
        """
    else:
        q = f"""
        [out:json][timeout:10];
        area["name"="{city}"]["boundary"="administrative"][admin_level=8]->.a;
        (
          node["tourism"="hotel"](area.a);
          node["amenity"="restaurant"](area.a);
          node["tourism"="attraction"](area.a);
          node["tourism"="museum"](area.a);
        );
        out count;
        """

    for mirror in MIRRORS:
        try:
            r = requests.post(mirror, data={"data": q}, headers={"User-Agent": "TFM-Investigation/1.0"}, timeout=8)
            if r.status_code == 200:
                elements = r.json().get("elements", [])
                if elements and elements[0].get("type") == "count":
                    total = elements[0]["tags"]["total"]
                    return mirror, total
        except Exception:
            continue

    # Fallback to Nominatim if Overpass fails
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": f"turismo en {city}, España", "format": "json", "limit": 10},
            headers={"User-Agent": "TFM-Investigation/1.0"},
            timeout=5
        )
        if r.status_code == 200:
            return "Nominatim_fallback", len(r.json())
    except Exception:
        pass

    return None, None

test_cities = [
    ("Madrid", 40.4168, -3.7038),
    ("Barcelona", 41.3851, 2.1734),
    ("Toledo", 39.8628, -4.0273),
    ("Sevilla", 37.3891, -5.9845),
    ("Albacete", 38.9943, -1.8585),
]

for name, lat, lon in test_cities:
    t0 = time.time()
    mirror, total = query_pois(name, lat, lon)
    dt = time.time() - t0
    print(f"City: {name:12} | Fuente: {str(mirror):30} | Total POIs: {total} | Time: {dt:.2f}s", flush=True)
