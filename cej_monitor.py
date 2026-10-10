"""
Overvåger en CEJ Udlejning-søgning og sender push via ntfy.sh,
når der dukker en ny bolig op.

Kører på GitHub Actions (se .github/workflows/cej.yml).
Kræver kun Python's standardbibliotek.
"""

import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request

# Søgningen der overvåges (kan overskrives med miljøvariablen CEJ_URL)
DEFAULT_URL = (
    "https://udlejning.cej.dk/find-bolig/overblik?collection=residences"
    "&minRooms=2&monthlyPrice=0-15400&p=sj%C3%A6lland%2Ck%C3%B8benhavn"
    "&types=apartment"
)
URL = os.environ.get("CEJ_URL", DEFAULT_URL)
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
STATE_FILE = os.environ.get("STATE_FILE", "seen.json")
BASE = "https://udlejning.cej.dk"
SCRAPINGANT_API_KEY = os.environ.get("SCRAPINGANT_API_KEY", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "da-DK,da;q=0.9,en;q=0.8",
    "Referer": "https://udlejning.cej.dk/",
}

LISTING_RE = re.compile(r"/boliger/([0-9a-f]{32})")


def fetch(url: str, attempts: int = 5) -> str:
    import time
    import urllib.error

    if SCRAPINGANT_API_KEY:
        encoded_url = urllib.parse.quote(url)
        url = f"https://api.scrapingant.com/v2/general?url={encoded_url}&x-api-key={SCRAPINGANT_API_KEY}"

    for attempt in range(1, attempts + 1):
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
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
    # Titel m.m. sendes som URL-parametre, så æøå virker uden problemer
    params = {"title": title, "tags": tags}
    if click:
        params["click"] = click
    req = urllib.request.Request(
        f"https://ntfy.sh/{urllib.parse.quote(NTFY_TOPIC)}?{urllib.parse.urlencode(params)}",
        data=message.encode("utf-8"),
        method="POST",
    )
    urllib.request.urlopen(req, timeout=30).read()


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


def describe(listing_id: str) -> str:
    """Prøv at hente en kort beskrivelse af boligen (titel/adresse)."""
    try:
        html = fetch(f"{BASE}/boliger/{listing_id}")
    except Exception:
        return "Ny bolig – tryk for at åbne"
    parts = []
    for pattern in (
        r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"',
        r"<title>(.*?)</title>",
        r'<meta[^>]+name="description"[^>]+content="([^"]+)"',
    ):
        m = re.search(pattern, html, re.S | re.I)
        if m:
            t = clean(m.group(1))
            if t and t not in parts:
                parts.append(t)
    return " · ".join(parts[:2])[:300] or "Ny bolig – tryk for at åbne"


def main() -> int:
    state = load_state()
    today = datetime.date.today().isoformat()
    first_run = "seen" not in state
    seen = set(state.get("seen", []))

    try:
        html = fetch(URL)
    except Exception as exc:  # netværksfejl, 5xx osv.
        errors = state.get("errors", 0) + 1
        state["errors"] = errors
        print(f"Kunne ikke hente siden ({errors} fejl i træk): {exc}")
        if errors == 18:  # ca. 3 timer uden en eneste vellykket kørsel
            notify("CEJ-overvågning: fejl", f"Har ikke kunnet hente CEJ i ca. 3 timer: {exc}",
                   click=URL, tags="warning")
        save_state(state)
        return 0
    state["errors"] = 0

    current = sorted(set(LISTING_RE.findall(html)))
    print(f"Fandt {len(current)} boliger på siden.")

    if not current:
        # Siden har måske ændret sig (eller indlæses kun med JavaScript)
        if state.get("empty_warned") != today:
            notify("CEJ-overvågning: 0 boliger fundet",
                   "Scriptet fandt ingen boliger. Siden kan have ændret sig – tjek den manuelt.",
                   click=URL, tags="warning")
            state["empty_warned"] = today
        save_state(state)
        return 0

    new = [i for i in current if i not in seen]

    if first_run:
        notify("CEJ-overvågning startet ✅",
               f"Følger nu din søgning. {len(current)} boliger ligger der allerede – "
               "du får besked, når der kommer nye.", click=URL, tags="white_check_mark")
    else:
        for listing_id in new:
            link = f"{BASE}/boliger/{listing_id}"
            notify("Ny bolig hos CEJ 🏠", describe(listing_id), click=link)
            print(f"Ny bolig: {link}")

    state["seen"] = sorted(seen | set(current))
    state["last_check_day"] = today  # ændres én gang i døgnet → holder workflowet aktivt
    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
