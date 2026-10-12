"""
Overvåger CEJ, Kereby, Heimstaden og Propstep for nye lejeboliger og sender push via ntfy.sh.
Kører på GitHub Actions via cron-job.org.
"""

import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from playwright.sync_api import sync_playwright

# --- Indstillinger for CEJ ---
DEFAULT_CEJ_URL = (
    "https://udlejning.cej.dk/find-bolig/overblik?collection=residences&minRooms=2&monthlyPrice=0-15000&p=k%C3%B8benhavn&types=apartment"
)
CEJ_URL = os.environ.get("CEJ_URL", DEFAULT_CEJ_URL)
CEJ_BASE = "https://udlejning.cej.dk"

# --- Indstillinger for Kereby ---
KEREBY_URL = "https://kereby.dk/bolig/"
KEREBY_BASE = "https://kereby.dk"

# --- Indstillinger for Heimstaden ---
HEIMSTADEN_URL = (
    "https://www.heimstaden.dk/ledige-lejeboliger/?property=9-311%2C9-298%2C9-227%2C9-238%2C9-691%2C9-288%2C9-715%2C9-716%2C9-356%2C9-335%2C9-229%2C9-201%2C9-210%2C9-689%2C9-110%2C9-301%2C9-336%2C9-223%2C9-692%2C9-688%2C9-280%2C9-297%2C9-232%2C9-118%2C9-217%2C9-337%2C9-219%2C9-218%2C9-281%2C9-235%2C9-212%2C9-317%2C9-323%2C9-234%2C9-228%2C9-318%2C9-319%2C9-289%2C9-221%2C9-112%2C9-233%2C9-222%2C9-714%2C9-220%2C9-290%2C9-690&rentalType=lejlighed&rooms=2%2C10&rent=1000%2C15000"
)
HEIMSTADEN_BASE = "https://www.heimstaden.dk"

# --- Indstillinger for Propstep ---
PROPSTEP_URL = (
    "https://propstep.com/da-DK/soeg?viewportCoordinates=%7B%22center%22%3A%7B%22coordinates%22%3A%5B12.582808189482762%2C55.68064645900864%5D%7D%2C%22northEast%22%3A%7B%22coordinates%22%3A%5B12.72430087%2C55.72946145%5D%7D%2C%22southWest%22%3A%7B%22coordinates%22%3A%5B12.512808189482762%2C55.64064645900864%5D%7D%2C%22location%22%3A%7B%22city%22%3A%22K%C3%B8benhavn+K%22%2C%22zipCode%22%3A%221050%2C1051%2C1052%2C1053%2C1054%2C1055%2C1056%2C1057%2C1058%2C1059%2C1060%2C1061%2C1062%2C1063%2C1064%2C1065%2C1066%2C1067%2C1068%2C1069%2C1070%2C1071%2C1072%2C1073%2C1074%2C1100%2C1101%2C1102%2C1103%2C1104%2C1105%2C1106%2C1107%2C1110%2C1111%2C1112%2C1113%2C1114%2C1115%2C1116%2C1117%2C1118%2C1119%2C1120%2C1121%2C1122%2C1123%2C1124%2C1125%2C1126%2C1127%2C1128%2C1129%2C1130%2C1131%2C1150%2C1151%2C1152%2C1153%2C1154%2C1155%2C1156%2C1157%2C1158%2C1159%2C1160%2C1161%2C1162%2C1164%2C1165%2C1166%2C1167%2C1168%2C1169%2C1170%2C1171%2C1172%2C1173%2C1174%2C1175%2C1200%2C1201%2C1202%2C1203%2C1204%2C1205%2C1206%2C1207%2C1208%2C1209%2C1210%2C1211%2C1212%2C1213%2C1214%2C1215%2C1216%2C1218%2C1219%2C1220%2C1221%2C1250%2C1251%2C1252%2C1253%2C1254%2C1255%2C1256%2C1257%2C1259%2C1260%2C1261%2C1263%2C1264%2C1265%2C1266%2C1267%2C1268%2C1270%2C1271%2C1300%2C1301%2C1302%2C1303%2C1304%2C1306%2C1307%2C1308%2C1309%2C1310%2C1311%2C1312%2C1313%2C1314%2C1315%2C1316%2C1317%2C1318%2C1319%2C1320%2C1321%2C1322%2C1323%2C1324%2C1325%2C1326%2C1327%2C1328%2C1329%2C1350%2C1352%2C1353%2C1354%2C1355%2C1356%2C1357%2C1358%2C1359%2C1360%2C1361%2C1362%2C1363%2C1364%2C1365%2C1366%2C1367%2C1368%2C1369%2C1370%2C1371%2C1400%2C1401%2C1402%2C1403%2C1406%2C1407%2C1408%2C1409%2C1410%2C1411%2C1412%2C1413%2C1414%2C1415%2C1416%2C1417%2C1418%2C1419%2C1420%2C1421%2C1422%2C1423%2C1424%2C1425%2C1426%2C1427%2C1428%2C1429%2C1430%2C1432%2C1433%2C1434%2C1435%2C1436%2C1437%2C1438%2C1439%2C1440%2C1441%2C1450%2C1451%2C1452%2C1453%2C1454%2C1455%2C1456%2C1457%2C1458%2C1459%2C1460%2C1461%2C1462%2C1463%2C1464%2C1465%2C1466%2C1467%2C1468%2C1470%2C1471%2C1472%2C1473%22%2C%22label%22%3A%221050-1473+K%C3%B8benhavn+K%22%7D%7D&priceMax=15000&propertyTypes=%5B1%5D&radius=5&page=1&zipCodes=1050...&roomsMin=2"
)
PROPSTEP_BASE = "https://propstep.com"

