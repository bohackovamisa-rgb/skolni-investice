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

# Slovník: NÁZEV -> (TICKER NA BURZE, MĚNA, NÁZEV SLOUPCE V TABULCE)
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
                    st.session_state["zustatek"] = float(radek["Zustatek"])
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
    
    st.subheader("📈 Trh s aktivy")
    
    vybrane_aktivum = st.selectbox("Vyber aktivum, které tě zajímá:", list(AKTIVA.keys()))
    ticker_symbol, mena, sloupec_db = AKTIVA[vybrane_aktivum]
    
    with st.spinner(f"Stahuji živá data pro {vybrane_aktivum}..."):
        try:
            # 1. Zjištění kurzu
            if mena == "USD":
                kurz_usd_czk = yf.Ticker("CZK=X").history(period="1d")['Close'].iloc[-1]
            else:
                kurz_usd_czk = 1.0
            
            # 2. Stažení dat a přepočet
            data_aktiva = yf.Ticker(ticker_symbol)
            historie = data_aktiva.history(period="1mo")['Close']
            historie_czk = historie * kurz_usd_czk
            aktualni_cena = float(historie_czk.iloc[-1])
            
            st.info(f"📊 **{vybrane_aktivum}**: Aktuální cena **{aktualni_cena:.2f} Kč**")
            st.line_chart(historie_czk)
            
            # 3. Formulář pro NÁKUP
            st.write(f"### 🛒 Koupit {vybrane_aktivum}")
            pocet = st.number_input(f"Kolik kusů chceš koupit?", min_value=1.0, step=1.0, value=1.0)
            cena_celkem = pocet * aktualni_cena
            st.write(f"Celková cena: **{cena_celkem:.2f} Kč**")
            
            if st.button(f"Potvrdit nákup ({pocet} ks)"):
                if st.session_state["zustatek"] >= cena_celkem:
                    with st.spinner("Zapisuji transakci do banky..."):
                        # Najdeme řádek uživatele a sloupec aktiva
                        jmena_sloupec = db.col_values(1)
                        cislo_radku = jmena_sloupec.index(st.session_state["jmeno"]) + 1
                        
                        hlavicky = db.row_values(1)
                        cislo_sloupce_aktiva = hlavicky.index(sloupec_db) + 1
                        cislo_sloupce_zustatek = 3 # Zůstatek je vždy 3. sloupec
                        
                        # Přečteme, kolik toho má žák teď (pokud je buňka prázdná, dáme 0)
                        stav_aktiva_str = db.cell(cislo_radku, cislo_sloupce_aktiva).value
                        stav_aktiva_ted = float(stav_aktiva_str.replace(",", ".")) if stav_aktiva_str else 0.0
                        
                        # Spočítáme nové hodnoty
                        novy_zustatek = st.session_state["zustatek"] - cena_celkem
                        novy_stav_aktiva = stav_aktiva_ted + pocet
                        
                        # Zapíšeme do Googlu
                        db.update_cell(cislo_radku, cislo_sloupce_zustatek, novy_zustatek)
                        db.update_cell(cislo_radku, cislo_sloupce_aktiva, novy_stav_aktiva)
                        
                        # Aktualizujeme paměť a obnovíme
                        st.session_state["zustatek"] = novy_zustatek
                        st.success("✅ Nákup úspěšně proběhl!")
                        st.rerun()
                else:
                    st.error("❌ Na tento nákup nemáš dostatek prostředků.")
                    
        except Exception as e:
            st.warning(f"Chyba při stahování dat: {e}")
