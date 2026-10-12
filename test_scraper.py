import urllib.request
import urllib.error
import urllib.parse
import ssl
import re

# Sæt den URL ind, du vil teste (f.eks. Propstep eller Kereby)
TEST_URL = "https://propstep.com/da-DK/soeg?viewportCoordinates=%7B%22center%22%3A%7B%22coordinates%22%3A%5B12.582808189482762%2C55.68064645900864%5D%7D%2C%22northEast%22%3A%7B%22coordinates%22%3A%5B12.72430087%2C55.72946145%5D%7D%2C%22southWest%22%3A%7B%22coordinates%22%3A%5B12.512808189482762%2C55.64064645900864%5D%7D%2C%22location%22%3A%7B%22city%22%3A%22K%C3%B8benhavn+K%22%2C%22zipCode%22%3A%221050%2C1051%2C1052%2C1053%2C1054%2C1055%2C1056%2C1057%2C1058%2C1059%2C1060%2C1061%2C1062%2C1063%2C1064%2C1065%2C1066%2C1067%2C1068%2C1069%2C1070%2C1071%2C1072%2C1073%2C1074%2C1100%2C1101%2C1102%2C1103%2C1104%2C1105%2C1106%2C1107%2C1110%2C1111%2C1112%2C1113%2C1114%2C1115%2C1116%2C1117%2C1118%2C1119%2C1120%2C1121%2C1122%2C1123%2C1124%2C1125%2C1126%2C1127%2C1128%2C1129%2C1130%2C1131%2C1150%2C1151%2C1152%2C1153%2C1154%2C1155%2C1156%2C1157%2C1158%2C1159%2C1160%2C1161%2C1162%2C1164%2C1165%2C1166%2C1167%2C1168%2C1169%2C1170%2C1171%2C1172%2C1173%2C1174%2C1175%2C1200%2C1201%2C1202%2C1203%2C1204%2C1205%2C1206%2C1207%2C1208%2C1209%2C1210%2C1211%2C1212%2C1213%2C1214%2C1215%2C1216%2C1218%2C1219%2C1220%2C1221%2C1250%2C1251%2C1252%2C1253%2C1254%2C1255%2C1256%2C1257%2C1259%2C1260%2C1261%2C1263%2C1264%2C1265%2C1266%2C1267%2C1268%2C1270%2C1271%2C1300%2C1301%2C1302%2C1303%2C1304%2C1306%2C1307%2C1308%2C1309%2C1310%2C1311%2C1312%2C1313%2C1314%2C1315%2C1316%2C1317%2C1318%2C1319%2C1320%2C1321%2C1322%2C1323%2C1324%2C1325%2C1326%2C1327%2C1328%2C1329%2C1350%2C1352%2C1353%2C1354%2C1355%2C1356%2C1357%2C1358%2C1359%2C1360%2C1361%2C1362%2C1363%2C1364%2C1365%2C1366%2C1367%2C1368%2C1369%2C1370%2C1371%2C1400%2C1401%2C1402%2C1403%2C1406%2C1407%2C1408%2C1409%2C1410%2C1411%2C1412%2C1413%2C1414%2C1415%2C1416%2C1417%2C1418%2C1419%2C1420%2C1421%2C1422%2C1423%2C1424%2C1425%2C1426%2C1427%2C1428%2C1429%2C1430%2C1432%2C1433%2C1434%2C1435%2C1436%2C1437%2C1438%2C1439%2C1440%2C1441%2C1450%2C1451%2C1452%2C1453%2C1454%2C1455%2C1456%2C1457%2C1458%2C1459%2C1460%2C1461%2C1462%2C1463%2C1464%2C1465%2C1466%2C1467%2C1468%2C1470%2C1471%2C1472%2C1473%22%2C%22label%22%3A%221050-1473+K%C3%B8benhavn+K%22%7D%7D&priceMax=20000&roomsMin=2&propertyTypes=%5B1%5D&radius=5&page=1&zipCodes=1050..."

# Vælg det regex, der passer til siden (her sat op til Propstep som eksempel)
REGEX_PATTERN = r'href="(/da-DK/bolig/[^"]+)"'

def run_test():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(TEST_URL, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })

    print(f"Tester forbindelsen til: {TEST_URL[:60]}...\n")
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            html = resp.read().decode("utf-8", errors="replace")
            print(f"✅ Siden svarede (Kode {resp.getcode()}). Hentede {len(html)} tegn HTML.")
            
            links = set(re.findall(REGEX_PATTERN, html))
            print(f"🔗 Fandt {len(links)} match på dit regex.")
            
            if links:
                print("Eksempler på fundne links:")
                for l in list(links)[:5]:
                    print(" -", l)
            else:
                print("\n⚠️ ADVARSEL: Fandt INGEN links. Koden ser dette:")
                # Printer starten og slutningen af koden for at bevise, at siden er tom for boliger (React-skal)
                print(html[:500])
                print("...\n[KLIP]\n...")
                print(html[-500:])
                
    except urllib.error.HTTPError as e:
        print(f"❌ BLOKERET: Serveren smed os af med HTTP {e.code}. Dette kræver fallback.")
    except Exception as e:
        print(f"❌ Kritis fejl: {e}")

if __name__ == "__main__":
    run_test()