# --- Indstillinger for City Apartment ---
CITYAPARTMENT_URL = "https://cityapartment.dk/da/lejeboliger-koebenhavn/?_sfm_pris=0+15100&_sfm_ikon_m2=0+300"

# --- Indstillinger for Findbolig ---
FINDBOLIG_URL = (
    "https://www.findbolig.nu/da-dk/find?Commune=Frederiksberg&Rent=0%2C45000&Rooms=0%2C10&Area=0%2C500&Floor=0%2C20&PropertyYear=1900%2C2026&City=K%C3%B8benhavn+%C3%98%2CK%C3%B8benhavn+N%2CK%C3%B8benhavn+V%2CK%C3%B8benhavn+K"
)
FINDBOLIG_BASE = "https://www.findbolig.nu"

# --- System ---
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
STATE_FILE = os.environ.get("STATE_FILE", "seen.json")
SCRAPINGANT_API_KEY = os.environ.get("SCRAPINGANT_API_KEY", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "da-DK,da;q=0.9,en;q=0.8",
}

def fetch(url: str, attempts: int = 5, force_scrapingant: bool = False) -> str:
    import time
    import urllib.error
    import ssl

    # Opsæt SSL-kontekst til at ignorere certifikat-tjek
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # Tjek om vi skal bruge ScrapingAnt (enten fordi vi beder om det, eller som fallback)
    target_url = url
    if force_scrapingant and SCRAPINGANT_API_KEY:
        encoded_url = urllib.parse.quote(url)
        target_url = f"https://api.scrapingant.com/v2/general?url={encoded_url}&x-api-key={SCRAPINGANT_API_KEY}&browser=false"

    for attempt in range(1, attempts + 1):
        req = urllib.request.Request(target_url, headers=HEADERS)
        try:
            # Vi tilføjer context=ctx her for at ignorere SSL-fejlen
            with urllib.request.urlopen(req, timeout=90, context=ctx) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            # Hvis vi bliver blokeret af et anti-bot system (403, 406) eller rammer en rate limit (429) på et gratis kald
            if not force_scrapingant and SCRAPINGANT_API_KEY and exc.code in (401, 403, 406, 429, 503):
                print(f"HTTP {exc.code} på {url} – skifter til ScrapingAnt (fallback)...")
                return fetch(url, attempts=3, force_scrapingant=True)
            
            if exc.code not in (429, 503) or attempt == attempts:
                raise
            retry_after = exc.headers.get("Retry-After", "")
            wait = int(retry_after) if retry_after.isdigit() else 15 * attempt
            wait = min(wait, 45)
            print(f"HTTP {exc.code} – venter {wait} sek. og prøver igen ({attempt}/{attempts})")
            time.sleep(wait)
            
    raise RuntimeError("unreachable")

