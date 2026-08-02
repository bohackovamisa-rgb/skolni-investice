import streamlit as st
import yfinance as yf
import gspread
import json

st.set_page_config(page_title="Investiční simulátor", layout="centered")

# --- PAMĚŤ APLIKACE ---
if "prihlasen" not in st.session_state:
    st.session_state["prihlasen"] = False
    st.session_state["jmeno"] = ""
    st.session_state["zustatek"] = 0

# --- PŘIPOJENÍ K DATABÁZI ---
@st.cache_resource
def pripojit_databazi():
    tajemstvi = json.loads(st.secrets["google_credentials"])
    client = gspread.service_account_from_dict(tajemstvi)
    return client.open("Skolni_Investice_DB").sheet1

try:
    db = pripojit_databazi()
except Exception as e:
    st.error(f"❌ Chyba při připojování databáze: {e}")
    st.stop()

# Slovník: NÁZEV -> (TICKER, MĚNA, NÁZEV SLOUPCE)
AKTIVA = {
    "Apple": ("AAPL", "USD", "AAPL"),
    "Tesla": ("TSLA", "USD", "TSLA"),
    "Microsoft": ("MSFT", "USD", "MSFT"),
    "Google": ("GOOGL", "USD", "GOOGL"),
    "Amazon": ("AMZN", "USD", "AMZN"),
    "Nvidia": ("NVDA", "USD", "NVDA"),
    "Meta (Facebook)": ("META", "USD", "META"),
    "ČEZ": ("CEZ.PR", "CZK", "CEZ"),
    "Bitcoin": ("BTC-USD", "USD", "BTC"),
    "Ethereum": ("ETH-USD", "USD", "ETH")
}

