import re
from playwright.sync_api import sync_playwright

CEJ_URL = "https://udlejning.cej.dk/find-bolig/overblik?collection=residences&minRooms=2&monthlyPrice=0-15000&p=k%C3%B8benhavn&types=apartment"
CEJ_BASE = "https://udlejning.cej.dk"

def test_cej_playwright_robust():
    print("Tester CEJ med en fuld Playwright-browser (omgår 503/429 bot-filter)...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # Vi bruger en ægte browser-kontekst med en rigtig User-Agent
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()
            
            # Gå til siden
            page.goto(CEJ_URL, timeout=60000)
            
            # Vent på at Cloudflare/React er helt færdig
            page.wait_for_timeout(8000)
            
            html = page.content()
            browser.close()
            
            if "429" in html or "Service Unavailable" in html or "Cloudflare" in html:
                print("❌ Stadig fanget i bot-filter/rate limit. IP'en skal have lov til at puste ud i 10 minutter.")
            else:
                current = sorted(set(re.findall(r"/boliger/([0-9a-f]{32})", html)))
                print(f"✅ SUCCES! Fandt {len(current)} boliger på CEJ.")
                for listing_id in current[:3]:
                    print(f"   - {CEJ_BASE}/boliger/{listing_id}")
                    
    except Exception as e:
        print(f"❌ Playwright fejlede: {e}")

if __name__ == "__main__":
    test_cej_playwright_robust()