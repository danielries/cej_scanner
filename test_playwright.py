import json
from playwright.sync_api import sync_playwright

# Dit præcise link med Frederiksberg, Ø, N, V og K
TEST_URL = "https://www.findbolig.nu/da-dk/find?Commune=Frederiksberg&Rent=0%2C45000&Rooms=0%2C10&Area=0%2C500&Floor=0%2C20&PropertyYear=1900%2C2026&City=K%C3%B8benhavn+%C3%98%2CK%C3%B8benhavn+N%2CK%C3%B8benhavn+V%2CK%C3%B8benhavn+K"

def run_local_test():
    print("Starter netværks-lytter for Findbolig...")
    boliger = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        def handle_response(response):
            if "api/search" in response.url.lower():
                try:
                    data = response.json()
                    if "results" in data:
                        boliger.extend(data["results"])
                        print(f"--> 📡 Fangede usynlig datapakke med {len(data['results'])} boliger!")
                except Exception:
                    pass
                    
        page.on("response", handle_response)
        
        print("Åbner dit specifikke link og venter på deres database...")
        page.goto(TEST_URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)
        
        browser.close()

    print(f"\nFandt i alt {len(boliger)} boliger på første dataside.")
    print("Filtrerer nu lokalt i Python (Postnr 1000-2200, Maks 25.000 kr, min 2 værelser)...\n")

    fundne_boliger = 0
    for b in boliger:
        b_id = str(b.get("id", ""))
        pris = b.get("rent", 999999)
        vaer = b.get("rooms", 0)
        vej = b.get("street", "Ukendt vej")
        by = b.get("postalCodeName", "Ukendt by")
        postnr = b.get("postalCode", 0)
        
        # 1. Postnummer-sikkerhedsnet (blokerer Amager/Nordvest hvis URL'en fejler)
        if not (1000 <= postnr <= 2200):
            continue
            
        # 2. Filter (sat til 25.000 kr. i testen for at se resultater)
        if pris <= 25000 and vaer >= 2:
            fundne_boliger += 1
            link = f"https://www.findbolig.nu/da-dk/bolig/{b_id}"
            print(f"✅ GODKENDT: {vej}, {postnr} {by} | Pris: {pris} kr. | Vær: {vaer}")
            print(f"   Link: {link}\n")
            
    if fundne_boliger == 0:
        print("❌ Filteret sorterede alt fra.")
    else:
        print(f"🎉 Succes! Din Python-kode og postnummer-sikring fandt {fundne_boliger} matchende boliger.")

if __name__ == "__main__":
    run_local_test()