# ==========================================
# --- A: OBRAZOVKA PRO NEPŘIHLÁŠENÉ ---
# ==========================================
if not st.session_state["prihlasen"]:
    st.title("📈 Školní investiční simulátor")
    tab1, tab2 = st.tabs(["🔐 Přihlášení", "📝 Nová registrace"])

    with tab1:
        login_jmeno = st.text_input("Jméno (přesně jako v tabulce):")
        login_pin = st.text_input("PIN:", type="password")
        if st.button("Přihlásit se"):
            zaznamy = db.get_all_records()
            nalezen = False
            for radek in zaznamy:
                if str(radek["Jmeno"]) == login_jmeno and str(radek["PIN"]) == login_pin:
                    nalezen = True
                    st.session_state["prihlasen"] = True
                    st.session_state["jmeno"] = login_jmeno
                    st.session_state["zustatek"] = float(str(radek["Zustatek"]).replace(",", "."))
                    st.rerun()
            if not nalezen:
                st.error("Chybné jméno nebo PIN.")

    with tab2:
        reg_jmeno = st.text_input("Tvé jméno:")
        reg_pin = st.text_input("Vymysli si PIN:", type="password")
        if st.button("Zaregistrovat"):
            zaznamy = db.get_all_records()
            if reg_jmeno in [str(r["Jmeno"]) for r in zaznamy]:
                st.error("Toto jméno už existuje.")
            else:
                db.append_row([reg_jmeno, reg_pin, 10000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
                st.success("Účet vytvořen! Nyní se můžeš přihlásit.")

# ==========================================
# --- B: OBRAZOVKA PRO PŘIHLÁŠENÉ (BURZA) ---
# ==========================================
else:
    sloupec1, sloupec2 = st.columns([3, 1])
    with sloupec1:
        st.title(f"Vítej, {st.session_state['jmeno']}! 👋")
    with sloupec2:
        if st.button("Odhlásit se"):
            st.session_state["prihlasen"] = False
            st.rerun()

    st.metric(label="Dostupné prostředky", value=f"{st.session_state['zustatek']:.2f} Kč")
    st.divider()
    
    # NOVINKA: Záložky i pro přihlášeného uživatele
    tab_burza, tab_portfolio = st.tabs(["📈 Burza (Nákup/Prodej)", "💼 Moje Portfolio"])
    
    # ---------------- ZÁLOŽKA: BURZA ----------------
    with tab_burza:
        vybrane_aktivum = st.selectbox("Vyber aktivum, které tě zajímá:", list(AKTIVA.keys()))
        ticker_symbol, mena, sloupec_db = AKTIVA[vybrane_aktivum]
        
        with st.spinner(f"Stahuji živá data pro {vybrane_aktivum}..."):
            try:
                # 1. Kurz a data
                if mena == "USD":
                    kurz_usd_czk = yf.Ticker("CZK=X").history(period="1d")['Close'].iloc[-1]
                else:
                    kurz_usd_czk = 1.0
                
                historie = yf.Ticker(ticker_symbol).history(period="1mo")['Close']
                historie_czk = historie * kurz_usd_czk
                aktualni_cena = float(historie_czk.iloc[-1])
                
                st.info(f"📊 **{vybrane_aktivum}**: Aktuální cena **{aktualni_cena:.2f} Kč**")
                st.line_chart(historie_czk)
                
                # Zjištění, kolik toho žák teď má (načítáme vždy aktuálně z tabulky)
                jmena_sloupec = db.col_values(1)
                cislo_radku = jmena_sloupec.index(st.session_state["jmeno"]) + 1
                hlavicky = db.row_values(1)
                cislo_sloupce_aktiva = hlavicky.index(sloupec_db) + 1
                
                stav_aktiva_str = db.cell(cislo_radku, cislo_sloupce_aktiva).value
                stav_aktiva_ted = float(stav_aktiva_str.replace(",", ".")) if stav_aktiva_str else 0.0

                # Dva sloupce: Nákup vedle Prodeje
                col_nakup, col_prodej = st.columns(2)
                
                with col_nakup:
                    st.write("### 🛒 Koupit")
                    pocet_koupit = st.number_input("Kusů ke koupi", min_value=0.0, step=1.0, value=0.0, key="nakup")
                    cena_koupit = pocet_koupit * aktualni_cena
                    st.write(f"Celková cena: **{cena_koupit:.2f} Kč**")
                    
                    if st.button("Potvrdit nákup"):
                        if pocet_koupit > 0:
                            if st.session_state["zustatek"] >= cena_koupit:
                                with st.spinner("Zapisuji do databáze..."):
                                    novy_zustatek = st.session_state["zustatek"] - cena_koupit
                                    db.update_cell(cislo_radku, 3, novy_zustatek) # Sloupec 3 = Zůstatek
                                    db.update_cell(cislo_radku, cislo_sloupce_aktiva, stav_aktiva_ted + pocet_koupit)
                                    st.session_state["zustatek"] = novy_zustatek
                                    st.success("✅ Nákup proběhl úspěšně!")
                                    st.rerun()
                            else:
                                st.error("❌ Nemáš dostatek prostředků.")
                
                with col_prodej:
                    st.write("### 💰 Prodat")
                    st.write(f"Vlastníš: **{stav_aktiva_ted} ks**")
                    pocet_prodat = st.number_input("Kusů k prodeji", min_value=0.0, max_value=float(stav_aktiva_ted) if stav_aktiva_ted > 0 else 0.0, step=1.0, value=0.0, key="prodej")
                    cena_prodat = pocet_prodat * aktualni_cena
                    st.write(f"Získáš: **{cena_prodat:.2f} Kč**")
                    
                    if st.button("Potvrdit prodej"):
                        if pocet_prodat > 0 and pocet_prodat <= stav_aktiva_ted:
                            with st.spinner("Zapisuji do databáze..."):
                                novy_zustatek = st.session_state["zustatek"] + cena_prodat
                                db.update_cell(cislo_radku, 3, novy_zustatek)
                                db.update_cell(cislo_radku, cislo_sloupce_aktiva, stav_aktiva_ted - pocet_prodat)
                                st.session_state["zustatek"] = novy_zustatek
                                st.success("✅ Prodej proběhl úspěšně!")
                                st.rerun()

            except Exception as e:
                st.warning(f"Chyba při stahování dat: {e}")

    # ---------------- ZÁLOŽKA: PORTFOLIO ----------------
    with tab_portfolio:
        st.subheader("V tvém sejfu se aktuálně nachází:")
        
        # Stáhneme celou tabulku a najdeme data přihlášeného uživatele
        vsechna_data = db.get_all_records()
        moje_data = None
        for r in vsechna_data:
            if str(r["Jmeno"]) == st.session_state["jmeno"]:
                moje_data = r
                break
                
        if moje_data:
            ma_neco = False
            for nazev, (_, _, db_sloupec) in AKTIVA.items():
                # Získáme množství z tabulky a převedeme na číslo
                mnozstvi = float(str(moje_data.get(db_sloupec, 0)).replace(",", "."))
                if mnozstvi > 0:
                    ma_neco = True
                    st.write(f"🔸 **{nazev}**: {mnozstvi} ks")
            
            if not ma_neco:
                st.info("Tvé portfolio je zatím prázdné. Běž na burzu a nakup své první akcie nebo krypto!")
