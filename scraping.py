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

            # Dirigeant
            try:
                dirigeant_elem = await page.query_selector(
                    "//div[@data-testid='block-representant-legal']//div[contains(@class, 'textData')]"
                )
                dirigeant = await dirigeant_elem.inner_text() if dirigeant_elem else "Non trouvé"
            except:
                dirigeant = "Non trouvé"

            # Chiffre d'affaires
            try:
                ca_elem = await page.query_selector("div[data-testid='ca']")
                ca = await ca_elem.inner_text() if ca_elem else "Non trouvé"
            except:
                ca = "Non trouvé"

            await browser.close()
            return dirigeant, ca

        except Exception as e:
            await browser.close()
            print(f"❌ Erreur {siren} : {str(e)}")
            return "Erreur", "Erreur"

@app.route('/scrape', methods=['POST'])
async def scrape_all_missing():
    updates = []

    # Lire toutes les lignes
    rows = worksheet.get_all_values()

    for i, row in enumerate(rows[1:], start=2):
        siren = row[siren_col] if len(row) > siren_col else ""
        dirigeant_val = row[dirigeant_col] if len(row) > dirigeant_col else ""
        ca_val = row[ca_col] if len(row) > ca_col else ""

        if not siren or dirigeant_val or ca_val:
            continue

        print(f"🔍 Traitement {siren}")
        dirigeant, ca = await get_infogreffe_info(siren)

        if dirigeant in ["Non trouvé", "Erreur"] and ca in ["Non trouvé", "Erreur"]:
            continue

        print(f"✅ À mettre à jour : ligne {i} → {dirigeant} | {ca}")

        updates.append({
            'range': gspread.utils.rowcol_to_a1(i, dirigeant_col + 1),
            'values': [[dirigeant]]
        })
        updates.append({
            'range': gspread.utils.rowcol_to_a1(i, ca_col + 1),
            'values': [[ca]]
        })

    if updates:
        worksheet.batch_update(updates)
        return jsonify({
            "message": f"{len(updates)//2} lignes mises à jour.",
            "status": "success",
            "updates": len(updates)//2
        })
    else:
        return jsonify({
            "message": "Aucune mise à jour nécessaire.",
            "status": "success",
            "updates": 0
        })