def fetch_js(url: str) -> str:
    print(f"Starter usynlig browser for: {url[:50]}...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=HEADERS["User-Agent"])
        # Venter indtil al netværkstrafik (JavaScript) er færdig
        page.goto(url, wait_until="networkidle", timeout=60000)
        html = page.content()
        browser.close()
        return html

def notify(title: str, message: str, click: str | None = None, tags: str = "house") -> None:
    if not NTFY_TOPIC:
        return
    params = {"title": title, "tags": tags}
    if click:
        params["click"] = click
    req = urllib.request.Request(
        f"https://ntfy.sh/{urllib.parse.quote(NTFY_TOPIC)}?{urllib.parse.urlencode(params)}",
        data=message.encode("utf-8"),
        method="POST",
    )
    urllib.request.urlopen(req, timeout=90).read()

def load_state() -> dict:
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

def check_cej(state: dict, first_run: bool):
    seen = set(state.get("seen", []))
    try:
        html = fetch(CEJ_URL)
        current = sorted(set(re.findall(r"/boliger/([0-9a-f]{32})", html)))
        new = [i for i in current if i not in seen]
        if not first_run:
            for listing_id in new:
                link = f"{CEJ_BASE}/boliger/{listing_id}"
                try:
                    b_html = fetch(link).lower()
                    
                    # 1. Frasortér reserverede og lukkede boliger
                    if "reserveret" in b_html or "udlejet" in b_html or "lukket" in b_html:
                        continue
                        
                    # 2. Hård blokering af Amager og uønskede postnumre
                    bad_zips = ["2300", "2400", "2450", "2500", "2700", "2720"]
                    if any(bz in b_html for bz in bad_zips):
                        continue
                        
                    notify("Ny bolig hos CEJ 🏠", "Ny bolig fundet – tryk for at se mere", click=link)
                except Exception:
                    pass
        state["seen"] = sorted(seen | set(current))
    except:
        pass

def check_kereby(state: dict, first_run: bool):
    print("--- Tjekker Kereby ---")
    seen = set(state.get("seen_kereby", []))
    is_kereby_first_run = len(seen) == 0
    
    try:
        html = fetch_js(KEREBY_URL)
        
        # Fanger nu links uanset om de starter med https://kereby.dk eller bare /bolig/
        links_abs = set(re.findall(r'href="(https://kereby\.dk/bolig/[^"]+)"', html))
        links_rel = set(re.findall(r'href="(/bolig/[^"]+)"', html))
        
        links = links_abs.union({KEREBY_BASE + l for l in links_rel})
        new_links = [lnk for lnk in links if lnk not in seen]

        if not first_run and not is_kereby_first_run:
            for link in new_links:
                # 1. Tjek postnummer via URL'en (Tillad 1000-2000, 2100, 2200)
                postnr_match = re.search(r'-([1-2][0-9]{3})-(kobenhavn|frederiksberg)', link, re.I)
                if postnr_match:
                    p = int(postnr_match.group(1))
                    if (1000 <= p <= 2000) or p == 2100 or p == 2200:
                        
                        # 2. Åbn boligen for at tjekke pris, værelser og status
                        try:
                            b_html = fetch(link)
                            
                            # Frasortér hvis den allerede er reserveret
                            if "reserveret" in b_html.lower():
                                continue
                            
                            # Find pris
                            pris_m = re.search(r'([0-9]{1,2}\.[0-9]{3})\s*kr', b_html, re.I)
                            pris_val = int(pris_m.group(1).replace('.', '')) if pris_m else 999999
                            
                            # Find værelser
                            vaer_m = re.search(r'([1-9])\s*Værels', b_html, re.I)
                            vaer_val = int(vaer_m.group(1)) if vaer_m else 0

                            # Hård grænse på maks 15.000 kr.
                            if pris_val <= 15000 and vaer_val >= 2:
                                notify("Ny bolig hos Kereby 🏠", f"{pris_val} kr. · {vaer_val} vær.", click=link)
                        except Exception as e:
                            print(f"Fejl ved Kereby bolig {link}: {e}")
                        
        state["seen_kereby"] = sorted(seen | links)
    except Exception as exc:
        print(f"Kunne ikke hente Kereby: {exc}")

def check_heimstaden(state: dict, first_run: bool):
    print("--- Tjekker Heimstaden ---")
    seen = set(state.get("seen_heimstaden", []))
    is_heimstaden_first_run = len(seen) == 0
    
    try:
        html = fetch_js(HEIMSTADEN_URL)
        links = set(re.findall(r'href="(/bolig/[^"]+)"', html))
        links.update(re.findall(r'href="(/lejebolig/[^"]+)"', html))
        current_links = [HEIMSTADEN_BASE + l if not l.startswith("http") else l for l in links]
        new_links = [lnk for lnk in current_links if lnk not in seen]

        if not first_run and not is_heimstaden_first_run:
            for link in new_links:
                # Træk postnummer ud af URL'en og tillad kun de rigtige
                postnr_match = re.search(r'-([1-2][0-9]{3})-(koebenhavn|frederiksberg)', link, re.I)
                
                # Bloker Amager (2300), Nordvest (2400) osv. direkte
                bad_zips = ["2300", "2400", "2450", "2500", "2700", "2720"]
                if any(bz in link for bz in bad_zips):
                    continue
                    
                if postnr_match:
                    p = int(postnr_match.group(1))
                    if (1000 <= p <= 2000) or p == 2100 or p == 2200:
                        notify("Ny bolig hos Heimstaden 🏠", "Tryk for at åbne", click=link)
                
        state["seen_heimstaden"] = sorted(seen | set(current_links))
    except Exception as exc:
        print(f"Kunne ikke hente Heimstaden: {exc}")

def check_propstep(state: dict, first_run: bool):
    print("--- Tjekker Propstep ---")
    seen = set(state.get("seen_propstep", []))
    is_propstep_first_run = len(seen) == 0  # Forhindrer spam, når Propstep tilføjes første gang
    
    try:
        html = fetch_js(PROPSTEP_URL)
        links = set(re.findall(r'href="(/da-DK/bolig/[^"]+)"', html))
        current_links = [PROPSTEP_BASE + l if not l.startswith("http") else l for l in links]
        new_links = [lnk for lnk in current_links if lnk not in seen]

        if not first_run and not is_propstep_first_run:
            for link in new_links:
                try:
                    b_html = fetch(link)
                    html_lower = b_html.lower()
                    
                    # 1. Frasortér reserverede og udlejede boliger
                    if "reserveret" in html_lower or "udlejet" in html_lower:
                        continue
                        
                    # 2. Hård blokering af uønskede postnumre/bydele (Amager, Nordvest, Sydhavn osv.)
                    bad_zips = ["2300", "2400", "2450", "2500", "2700", "2720"]
                    if any(re.search(rf"\b{bz}\b", b_html) for bz in bad_zips):
                        continue
                        
                    # 3. Find pris, værelser og m2
                    pris_m = re.search(r'([0-9]{1,2}[.,][0-9]{3})', b_html)
                    pris = pris_m.group(1).replace(',', '.') if pris_m else "?"
                    
                    vaer_m = re.search(r'([1-9])\s*vær', b_html, re.I)
                    vaer = vaer_m.group(1) if vaer_m else "?"
                    
                    m2_m = re.search(r'([0-9]{2,3})\s*m', b_html, re.I)
                    m2 = m2_m.group(1) if m2_m else "?"

                    notify("Ny bolig hos Propstep 🏠", f"{pris} kr. · {vaer} vær. · {m2} m²", click=link)
                except Exception as e:
                    print(f"Fejl ved Propstep bolig {link}: {e}")
                    
        state["seen_propstep"] = sorted(seen | set(current_links))
    except Exception as exc:
        print(f"Kunne ikke hente Propstep: {exc}")

def check_cityapartment(state: dict, first_run: bool):
    print("--- Tjekker City Apartment ---")
    seen = set(state.get("seen_cityapt", []))
    is_cityapt_first_run = len(seen) == 0
    
    try:
        html = fetch_js(CITYAPARTMENT_URL)
        links = set(re.findall(r'href="(https://cityapartment\.dk/da/[^"]+)"', html))
        
        # OPATERET FILTER: Vi leder efter "cityapartments" i stedet for "property"
        links = {l for l in links if "cityapartments" in l and l != CITYAPARTMENT_URL}
        
        new_links = [lnk for lnk in links if lnk not in seen]

        if not first_run and not is_cityapt_first_run:
            for link in new_links:
                try:
                    b_html = fetch(link)
                    
                    # 1. Tjek postnummer (tillad kun K, V, Frb, Ø, N)
                    postnr_match = re.search(r'\b(1[0-9]{3}|2000|2100|2200)\b', b_html)
                    if not postnr_match:
                        continue
                        
                    # 2. Find pris og værelser
                    pris_m = re.search(r'([0-9]{1,2}[.,][0-9]{3})\s*DKK', b_html, re.I)
                    pris_val = int(pris_m.group(1).replace('.', '').replace(',', '')) if pris_m else 999999
                    pris_str = pris_m.group(1) if pris_m else "?"
                    
                    vaer_m = re.search(r'([1-9])\s*-?\s*vær', b_html, re.I)
                    vaer_val = int(vaer_m.group(1)) if vaer_m else 0
                    vaer_str = vaer_m.group(1) if vaer_m else "?"

                    # 3. Filtrer benhårdt på dine krav
                    if pris_val <= 15000 and vaer_val >= 2:
                        notify("Ny bolig hos City Apartment 🏠", f"{pris_str} kr. · {vaer_str} vær.", click=link)
                except Exception as e:
                    print(f"Fejl ved City Apt bolig {link}: {e}")
                    
        state["seen_cityapt"] = sorted(seen | links)
    except Exception as exc:
        print(f"Kunne ikke hente City Apartment: {exc}")

def check_findbolig(state: dict, first_run: bool):
    print("--- Tjekker Findbolig ---")
    seen = set(state.get("seen_findbolig", []))
    is_findbolig_first_run = len(seen) == 0
    
    # Din præcise URL med Frederiksberg og Kbh K, V, N, Ø
    FINDBOLIG_SEARCH_URL = "https://www.findbolig.nu/da-dk/find?Commune=Frederiksberg&Rent=0%2C45000&Rooms=0%2C10&Area=0%2C500&Floor=0%2C20&PropertyYear=1900%2C2026&City=K%C3%B8benhavn+%C3%98%2CK%C3%B8benhavn+N%2CK%C3%B8benhavn+V%2CK%C3%B8benhavn+K"
    
    try:
        boliger = []
        
        print("Starter usynlig browser og aflytter Findboligs API...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=HEADERS["User-Agent"])
            
            def handle_response(response):
                if "api/search" in response.url.lower():
                    try:
                        data = response.json()
                        if "results" in data:
                            boliger.extend(data["results"])
                    except:
                        pass
                        
            page.on("response", handle_response)
            page.goto(FINDBOLIG_SEARCH_URL, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)
            browser.close()

        current_links = []
        new_boliger = []
        
        for b in boliger:
            b_id = str(b.get("id", ""))
            if not b_id:
                continue
                
            link = f"{FINDBOLIG_BASE}/da-dk/bolig/{b_id}"
            current_links.append(link)
            
            if link not in seen:
                new_boliger.append((link, b))

        if not first_run and not is_findbolig_first_run:
            for link, b in new_boliger:
                pris = b.get("rent", 999999)
                vaer = b.get("rooms", 0)
                vej = b.get("street", "Ukendt vej")
                postnr = b.get("postalCode", 0)
                
                # 1. Sikkerhedsnet: Tillad kun postnumre 1000-2200 (K, V, Frb, N, Ø)
                if not (1000 <= postnr <= 2200):
                    continue
                
                # 2. Filtrer på maks 15.000 kr. og min 2 værelser
                if pris <= 15000 and vaer >= 2:
                    notify("Ny bolig hos Findbolig 🏠", f"{vej} · {pris} kr. · {vaer} vær.", click=link)
                
        state["seen_findbolig"] = sorted(seen | set(current_links))
    except Exception as exc:
        print(f"Kunne ikke hente Findbolig: {exc}")


def main() -> int:
    state = load_state()
    today = datetime.date.today().isoformat()
    first_run = "seen" not in state

    if first_run:
        notify("Scanner opdateret ✅", "Propstep er nu tilføjet din bolig-overvågning.", tags="white_check_mark")

    check_cej(state, first_run)
    check_kereby(state, first_run)
    check_heimstaden(state, first_run)
    check_propstep(state, first_run)
    check_cityapartment(state, first_run)
    check_findbolig(state, first_run)

    state["last_check_day"] = today
    save_state(state)
    return 0

if __name__ == "__main__":
    sys.exit(main())