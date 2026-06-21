#!/usr/bin/env python3
"""
scrape_doggydating.py
----------------------
Haalt alle losloopgebieden van doggydating.com op: naam, plaats, provincie,
type, kenmerken zoals zwemwater, coordinaten, de VOLLEDIGE beschrijftekst
(niet de afgekapte SEO-samenvatting), alle doorklik-links die in die tekst
staan (bv. naar Staatsbosbeheer/gemeente/Natuurmonumenten), een ruwe
seizoensregel-signaalvlag, en een foto. Schrijft dit weg naar een JSON-
bestand dat de viewer-app (losloopkaart-site/index.html) kan inladen.

robots.txt van doggydating.com staat crawlen volledig toe (User-agent: *,
Disallow: <leeg>). Dit script is desondanks bewust traag en stuurt een
herkenbare User-Agent, uit respect voor een site met weinig personeel.

Gebruik:
    pip install requests beautifulsoup4 lxml --break-system-packages
    python scrape_doggydating.py
    python scrape_doggydating.py --limit 20          # snelle test op 20 gebieden
    python scrape_doggydating.py --delay 1.0         # nog rustiger aan
    python scrape_doggydating.py --output data.json  # andere bestandsnaam

Output: losloopgebieden.json (standaard), te openen via de viewer-app.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE = "https://www.doggydating.com"
SITEMAP_INDEX = f"{BASE}/sitemap_index.xml"
LISTING_BASE = f"{BASE}/hondenlosloopgebied/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PersoonlijkeLosloopTool/1.0; "
        "eigen gebruik, niet commercieel; contact via doggydating.com/contact)"
    )
}

# Vaste lijst NL provincies, gebruikt als anker om "Plaats, Provincie" te
# herkennen op de overzichtspagina's (de tekst staat los van de titel-link,
# dus we matchen op een bekend eindwoord in plaats van op CSS-classes -
# dat blijft werken ook als het thema/template ooit verandert).
PROVINCIES = [
    "Groningen", "Friesland", "Drenthe", "Overijssel", "Flevoland",
    "Gelderland", "Utrecht", "Noord-Holland", "Zuid-Holland", "Zeeland",
    "Noord-Brabant", "Limburg",
]
PROVINCIE_RE = re.compile(
    r"^(?P<plaats>.+?),\s*(?P<provincie>" + "|".join(PROVINCIES) + r")\s*$",
    re.IGNORECASE,
)

# Bekende type- en kenmerk-tags (alt-tekst van de icoontjes op detailpaginas)
TYPES = {"natuurgebied", "park", "strand", "hondenspeeltuin"}
KENMERKEN = {
    "zwemwater", "horeca", "omheining", "wandelroutes",
    "rolstoelvriendelijk", "ruiterpaden", "mtb",
}

# Herkent datums als "15 april" of "1 oktober" in lopende tekst - gebruikt
# als (ruwe) seinwacht: ligt er een datum/periode-vermelding in de officiele
# omschrijving van een gebied met zwemwater? Geen garantie dat dit specifiek
# over zwemmen gaat (vaak gaat het over het algemene losloop-seizoen, wat in
# de praktijk meestal ook het zwem-seizoen bepaalt) - dus altijd zelf checken,
# dit is een hint om te weten WELKE gebieden de moeite waard zijn om na te
# kijken, niet een betrouwbare uitspraak over de regels zelf.
MAAND_RE = re.compile(
    r"\b(januari|februari|maart|april|mei|juni|juli|augustus|"
    r"september|oktober|november|december)\b",
    re.IGNORECASE,
)


def get(session: requests.Session, url: str, delay: float) -> requests.Response | None:
    try:
        resp = session.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        time.sleep(delay)
        return resp
    except requests.RequestException as e:
        print(f"  [WAARSCHUWING] kon {url} niet ophalen: {e}", file=sys.stderr)
        return None


def get_all_area_urls(session: requests.Session, delay: float) -> list[str]:
    """Haalt de volledige lijst losloopgebied-URLs uit de XML-sitemap."""
    print("Sitemap-index ophalen...")
    resp = get(session, SITEMAP_INDEX, delay)
    if resp is None:
        sys.exit("Kon sitemap_index.xml niet ophalen, stoppen.")

    soup = BeautifulSoup(resp.content, "xml")
    losloop_sitemap = None
    for loc in soup.find_all("loc"):
        if "losloopgebieden-sitemap" in loc.text:
            losloop_sitemap = loc.text.strip()
            break
    if not losloop_sitemap:
        sys.exit("Geen losloopgebieden-sitemap gevonden in sitemap_index.xml")

    print(f"Losloopgebieden-sitemap ophalen: {losloop_sitemap}")
    resp = get(session, losloop_sitemap, delay)
    if resp is None:
        sys.exit("Kon losloopgebieden-sitemap.xml niet ophalen, stoppen.")

    soup = BeautifulSoup(resp.content, "xml")
    urls = []
    for loc in soup.find_all("loc"):
        url = loc.text.strip()
        # de overzichtspagina zelf (zonder slug) overslaan
        if url.rstrip("/").endswith("/hondenlosloopgebied"):
            continue
        urls.append(url)
    print(f"  -> {len(urls)} gebieden gevonden in de sitemap")
    return urls


def get_plaats_provincie_per_slug(session: requests.Session, delay: float) -> dict[str, tuple[str, str]]:
    """
    Doorloopt de gepagineerde overzichtspagina's en koppelt elke gebied-slug
    aan (plaats, provincie). Dit staat namelijk niet expliciet op de
    detailpagina zelf, wel duidelijk op de kaartjes in het overzicht.
    """
    result: dict[str, tuple[str, str]] = {}
    page = 1
    while True:
        url = LISTING_BASE if page == 1 else f"{LISTING_BASE}page/{page}/"
        print(f"Overzichtspagina {page} ophalen...")
        resp = get(session, url, delay)
        if resp is None:
            break

        soup = BeautifulSoup(resp.text, "lxml")

        # alle links naar detailpaginas, op volgorde, met bijbehorende titel
        title_links = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if re.search(r"/hondenlosloopgebied/[^/]+/?$", href) and "page/" not in href:
                slug = href.rstrip("/").rsplit("/", 1)[-1]
                text = a.get_text(strip=True)
                if slug and text and text.lower() != "meer informatie" and slug not in seen:
                    seen.add(slug)
                    title_links.append(slug)

        # alle tekstregels die op "Plaats, Provincie" lijken, op volgorde
        plaats_provincie = []
        for text in soup.stripped_strings:
            m = PROVINCIE_RE.match(text)
            if m:
                plaats_provincie.append((m.group("plaats").strip(), m.group("provincie").strip()))

        if not title_links:
            # geen kaartjes meer gevonden -> laatste pagina was vorige
            break

        if len(title_links) != len(plaats_provincie):
            print(
                f"  [LET OP] pagina {page}: {len(title_links)} titels maar "
                f"{len(plaats_provincie)} locatieregels gevonden - koppeling kan "
                f"hier mismatchen, controleer dit gebied later evt. handmatig."
            )

        for slug, pp in zip(title_links, plaats_provincie):
            result[slug] = pp

        # stoppen zodra er geen "volgende" link meer is
        if not soup.find("a", string=re.compile("Volgende", re.IGNORECASE)) and page > 1:
            # eerste pagina heeft altijd een "volgende", latere niet meer
            # als er geen paginanummers meer hoger dan de huidige zijn: stop
            nums = [int(n) for n in re.findall(r"/page/(\d+)/", resp.text)]
            if not nums or max(nums) <= page:
                break

        page += 1
        if page > 60:  # veiligheidsklep
            break

    print(f"  -> plaats/provincie gevonden voor {len(result)} gebieden")
    return result


def extract_body_and_links(soup: BeautifulSoup, page_url: str) -> tuple[str, list[dict]]:
    """
    Haalt de volledige tekst onder de "Honden los in X"-kop op (dus niet de
    afgekapte SEO-samenvatting), plus alle links die daarin voorkomen - denk
    aan verwijzingen naar Staatsbosbeheer, gemeentes, Natuurmonumenten,
    Leisurelands e.d. die vaak de actuele/officiele regels bevatten.
    Stopt zodra het reviewformulier ("Deel je ervaringen") begint.
    """
    heading = None
    for tag in soup.find_all(["h2", "h1"]):
        if tag.get_text(strip=True).lower().startswith("honden los in"):
            heading = tag
            break
    if heading is None:
        return "", []

    paragraphs: list[str] = []
    links: list[dict] = []
    seen = set()

    for tag in heading.find_all_next(["p", "h2", "h3", "form"]):
        if tag.name in ("h2", "h3", "form"):
            break
        text = tag.get_text(" ", strip=True)
        if "deel je ervaringen" in text.lower():
            break
        if text:
            paragraphs.append(text)
        for a in tag.find_all("a", href=True):
            link_text = a.get_text(strip=True)
            href = urljoin(page_url, a["href"])
            key = (link_text, href)
            if not link_text or key in seen:
                continue
            seen.add(key)
            links.append({
                "tekst": link_text,
                "url": href,
                "extern": "doggydating.com" not in urlparse(href).netloc,
            })

    return "\n\n".join(paragraphs), links


def parse_area_page(session: requests.Session, url: str, delay: float) -> dict | None:
    resp = get(session, url, delay)
    if resp is None:
        return None

    soup = BeautifulSoup(resp.text, "lxml")
    slug = url.rstrip("/").rsplit("/", 1)[-1]

    h1 = soup.find("h1")
    naam = h1.get_text(strip=True) if h1 else slug

    def meta(prop):
        tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
        return tag["content"].strip() if tag and tag.get("content") else None

    beschrijving, links = extract_body_and_links(soup, url)
    if not beschrijving:
        # vangnet: als de structuur toch afwijkt, val terug op de korte
        # SEO-omschrijving zodat het veld nooit helemaal leeg is
        beschrijving = meta("og:description") or ""

    afbeelding = meta("og:image") or ""

    keer_bekeken = None
    m = re.search(r"([\d.,]+)\s*keer bekeken", soup.get_text())
    if m:
        keer_bekeken = int(re.sub(r"[.,]", "", m.group(1)))

    lat = lon = None
    maps_link = soup.find("a", href=re.compile(r"google\.[a-z.]+/maps/dir"))
    if maps_link:
        m = re.search(r"dir//(-?[\d.]+),(-?[\d.]+)", maps_link["href"])
        if m:
            lat, lon = float(m.group(1)), float(m.group(2))

    gebied_type = None
    kenmerken: list[str] = []
    for img in soup.find_all("img", src=re.compile(r"/images/icon_")):
        alt = (img.get("alt") or img.get("title") or "").strip().lower()
        if not alt:
            continue
        link = img.find_parent("a")
        href = link["href"] if link else ""
        if alt in TYPES or "type=" in href:
            gebied_type = alt
        elif alt in KENMERKEN or "kenmerken" in href:
            if alt not in kenmerken:
                kenmerken.append(alt)

    seizoensregel_check = bool(
        "zwemwater" in kenmerken and beschrijving and MAAND_RE.search(beschrijving)
    )

    return {
        "slug": slug,
        "naam": naam,
        "plaats": None,       # wordt later aangevuld vanuit het overzicht
        "provincie": None,    # idem
        "type": gebied_type,
        "kenmerken": kenmerken,
        "lat": lat,
        "lon": lon,
        "keer_bekeken": keer_bekeken,
        "beschrijving": beschrijving,
        "links": links,
        "seizoensregel_check": seizoensregel_check,
        "afbeelding": afbeelding,
        "url": url,
    }


def main():
    parser = argparse.ArgumentParser(description="Scraper voor doggydating.com losloopgebieden")
    parser.add_argument("--output", default="losloopgebieden.json", help="Output JSON-bestand")
    parser.add_argument("--delay", type=float, default=0.4, help="Pauze (sec) tussen requests")
    parser.add_argument("--limit", type=int, default=None, help="Stop na N gebieden (handig om te testen)")
    parser.add_argument("--skip-plaats", action="store_true", help="Sla plaats/provincie-koppeling over (sneller testen)")
    args = parser.parse_args()

    session = requests.Session()

    area_urls = get_all_area_urls(session, args.delay)
    if args.limit:
        area_urls = area_urls[: args.limit]

    plaats_lookup = {} if args.skip_plaats else get_plaats_provincie_per_slug(session, args.delay)

    out_path = Path(args.output)
    resultaten = []
    if out_path.exists():
        try:
            resultaten = json.loads(out_path.read_text(encoding="utf-8"))
            print(f"Bestaand bestand gevonden met {len(resultaten)} gebieden, ga door waar gebleven...")
        except json.JSONDecodeError:
            resultaten = []
    klaar_slugs = {r["slug"] for r in resultaten}

    print(f"\nStart scrapen van {len(area_urls)} detailpaginas...\n")
    for i, url in enumerate(area_urls, 1):
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        if slug in klaar_slugs:
            continue

        print(f"[{i}/{len(area_urls)}] {slug}")
        data = parse_area_page(session, url, args.delay)
        if data is None:
            continue

        if slug in plaats_lookup:
            data["plaats"], data["provincie"] = plaats_lookup[slug]

        resultaten.append(data)

        # tussentijds opslaan, zodat een onderbreking geen ramp is
        if i % 20 == 0:
            out_path.write_text(json.dumps(resultaten, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  ... tussentijds opgeslagen ({len(resultaten)} gebieden)")

    out_path.write_text(json.dumps(resultaten, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nKlaar! {len(resultaten)} gebieden weggeschreven naar {out_path.resolve()}")
    print("Open doggydating_viewer.html en laad dit bestand in om te filteren.")


if __name__ == "__main__":
    main()
