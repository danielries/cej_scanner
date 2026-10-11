"""
Overvåger CEJ Udlejning, Kereby og Heimstaden for nye lejeboliger og sender push via ntfy.sh.
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
        print(f"[ingen NTFY_TOPIC] {title}: {message}")
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

def check_cej(state: dict, first_run: bool, today: str):
    print("--- Tjekker CEJ ---")
    seen = set(state.get("seen", []))
    try:
        html = fetch(CEJ_URL)
    except Exception as exc:
        print(f"Kunne ikke hente CEJ: {exc}")
        return

    current = sorted(set(re.findall(r"/boliger/([0-9a-f]{32})", html)))
    new = [i for i in current if i not in seen]

    if not first_run:
        for listing_id in new:
            link = f"{CEJ_BASE}/boliger/{listing_id}"
            notify("Ny bolig hos CEJ 🏠", "Ny bolig fundet – tryk for at se mere", click=link)

    state["seen"] = sorted(seen | set(current))

def check_kereby(state: dict, first_run: bool):
    print("--- Tjekker Kereby ---")
    seen = set(state.get("seen_kereby", []))
    try:
        html = fetch(KEREBY_URL)
    except Exception as exc:
        print(f"Kunne ikke hente Kereby: {exc}")
        return

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

def check_heimstaden(state: dict, first_run: bool):
    print("--- Tjekker Heimstaden ---")
    seen = set(state.get("seen_heimstaden", []))
    try:
        html = fetch(HEIMSTADEN_URL)
    except Exception as exc:
        print(f"Kunne ikke hente Heimstaden: {exc}")
        return

    # Find alle bolig-links (Heimstaden bruger ofte /bolig/ eller /lejebolig/)
    links = set(re.findall(r'href="(/bolig/[^"]+)"', html))
    links.update(re.findall(r'href="(/lejebolig/[^"]+)"', html))
    current_links = [HEIMSTADEN_BASE + l if not l.startswith("http") else l for l in links]
    new_links = [lnk for lnk in current_links if lnk not in seen]

    if not first_run:
        for link in new_links:
            besked = "Ny bolig fundet – tryk for at se mere"
            try:
                # Vi henter siden kortvarigt for at finde pris og m2 til push-beskeden
                b_html = fetch(link)
                
                pris_m = re.search(r'([0-9]{1,2}\.[0-9]{3})\s*kr', b_html, re.I)
                pris = pris_m.group(1) if pris_m else "?"
                
                vaer_m = re.search(r'([1-9])\s*værels', b_html, re.I)
                vaer = vaer_m.group(1) if vaer_m else "?"
                
                m2_m = re.search(r'([0-9]{2,3})\s*m', b_html, re.I)
                m2 = m2_m.group(1) if m2_m else "?"

                if pris != "?" or vaer != "?":
                    besked = f"{pris} kr. · {vaer} vær. · {m2} m²"
            except:
                pass
            
            # Vi sender besked med det samme, fordi vi ved, at URL'en allerede har sorteret alt fra
            notify("Ny bolig hos Heimstaden 🏠", besked, click=link)

    state["seen_heimstaden"] = sorted(seen | set(current_links))

def main() -> int:
    state = load_state()
    today = datetime.date.today().isoformat()
    first_run = "seen" not in state

    if first_run:
        notify("Scanner opdateret ✅", "CEJ, Kereby og Heimstaden overvåges nu.", tags="white_check_mark")

    check_cej(state, first_run, today)
    check_kereby(state, first_run)
    check_heimstaden(state, first_run)

    state["last_check_day"] = today
    save_state(state)
    return 0

if __name__ == "__main__":
    sys.exit(main())