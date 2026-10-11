"""
Overvåger CEJ Udlejning og Kereby for nye lejeboliger og sender push via ntfy.sh.
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

def clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    for a, b in (("&amp;", "&"), ("&nbsp;", " "), ("&#x27;", "'"), ("&quot;", '"')):
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).strip()

def check_cej(state: dict, first_run: bool, today: str):
    print("--- Tjekker CEJ ---")
    seen = set(state.get("seen", []))
    try:
        html = fetch(CEJ_URL)
    except Exception as exc:
        print(f"Kunne ikke hente CEJ: {exc}")
        return

    current = sorted(set(re.findall(r"/boliger/([0-9a-f]{32})", html)))
    print(f"Fandt {len(current)} boliger hos CEJ.")
    new = [i for i in current if i not in seen]

    if not first_run:
        for listing_id in new:
            link = f"{CEJ_BASE}/boliger/{listing_id}"
            notify("Ny bolig hos CEJ 🏠", "Ny bolig fundet – tryk for at se mere", click=link)
            print(f"Ny bolig fundet: {link}")

    state["seen"] = sorted(seen | set(current))

def check_kereby(state: dict, first_run: bool):
    print("--- Tjekker Kereby ---")
    seen = set(state.get("seen_kereby", []))
    try:
        html = fetch(KEREBY_URL)
    except Exception as exc:
        print(f"Kunne ikke hente Kereby: {exc}")
        return

    # Find alle Kereby bolig-links på siden
    links = set(re.findall(r'href="(/bolig/[^"]+)"', html))
    links.update(re.findall(r'href="(https://kereby\.dk/bolig/[^"]+)"', html))

    current_links = []
    for link in links:
        if not link.startswith("http"):
            link = KEREBY_BASE + link
        current_links.append(link)

    new_links = [lnk for lnk in current_links if lnk not in seen]
    print(f"Fandt {len(current_links)} boliger hos Kereby. {len(new_links)} er nye.")

    if not first_run:
        for link in new_links:
            try:
                # Hent boligens egen side for at tjekke filtrene fra dit billede
                b_html = fetch(link)

                # Find pris, værelser og m2 i teksten
                pris_match = re.search(r'([0-9]{1,2}\.[0-9]{3})\s*kr', b_html, re.I)
                pris = int(pris_match.group(1).replace('.', '')) if pris_match else 999999

                vaer_match = re.search(r'([1-9])\s*værels', b_html, re.I)
                vaer = int(vaer_match.group(1)) if vaer_match else 0

                m2_match = re.search(r'([0-9]{2,3})\s*m', b_html, re.I)
                m2 = int(m2_match.group(1)) if m2_match else 0

                # Tjek om det er i København
                omraade_ok = any(by in link.lower() or by in b_html.lower() for by in ['københavn', 'kobenhavn', 'frederiksberg'])
                er_reserveret = "reserveret" in b_html.lower()

                # Anvend dine specifikke filtre
                if pris <= 15000 and vaer >= 2 and m2 >= 25 and omraade_ok and not er_reserveret:
                    besked = f"{pris} kr. · {vaer} vær. · {m2} m²"
                    notify("Ny bolig hos Kereby 🏠", besked, click=link)
                    print(f"Kereby match fundet: {link} ({besked})")
                else:
                    print(f"Afvist af filtre ({pris} kr, {vaer} vær, {m2} m2, reserveret: {er_reserveret}): {link}")

            except Exception as e:
                print(f"Kunne ikke tjekke detaljer for {link}: {e}")

    state["seen_kereby"] = sorted(seen | set(current_links))

def main() -> int:
    state = load_state()
    today = datetime.date.today().isoformat()
    first_run = "seen" not in state

    if first_run:
        notify("Scanner opdateret ✅", "CEJ og Kereby overvåges nu med dine specifikke filtre.", tags="white_check_mark")

    # Kør begge tjek
    check_cej(state, first_run, today)
    check_kereby(state, first_run)

    state["last_check_day"] = today
    save_state(state)
    return 0

if __name__ == "__main__":
    sys.exit(main())