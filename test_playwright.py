import re
from playwright.sync_api import sync_playwright

TEST_URL = "https://kereby.dk/bolig/"

def run_local_test():
    print("Starter usynlig browser for Kereby...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        page.goto(TEST_URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(5000)  # Giver siden tid til at loade bolig-kortene
        
        html = page.content()
        browser.close()
        
        print(f"✅ Siden er hentet! Læste {len(html)} tegn HTML.")
        
        # Vi støvsuger siden for alle links
        all_links = set(re.findall(r'href="([^"]+)"', html))
        
        # Vi leder specifikt efter de dyre boliger på dit screenshot for at finde nålen i høstakken
        bolig_links = [l for l in all_links if "strandboulevarden" in l.lower() or "sortendam" in l.lower() or "gersonsvej" in l.lower()]
        
        if bolig_links:
            print("\n✅ Fandt boligerne! Deres nye URL-struktur ser sådan her ud:")
            for l in bolig_links:
                print(" -", l)
        else:
            print("\n❌ Fandt dem ikke. Kereby skjuler dem sandsynligvis i et API ligesom Findbolig. Her er de 15 første links på siden:")
            for l in list(all_links)[:15]:
                print(" -", l)

if __name__ == "__main__":
    run_local_test()