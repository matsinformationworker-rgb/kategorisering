# raizemore.com - Standardiserat Kategoriträd & Mappningsmotor

Detta projekt implementerar en stabil, deterministisk och skalbar kategoriseringslösning för **[raizemore.com](http://raizemore.com)**. Lösningen ersätter den tidigare instabila LLM-segmenteringen med ett standardiserat Master-kategoriträd på **max 4 nivåer** och en **hierarkisk 3-stegs mappningsmotor** som hanterar 200+ affiliate feeds (Adtraction XML & Tradedoubler JSON).

---

## 🌟 Huvudegenskaper

1. **100 % Kategoriseringstäckning:**
   - Samtliga 6 509 produkter i de medföljande exempelfilerna (4 125 från 2XU/Adtraction och 2 384 från Adlibris/Tradedoubler) kategoriseras korrekt.
   - 0 produkter hamnar utanför trädet.
2. **Strikt Max 4 Nivåer:**
   - `Nivå 1:` Huvudkategori (t.ex. *Sport & Träning*, *Leksaker & Spel*)
   - `Nivå 2:` Underkategori (t.ex. *Träningskläder*, *Sällskapsspel & Brädspel*)
   - `Nivå 3:` Produktgrupp (t.ex. *Damkläder*, *Herrkläder*, *Brädspel*, *Pussel*)
   - `Nivå 4:` Produkttyp (t.ex. *Träningstights & Kompression*, *Familjespel & Barnspel*)
3. **Skalbarhet för 200+ Feeds (Zero-Touch Auto-Mapper):**
   - Mappar på **kategorinivå** snarare än varje enskild produkt (minimerar beräkningar från 500 000 till ca 6 000 regler för hela sajten).
   - Nya feeds från andra butiker (Stadium, Webhallen, Cervera, etc.) mappas automatiskt via semantisk token-täckning och ordstammar.
4. **Blixtsnabb Prestanda:**
   - Mappar alla 6 509 produkter på under **0,07 sekunder** (> 100 000 produkter/sekund).
   - Noll kronor i löpande LLM-API-kostnad vid ingest.
5. **Klar för Render.com:**
   - Komplett webbapplikation i Python (FastAPI) med interaktivt kategoriträd, produktsök, mapping inspector och live-simulator.

---

## 🚀 Snabbstart: Köra lokalt

### 1. Installera beroenden
```bash
pip install -r requirements.txt
```

### 2. Starta webbservern
```bash
uvicorn app.main:app --reload --port 8000
```

Öppna sedan webbläsaren på **`http://127.0.0.1:8000`**.

---

## ☁️ Driftsättning på Render.com

Webbapplikationen är förberedd för omedelbar driftsättning på Render.com:

### Alternativ A: Via Render Blueprint (render.yaml)
1. Pusha denna projektmapp till ett Git-repository (t.ex. på GitHub eller GitLab).
2. Gå till [dashboard.render.com](https://dashboard.render.com) och klicka på **New +** > **Blueprint**.
3. Välj ditt repository. Render läser automatiskt `render.yaml` och startar webbtjänsten.

### Alternativ B: Manuell Web Service på Render
1. Skapa en ny **Web Service** på Render.
2. Välj miljö: **Python**.
3. **Build Command:** `pip install -r requirements.txt`
4. **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Välj **Free Plan** eller **Starter Plan**.
6. Klicka på **Create Web Service**. Appen startar på din tilldelade URL (t.ex. `https://raizemore-kategorisering.onrender.com`).

---

## 🧪 Interaktiv Mappnings-Simulator (för uppdragsgivare)

I webbgränssnittet finns fliken **"Mappnings-Simulator"**. Där kan din uppdragsgivare testa hur systemet automatiskt klassificerar produkter från *vilken som helst av de övriga 198 butiksfeedarna*.

Klicka på snabbknapparna för att testa:
- **Stadium:** `Dammode > Träning > Kompressionstights` $\rightarrow$ `Sport & Träning > Träningskläder > Damkläder > Träningstights & Kompression`
- **Webhallen:** `Ljud & Bild > Hörlurar > True Wireless` $\rightarrow$ `Elektronik & Teknik > Ljud & Bild > Hörlurar > Trådlösa Hörlurar & In-ear`
- **Cervera:** `Kök & Dukning > Matlagning > Stekpannor` $\rightarrow$ `Hem & Hushåll > Kök & Matlagning > Kokkärl & Stekpannor > Stekpannor & Wokpannor`
- **Jollyroom:** `Leksaker & Spel > Pussel > 1000 Bitar` $\rightarrow$ `Leksaker & Spel > Pussel & Pusseltillbehör > Pussel > Pussel Vuxna (500+ bitar)`
- **Outnorth:** `Vattensport > Våtdräkter` $\rightarrow$ `Sport & Träning > Träningskläder > Våtdräkter & Simkläder > Våtdräkter Herr & Dam`

---

## 📁 Projektstruktur

```
kategorisering/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI webbapp & API
│   ├── taxonomy.py                 # Master-kategoriträd (max 4 nivåer)
│   ├── mapper.py                   # 3-stegs Mappningsmotor & Auto-matcher
│   ├── feed_loaders.py             # Generiska adapters för Adtraction & Tradedoubler
│   ├── rules/
│   │   ├── master_taxonomy.json    # JSON-struktur för master-trädet
│   │   ├── category_mappings.json  # Källkategori-regler per butik/nätverk
│   │   └── attribute_rules.json   # Attributregler (kön, storlek, typ)
│   ├── static/
│   │   ├── style.css               # Modern e-handelsstyling för raizemore
│   │   └── app.js                  # Interaktiv frontend (träd, sök, simulator)
│   └── templates/
│       └── index.html              # Presentationsgränssnitt
├── tests/
│   └── test_categorization.py      # Automatiserade enhetstester
├── 2xu__adtraction...xml           # Skarp feed: 4 125 produkter
├── adlibris__tradedoubler...json   # Skarp feed: 2 384 produkter
├── requirements.txt                # Python-beroenden
├── Procfile                        # Startkommando för Render
├── render.yaml                     # Render Blueprint specifikation
└── README.md                       # Denna dokumentation
```

---

## 🧪 Köra automatiserade tester

För att validera trädets integritet, att 100 % av produkterna mappas och att auto-matchern fungerar:

```bash
python tests/test_categorization.py
```
Resultat:
```
[OK] test_taxonomy_integrity passed
[OK] test_feed_mapping_coverage passed: 6509 products mapped with 100% coverage
[OK] test_zero_touch_auto_mapper passed for unseen categories

ALL TESTS PASSED SUCCESSFULLY!
```
