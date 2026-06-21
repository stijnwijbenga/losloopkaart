# Losloopkaart — je eigen app, onafhankelijk van DoggyDating

Eén keer scrapen, dan een eigen gehoste site die je op je iPhone als app
gebruikt. Geen account bij DoggyDating nodig, geen afhankelijkheid van hun
site die blijft bestaan — de data staat straks gewoon bij jou.

Alles staat in de map **`losloopkaart-site/`** (ook als zip), klaar om te
hosten. Daarbuiten staat alleen `scrape_doggydating.py`, het script dat je
één keer lokaal draait.

## Stap 1 — eenmalig scrapen

```bash
pip install requests beautifulsoup4 lxml --break-system-packages
python scrape_doggydating.py
```

Duurt ~5-8 minuten (het script is bewust traag, met pauzes en een
herkenbare User-Agent — uit respect voor een site met 1 medewerker).
Tussentijds wordt opgeslagen, dus een onderbreking is geen ramp.

Dit levert `losloopgebieden.json` op met alle ~455 gebieden: naam, plaats,
provincie, type, kenmerken (incl. zwemwater of niet), coördinaten,
beschrijving, foto en de originele link.

**Vervang** het voorbeeldbestand in de site-map hiermee:
```bash
cp losloopgebieden.json losloopkaart-site/losloopgebieden.json
```

## Stap 2 — hosten (kies één optie)

### Optie A — GitHub Pages (aanbevolen: gratis, permanent, makkelijk te updaten)
1. Maak een gratis account op [github.com](https://github.com) als je die nog niet hebt.
2. Maak een nieuwe **public** repository, bijv. `losloopkaart`.
3. Open de repository → "Add file" → "Upload files" → sleep alle bestanden
   uit `losloopkaart-site/` erin (dus de inhoud van die map, niet de map
   zelf) → Commit.
4. Ga naar **Settings → Pages**. Bij "Branch" kies je `main` en map `/ (root)` → Save.
5. Na ~1 minuut staat je site live op:
   `https://JOUW-GEBRUIKERSNAAM.github.io/losloopkaart/`
6. Volgende keer dat je een nieuwe scrape doet: upload simpelweg het nieuwe
   `losloopgebieden.json` opnieuw via "Add file" → "Upload files" (overschrijft
   automatisch).

### Optie B — Netlify Drop (sneller opzetten, geen account nodig)
1. Ga naar [app.netlify.com/drop](https://app.netlify.com/drop)
2. Sleep de hele `losloopkaart-site/`-map erin
3. Je krijgt direct een live URL (zoiets als `wonderful-paw-123.netlify.app`)
4. Let op: zonder account verloopt deze gratis preview na een tijdje. Maak
   een gratis account aan en "claim" de site als je 'm permanent wilt.

## Stap 3 — op je iPhone

1. Open de live URL in **Safari** op je iPhone (moet Safari zijn, niet Chrome,
   voor "Add to Home Screen").
2. Tik op het deel-icoon (vierkant met pijl omhoog) onderin.
3. Kies **"Zet op beginscherm"**.
4. Je hebt nu een eigen app-icoon (het pootafdruk-icoon) dat in fullscreen
   opent, zonder Safari-balken — voelt als een native app.
5. Omdat er een service worker meegestuurd is, blijft de site ook werken
   als je even geen bereik hebt: de data wordt na de eerste keer lokaal
   gecached op je telefoon.

## Bestanden in `losloopkaart-site/`
- `index.html` — de hele app (zoeken, filteren op type/kenmerken/zwemwater/
  provincie/seizoensvlag, sorteren). Laadt automatisch `losloopgebieden.json`
  uit dezelfde map.
- `losloopgebieden.json` — de data. Begint als voorbeeldset van 6 gebieden,
  vervang 'm na stap 1 met je volledige scrape.
- `manifest.json` + `icon-*.png` — zorgen dat "Zet op beginscherm" een
  eigen appnaam en -icoon krijgt.
- `sw.js` — kleine service worker voor offline/snel laden na de eerste keer.

## Over de zwem-seizoensregels
DoggyDating vermeldt lang niet altijd of, en wanneer, honden in het water
mogen — soms staat dat alleen op de site van de terreinbeheerder
(Staatsbosbeheer, een gemeente, Natuurmonumenten, Leisurelands, etc.). Dat
volledig automatisch betrouwbaar oplossen kan niet: elke beheerder heeft een
andere site-structuur en de regels veranderen seizoensgebonden, dus een
eenmalige scrape zou op dat punt toch verouderen. In plaats daarvan doet de
scraper nu drie dingen die het probleem wél structureel makkelijker maken:

1. **Volledige beschrijftekst** — niet meer de afgekapte SEO-samenvatting,
   maar de hele "Honden los in X"-tekst. Veel periode-informatie die er wél
   stond, werd voorheen afgekapt.
2. **Alle doorklik-links** uit die tekst staan nu als knop op elke kaart
   (`extern`-links, bv. naar Staatsbosbeheer, springen er visueel uit). Eén
   tik in plaats van zelf zoeken.
3. **Seizoensvlag** (⚠️) op gebieden met zwemwater waar de tekst ook een
   datum of maand noemt — een ruwe hint, geen garantie. Filter er met de
   knop "⚠️ Seizoensregel te checken" specifiek op om te zien welke
   gebieden de moeite waard zijn om na te kijken.
4. **Eigen notitieveld** per gebied (de "+ eigen notitie toevoegen"-knop
   onderaan elke kaart). Zodra je een keer hebt opgezocht wat de regel is,
   typ je 'm daar in — wordt lokaal op je iPhone bewaard (geen account,
   geen server) en staat er de volgende keer gewoon weer.

## Updaten in de toekomst
Wil je de data later verversen (nieuwe gebieden, gewijzigde info)? Draai
`scrape_doggydating.py` opnieuw en upload het nieuwe `losloopgebieden.json`
naar je hosting (GitHub: opnieuw uploaden; Netlify: map opnieuw slepen).
Verder hoef je niets aan te passen.

## Goed om te weten
- robots.txt van doggydating.com staat scrapen volledig toe; dit script
  blijft daarbinnen en is bewust traag/herkenbaar.
- De onderliggende data blijft inhoudelijk van DoggyDating/de
  terreinbeheerders — vandaar dat elke kaart linkt naar de originele pagina.
  Je bent na het scrapen alleen niet meer *technisch* afhankelijk van hun
  site om je eigen app te laten werken.
- Als DoggyDating ooit hun pagina-opmaak aanpast, is de plaats/provincie-
  koppeling (die los van de detailpagina staat) het meest kwetsbare
  onderdeel van de scraper. De rest (kenmerken, zwemwater, volledige
  beschrijving, links, coördinaten) leunt op stabiele meta-tags en de
  vaste "Honden los in X"-kop.
- De ⚠️-seizoensvlag is een tekst-heuristiek (zoekt maandnamen in gebieden
  met zwemwater), geen juridisch sluitende controle. Gebruik 'm als
  prioriteitenlijst, niet als eindoordeel.
