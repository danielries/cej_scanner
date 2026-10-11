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

# --- Indstillinger for CEJ ---
DEFAULT_CEJ_URL = (
    "https://udlejning.cej.dk/find-bolig/overblik?collection=residences"
    "&minRooms=2&monthlyPrice=0-15400&p=sj%C3%A6lland%2Ck%C3%B8benhavn"
    "&types=apartment"
)
CEJ_URL = os.environ.get("CEJ_URL", DEFAULT_CEJ_URL)
CEJ_BASE = "https://udlejning.cej.dk"

# --- Indstillinger for Kereby ---
KEREBY_URL = "https://kereby.dk/bolig/"
KEREBY_BASE = "https://kereby.dk"

# --- Indstillinger for Heimstaden ---
HEIMSTADEN_URL = (
    "https://www.heimstaden.dk/ledige-lejeboliger/?rooms=2%2C10"
    "&rent=1000%2C15000&property=9-311%2C9-298%2C9-227%2C9-238%2C9-691%2C9-693"
    "%2C9-288%2C9-715%2C9-716%2C9-356%2C9-335%2C9-229%2C9-201%2C9-210%2C9-287"
    "%2C9-689%2C9-110%2C9-301%2C9-336%2C9-223%2C9-692%2C9-688%2C9-280%2C9-355"
    "%2C9-297%2C9-232%2C9-118%2C9-217%2C9-337%2C9-219%2C9-218%2C9-281%2C9-231"
    "%2C9-235%2C9-212%2C9-317%2C9-323%2C9-234%2C9-228%2C9-318%2C9-319%2C9-239"
    "%2C9-289%2C9-221%2C9-112%2C9-233%2C9-222%2C9-714%2C9-220%2C9-290%2C9-204"
    "%2C9-690&rentalType=lejlighed"
)
HEIMSTADEN_BASE = "https://www.heimstaden.dk"

# --- Indstillinger for Propstep ---
PROPSTEP_URL = (
    "https://propstep.com/da-DK/soeg?viewportCoordinates=%7B%22center%22%3A%7B%22coordinates%22%3A%5B12.582808189482762%2C55.68064645900864%5D%7D%2C%22northEast%22%3A%7B%22coordinates%22%3A%5B12.72430087%2C55.72946145%5D%7D%2C%22southWest%22%3A%7B%22coordinates%22%3A%5B12.512808189482762%2C55.64064645900864%5D%7D%2C%22location%22%3A%7B%22city%22%3A%22K%C3%B8benhavn+K%22%2C%22zipCode%22%3A%221050%2C1051%2C1052%2C1053%2C1054%2C1055%2C1056%2C1057%2C1058%2C1059%2C1060%2C1061%2C1062%2C1063%2C1064%2C1065%2C1066%2C1067%2C1068%2C1069%2C1070%2C1071%2C1072%2C1073%2C1074%2C1100%2C1101%2C1102%2C1103%2C1104%2C1105%2C1106%2C1107%2C1110%2C1111%2C1112%2C1113%2C1114%2C1115%2C1116%2C1117%2C1118%2C1119%2C1120%2C1121%2C1122%2C1123%2C1124%2C1125%2C1126%2C1127%2C1128%2C1129%2C1130%2C1131%2C1150%2C1151%2C1152%2C1153%2C1154%2C1155%2C1156%2C1157%2C1158%2C1159%2C1160%2C1161%2C1162%2C1164%2C1165%2C1166%2C1167%2C1168%2C1169%2C1170%2C1171%2C1172%2C1173%2C1174%2C1175%2C1200%2C1201%2C1202%2C1203%2C1204%2C1205%2C1206%2C1207%2C1208%2C1209%2C1210%2C1211%2C1212%2C1213%2C1214%2C1215%2C1216%2C1218%2C1219%2C1220%2C1221%2C1250%2C1251%2C1252%2C1253%2C1254%2C1255%2C1256%2C1257%2C1259%2C1260%2C1261%2C1263%2C1264%2C1265%2C1266%2C1267%2C1268%2C1270%2C1271%2C1300%2C1301%2C1302%2C1303%2C1304%2C1306%2C1307%2C1308%2C1309%2C1310%2C1311%2C1312%2C1313%2C1314%2C1315%2C1316%2C1317%2C1318%2C1319%2C1320%2C1321%2C1322%2C1323%2C1324%2C1325%2C1326%2C1327%2C1328%2C1329%2C1350%2C1352%2C1353%2C1354%2C1355%2C1356%2C1357%2C1358%2C1359%2C1360%2C1361%2C1362%2C1363%2C1364%2C1365%2C1366%2C1367%2C1368%2C1369%2C1370%2C1371%2C1400%2C1401%2C1402%2C1403%2C1406%2C1407%2C1408%2C1409%2C1410%2C1411%2C1412%2C1413%2C1414%2C1415%2C1416%2C1417%2C1418%2C1419%2C1420%2C1421%2C1422%2C1423%2C1424%2C1425%2C1426%2C1427%2C1428%2C1429%2C1430%2C1432%2C1433%2C1434%2C1435%2C1436%2C1437%2C1438%2C1439%2C1440%2C1441%2C1450%2C1451%2C1452%2C1453%2C1454%2C1455%2C1456%2C1457%2C1458%2C1459%2C1460%2C1461%2C1462%2C1463%2C1464%2C1465%2C1466%2C1467%2C1468%2C1470%2C1471%2C1472%2C1473%22%2C%22label%22%3A%221050-1473+K%C3%B8benhavn+K%22%7D%7D&priceMax=15000&roomsMin=2&propertyTypes=%5B1%5D&radius=5&page=1&zipCodes=1050..." # Forkortet visuelt, koden loader hele URL'en
)
PROPSTEP_BASE = "https://propstep.com"

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

