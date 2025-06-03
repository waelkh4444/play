import asyncio
import gspread
import gspread.utils
from flask import Flask, request, jsonify
from playwright.async_api import async_playwright
import os
import json

app = Flask(__name__)

# Connexion à Google Sheet
creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
creds_dict = json.loads(creds_json)
gc = gspread.service_account_from_dict(creds_dict)
sh = gc.open("base_insee")
worksheet = sh.sheet1
headers = worksheet.row_values(1)
siren_col = headers.index("siren")
dirigeant_col = headers.index("Nom_dirigeant")
ca_col = headers.index("Chiffre_daffaire")

async def get_infogreffe_info(siren):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            url = f"https://www.infogreffe.fr/entreprise/{siren}"
            await page.goto(url, timeout=15000)
            await page.wait_for_timeout(5000)

            try:
                dirigeant_elem = await page.query_selector(
                    "//div[@data-testid='block-representant-legal']//div[contains(@class, 'textData')]"
                )
                dirigeant = await dirigeant_elem.inner_text() if dirigeant_elem else "Non trouvé"
            except:
                dirigeant = "Non trouvé"

            try:
                ca_elem = await page.query_selector("div[data-testid='ca']")
                ca = await ca_elem.inner_text() if ca_elem else "Non trouvé"
            except:
                ca = "Non trouvé"

        except Exception as e:
            print(f"❌ Erreur {siren} : {str(e)}")
            dirigeant, ca = "Non trouvé", "Non trouvé"
        finally:
            await page.close()
            await browser.close()

        return dirigeant, ca

@app.route('/scrape', methods=['POST'])
async def scrape_all_missing():
    updates = []
    rows = worksheet.get_all_values()
    count = 0

    for i, row in enumerate(rows[1:], start=2):
        if count >= 8:
            break

        siren = row[siren_col] if len(row) > siren_col else ""
        dirigeant_val = row[dirigeant_col] if len(row) > dirigeant_col else ""
        ca_val = row[ca_col] if len(row) > ca_col else ""

        if not siren or dirigeant_val or ca_val:
            continue

        print(f"🔍 Traitement {siren}")
        dirigeant, ca = await get_infogreffe_info(siren)
        print(f"✅ À mettre à jour : ligne {i} → {dirigeant} | {ca}")

        updates.append({
            'range': gspread.utils.rowcol_to_a1(i, dirigeant_col + 1),
            'values': [[dirigeant or "Non trouvé"]]
        })
        updates.append({
            'range': gspread.utils.rowcol_to_a1(i, ca_col + 1),
            'values': [[ca or "Non trouvé"]]
        })

        count += 1

        # ✅ Pause 2 seconde pour soulager la RAM
        await asyncio.sleep(2)

    if updates:
        worksheet.batch_update(updates)
        return jsonify({
            "message": f"{count} lignes mises à jour.",
            "status": "success",
            "updates": count
        })
    else:
        return jsonify({
            "message": "Aucune mise à jour nécessaire.",
            "status": "success",
            "updates": 0
        })
