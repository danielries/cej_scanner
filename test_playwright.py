import re
from playwright.sync_api import sync_playwright

# Vi bruger Heimstaden som test, da den fejlede totalt i din sidste test
TEST_URL = "https://www.heimstaden.dk/ledige-lejeboliger/?property=9-311%2C9-298%2C9-227%2C9-238%2C9-691%2C9-288%2C9-715%2C9-716%2C9-356%2C9-335%2C9-229%2C9-201%2C9-210%2C9-689%2C9-110%2C9-301%2C9-336%2C9-223%2C9-692%2C9-688%2C9-280%2C9-297%2C9-232%2C9-118%2C9-217%2C9-337%2C9-219%2C9-218%2C9-281%2C9-235%2C9-212%2C9-317%2C9-323%2C9-234%2C9-228%2C9-318%2C9-319%2C9-289%2C9-221%2C9-112%2C9-233%2C9-222%2C9-714%2C9-220%2C9-290%2C9-690&rentalType=lejlighed"

def run_local_test():
    print("Starter usynlig browser via Playwright...")
    with sync_playwright() as p:
        # Hvis du vil se browseren åbne rent fysisk på din skærm, kan du ændre headless=True til headless=False
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
        
        print("Venter på at siden og JavaScript er færdig med at loade (dette tager et par sekunder)...")
        page.goto(TEST_URL, wait_until="networkidle", timeout=60000)
        
        html = page.content()
        browser.close()
        
        print(f"✅ Siden er hentet! Læste {len(html)} tegn HTML.")
        
        # Prøver at finde links med præcis samme regex som i dit rigtige script
        links = set(re.findall(r'href="(/bolig/[^"]+)"', html))
        links.update(re.findall(r'href="(/lejebolig/[^"]+)"', html))
        
        print(f"🔗 Fandt {len(links)} bolig-links på siden.")
        
        if links:
            print("\nEksempler på fundne boliger:")
            for l in list(links)[:5]:
                print(" -", l)
        else:
            print("\n❌ Fandt STADIG ingen links. Koden er defekt.")

if __name__ == "__main__":
    run_local_test()