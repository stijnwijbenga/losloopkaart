#!/usr/bin/env python3
"""Geocodeert de Zwolse hondenlosloopterreinen via Nominatim en schrijft zwolle_honden.json."""

import json, time, re, sys
import requests

HEADERS = {"User-Agent": "LosloopkaartApp/1.0 (persoonlijk gebruik)"}

LOCATIES = [
    # Aa-landen
    {"wijk":"Aa-landen","buurt":"Aa-landen Midden","locatie":"Krammer"},
    {"wijk":"Aa-landen","buurt":"Aa-landen Midden","locatie":"Grevelingen"},
    {"wijk":"Aa-landen","buurt":"Aa-landen Noord","locatie":"Tjonger"},
    {"wijk":"Aa-landen","buurt":"Aa-landen Noord","locatie":"Park Aa-landen Noord"},
    {"wijk":"Aa-landen","buurt":"Aa-landen Zuid","locatie":"Kromme Rijn"},
    # Assendorp
    {"wijk":"Assendorp","buurt":"Pierik","locatie":"Mimosastraat"},
    {"wijk":"Assendorp","buurt":"Wezenlanden","locatie":"Park de Wezenlanden"},
    # Berkum
    {"wijk":"Berkum","buurt":"Berkum","locatie":"Maatgravenweg"},
    {"wijk":"Berkum","buurt":"Berkum","locatie":"Maatgravendijk"},
    {"wijk":"Berkum","buurt":"Berkum","locatie":"Vegtlusterbos"},
    {"wijk":"Berkum","buurt":"Berkum","locatie":"Leeghwaterlaan"},
    # Binnenstad
    {"wijk":"Binnenstad","buurt":"Noordereiland","locatie":"Nijkerkenbolwerk"},
    # Diezerpoort
    {"wijk":"Diezerpoort","buurt":"Hogenkamp","locatie":"Pieter Steynstraat"},
    {"wijk":"Diezerpoort","buurt":"Hogenkamp","locatie":"Middelweg"},
    {"wijk":"Diezerpoort","buurt":"Hogenkamp","locatie":"Ruusbroecstraat"},
    {"wijk":"Diezerpoort","buurt":"Meppelerstraatweg Zuid","locatie":"Meppelerstraatweg"},
    # Holtenbroek
    {"wijk":"Holtenbroek","buurt":"Holtenbroek 1 en 2","locatie":"Klooienberglaan"},
    {"wijk":"Holtenbroek","buurt":"Holtenbroek 2","locatie":"Beethovenlaan"},
    # Ittersum
    {"wijk":"Ittersum","buurt":"Oude Mars","locatie":"De Mars"},
    {"wijk":"Ittersum","buurt":"Gerenlanden","locatie":"Timmermeesterslaan"},
    {"wijk":"Ittersum","buurt":"Ittersumerbroek","locatie":"Staatssecretarislaan"},
    # Kamperpoort-Veerallee
    {"wijk":"Kamperpoort-Veerallee","buurt":"Kamperpoort","locatie":"Katerdijk"},
    {"wijk":"Kamperpoort-Veerallee","buurt":"Veerallee","locatie":"Rijksweg A28"},
    # Schelle
    {"wijk":"Schelle","buurt":"Schellerlanden","locatie":"Schellerpark"},
    {"wijk":"Schelle","buurt":"Schellerhoek","locatie":"Jofferenlaan"},
    {"wijk":"Schelle","buurt":"Schellerhoek","locatie":"Grenspad"},
    {"wijk":"Schelle","buurt":"Schellerhoek","locatie":"Grenslaan"},
    {"wijk":"Schelle","buurt":"Oldenelerbroek","locatie":"Oldeneelweg"},
    {"wijk":"Schelle","buurt":"Schellerbroek","locatie":"Wibergstraat"},
    {"wijk":"Schelle","buurt":"Katerveer-Engelse Werk","locatie":"Spoolderbos"},
    # Stadshagen
    {"wijk":"Stadshagen","buurt":"Breecamp","locatie":"Sportlaan"},
    {"wijk":"Stadshagen","buurt":"Werkeren","locatie":"Oude Wetering"},
    {"wijk":"Stadshagen","buurt":"Frankhuis","locatie":"Twistvlietweg"},
    {"wijk":"Stadshagen","buurt":"Frankhuis","locatie":"Frankhuisweg"},
    {"wijk":"Stadshagen","buurt":"Mastenbroek","locatie":"Stadsbroekpad"},
    {"wijk":"Stadshagen","buurt":"Milligen","locatie":"Milligerlaan"},
    {"wijk":"Stadshagen","buurt":"Milligen","locatie":"Lisdodde"},
    {"wijk":"Stadshagen","buurt":"Schoonhorst","locatie":"Hasselterdijk"},
    # Vechtlanden
    {"wijk":"Vechtlanden","buurt":"Langenholte","locatie":"Brinkhoekweg"},
    # Westenholte
    {"wijk":"Westenholte","buurt":"Westenholte Stins","locatie":"Stinspark"},
    {"wijk":"Westenholte","buurt":"Vreugderijk","locatie":"Zalkerdijk"},
    {"wijk":"Westenholte","buurt":"Oud-Westenholte","locatie":"Papaverweg"},
    # Wipstrik
    {"wijk":"Wipstrik","buurt":"Wipstrik-Zuid","locatie":"Evertsenstraat"},
    {"wijk":"Wipstrik","buurt":"Wipstrik-Zuid","locatie":"Weteringpark"},
]

def geocode(query):
    url = "https://nominatim.openstreetmap.org/search"
    resp = requests.get(url, params={
        "q": query, "countrycodes": "nl", "format": "json", "limit": 1
    }, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data:
        return float(data[0]["lat"]), float(data[0]["lon"])
    return None, None

resultaten = []
for i, loc in enumerate(LOCATIES, 1):
    query = f"{loc['locatie']}, Zwolle, Nederland"
    lat, lon = geocode(query)
    slug = re.sub(r"[^a-z0-9]+", "-", loc["locatie"].lower()).strip("-")
    entry = {
        "slug": f"zwolle-{slug}",
        "naam": loc["locatie"],
        "buurt": loc["buurt"],
        "wijk": loc["wijk"],
        "plaats": "Zwolle",
        "provincie": "Overijssel",
        "type": "losloopterrein",
        "lat": lat,
        "lon": lon,
        "url": "https://www.zwolle.nl/hondenkaart",
    }
    status = f"✓ ({lat:.4f}, {lon:.4f})" if lat else "✗ niet gevonden"
    print(f"[{i:2}/{len(LOCATIES)}] {loc['locatie']:35} {status}")
    resultaten.append(entry)
    time.sleep(1.1)

output = "zwolle_honden.json"
with open(output, "w", encoding="utf-8") as f:
    json.dump(resultaten, f, ensure_ascii=False, indent=2)

gevonden = sum(1 for r in resultaten if r["lat"])
print(f"\nKlaar: {gevonden}/{len(resultaten)} locaties gevonden → {output}")
