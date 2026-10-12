import re
from playwright.sync_api import sync_playwright

def test_city_apartment_raw():
    print("Test: Starter helt rå browser uden context...")
    with sync_playwright() as p:
        # Bemærk: Vi launcher direkte uden context, præcis som da det virkede!
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.goto("https://cityapartment.dk/da/lejeboliger-koebenhavn/", timeout=60000)
        page.wait_for_timeout(6000)
        
        html = page.content()
        browser.close()
        
        match_links = re.findall(r'href="(https://cityapartment\.dk/da/cityapartments/[^"]+)"', html)
        unique_links = list(set(match_links))
        
        print(f"✅ Resultat: Fandt {len(unique_links)} boliger.")
        for l in unique_links[:2]:
            print(f"   - {l}")

if __name__ == "__main__":
    test_city_apartment_raw()