def fetch(url: str, attempts: int = 5) -> str:
    import time
    import urllib.error

    if SCRAPINGANT_API_KEY:
        encoded_url = urllib.parse.quote(url)
        url = f"https://api.scrapingant.com/v2/general?url={encoded_url}&x-api-key={SCRAPINGANT_API_KEY}"

    for attempt in range(1, attempts + 1):
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 503) or attempt == attempts:
                raise
            retry_after = exc.headers.get("Retry-After", "")
            wait = int(retry_after) if retry_after.isdigit() else 15 * attempt
            wait = min(wait, 45)
            print(f"HTTP {exc.code} – venter {wait} sek. og prøver igen ({attempt}/{attempts})")
            time.sleep(wait)
    raise RuntimeError("unreachable")

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
                notify("Ny bolig hos CEJ 🏠", "Ny bolig fundet – tryk for at se mere", click=f"{CEJ_BASE}/boliger/{listing_id}")
        state["seen"] = sorted(seen | set(current))
    except:
        pass

def check_kereby(state: dict, first_run: bool):
    seen = set(state.get("seen_kereby", []))
    try:
        html = fetch(KEREBY_URL)
        links = set(re.findall(r'href="(/bolig/[^"]+)"', html))
        current_links = [KEREBY_BASE + l if not l.startswith("http") else l for l in links]
        new_links = [lnk for lnk in current_links if lnk not in seen]

        if not first_run:
            for link in new_links:
                try:
                    b_html = fetch(link)
                    pris_m = re.search(r'([0-9]{1,2}\.[0-9]{3})\s*kr', b_html, re.I)
                    pris = int(pris_m.group(1).replace('.', '')) if pris_m else 999999
                    vaer_m = re.search(r'([1-9])\s*værels', b_html, re.I)
                    vaer = int(vaer_m.group(1)) if vaer_m else 0
                    m2_m = re.search(r'([0-9]{2,3})\s*m', b_html, re.I)
                    m2 = int(m2_m.group(1)) if m2_m else 0
                    
                    omraade_ok = any(by in link.lower() or by in b_html.lower() for by in ['københavn', 'frederiksberg'])
                    er_reserveret = "reserveret" in b_html.lower()

                    if pris <= 15000 and vaer >= 2 and m2 >= 25 and omraade_ok and not er_reserveret:
                        notify("Ny bolig hos Kereby 🏠", f"{pris} kr. · {vaer} vær. · {m2} m²", click=link)
                except:
                    pass
        state["seen_kereby"] = sorted(seen | set(current_links))
    except:
        pass

def check_heimstaden(state: dict, first_run: bool):
    seen = set(state.get("seen_heimstaden", []))
    try:
        html = fetch(HEIMSTADEN_URL)
        links = set(re.findall(r'href="(/bolig/[^"]+)"', html))
        links.update(re.findall(r'href="(/lejebolig/[^"]+)"', html))
        current_links = [HEIMSTADEN_BASE + l if not l.startswith("http") else l for l in links]
        new_links = [lnk for lnk in current_links if lnk not in seen]

        if not first_run:
            for link in new_links:
                try:
                    b_html = fetch(link)
                    pris_m = re.search(r'([0-9]{1,2}\.[0-9]{3})\s*kr', b_html, re.I)
                    pris = pris_m.group(1) if pris_m else "?"
                    vaer_m = re.search(r'([1-9])\s*værels', b_html, re.I)
                    vaer = vaer_m.group(1) if vaer_m else "?"
                    m2_m = re.search(r'([0-9]{2,3})\s*m', b_html, re.I)
                    m2 = m2_m.group(1) if m2_m else "?"
                    notify("Ny bolig hos Heimstaden 🏠", f"{pris} kr. · {vaer} vær. · {m2} m²", click=link)
                except:
                    notify("Ny bolig hos Heimstaden 🏠", "Ny bolig fundet – tryk for at se mere", click=link)
        state["seen_heimstaden"] = sorted(seen | set(current_links))
    except:
        pass

def check_propstep(state: dict, first_run: bool):
    print("--- Tjekker Propstep ---")
    seen = set(state.get("seen_propstep", []))
    is_propstep_first_run = len(seen) == 0  # Forhindrer spam, når Propstep tilføjes første gang
    
    try:
        html = fetch(PROPSTEP_URL)
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

    state["last_check_day"] = today
    save_state(state)
    return 0

if __name__ == "__main__":
    sys.exit(main())