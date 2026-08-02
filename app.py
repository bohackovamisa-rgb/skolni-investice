import streamlit as st
import yfinance as yf
import gspread
import json

st.set_page_config(page_title="Investiční simulátor", layout="centered")

# --- POMOCNÉ FUNKCE ---
def bezpecny_float(hodnota):
    try:
        return float(hodnota)
    except (ValueError, TypeError):
        return 0.0

def hezke_kusy(hodnota):
    if float(hodnota).is_integer():
        return f"{int(hodnota)}"
    return f"{hodnota}"

# --- PAMĚŤ APLIKACE ---
if "prihlasen" not in st.session_state:
    st.session_state["prihlasen"] = False
    st.session_state["jmeno"] = ""
    st.session_state["zustatek"] = 0.0

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
            zaznamy = db.get_all_records(value_render_option="UNFORMATTED_VALUE")
            nalezen = False
            for radek in zaznamy:
                if str(radek.get("Jmeno", "")) == login_jmeno and str(radek.get("PIN", "")) == login_pin:
                    nalezen = True
                    st.session_state["prihlasen"] = True
                    st.session_state["jmeno"] = login_jmeno
                    st.session_state["zustatek"] = bezpecny_float(radek.get("Zustatek", 0))
                    st.rerun()
            if not nalezen:
                st.error("Chybné jméno nebo PIN.")

    with tab2:
        reg_jmeno = st.text_input("Tvé jméno:")
        reg_pin = st.text_input("Vymysli si PIN:", type="password")
        if st.button("Zaregistrovat"):
            zaznamy = db.get_all_records(value_render_option="UNFORMATTED_VALUE")
            if reg_jmeno in [str(r.get("Jmeno", "")) for r in zaznamy]:
                st.error("Toto jméno už existuje.")
            else:
                # Noví žáci dostanou do startu 20 000 Kč
                db.append_row([reg_jmeno, reg_pin, 20000.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
                st.success("Účet vytvořen s částkou 20 000 Kč! Nyní se můžeš přihlásit.")

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

    st.divider()
    tab_burza, tab_portfolio = st.tabs(["📈 Burza (Nákup/Prodej)", "💼 Moje Portfolio"])
    
    vsechna_data = db.get_all_records(value_render_option="UNFORMATTED_VALUE")
    moje_data = next((r for r in vsechna_data if str(r.get("Jmeno", "")) == st.session_state["jmeno"]), None)
    
    # ---------------- ZÁLOŽKA: BURZA ----------------
    with tab_burza:
        st.metric(label="Dostupné peníze na účtu", value=f"{st.session_state['zustatek']:.2f} Kč")
        
        vybrane_aktivum = st.selectbox("Vyber aktivum, které tě zajímá:", list(AKTIVA.keys()))
        ticker_symbol, mena, sloupec_db = AKTIVA[vybrane_aktivum]
        
        with st.spinner(f"Stahuji živá data pro {vybrane_aktivum}..."):
            try:
                if mena == "USD":
                    kurz_usd_czk = yf.Ticker("CZK=X").history(period="1d")['Close'].iloc[-1]
                else:
                    kurz_usd_czk = 1.0
                
                historie = yf.Ticker(ticker_symbol).history(period="1mo")['Close']
                historie_czk = historie * kurz_usd_czk
                aktualni_cena = round(float(historie_czk.iloc[-1]), 2)
                
                st.info(f"📊 **{vybrane_aktivum}**: Aktuální cena **{aktualni_cena:.2f} Kč**")
                st.line_chart(historie_czk)
                
                je_krypto = vybrane_aktivum in ["Bitcoin", "Ethereum"]
                if je_krypto:
                    st.warning("💡 **Tip do výuky:** Kryptoměny jsou drahé. Nemusíš ale kupovat celý kus! V políčku níže zadej jen malou část (např. `0.05` nebo `0.002`).")
                    krok_formulare = 0.001
                    format_cisla = "%.4f"
                else:
                    krok_formulare = 1.0
                    format_cisla = "%.2f"
                
                stav_aktiva_ted = bezpecny_float(moje_data.get(sloupec_db, 0)) if moje_data else 0.0

                col_nakup, col_prodej = st.columns(2)
                
                with col_nakup:
                    st.write("### 🛒 Koupit")
                    pocet_koupit = st.number_input("Kusů ke koupi", min_value=0.0, step=krok_formulare, format=format_cisla, value=0.0, key="nakup")
                    cena_koupit = round(pocet_koupit * aktualni_cena, 2)
                    st.write(f"Celková cena: **{cena_koupit:.2f} Kč**")
                    
                    if st.button("Potvrdit nákup"):
                        if pocet_koupit > 0:
                            if st.session_state["zustatek"] >= cena_koupit:
                                with st.spinner("Zapisuji do databáze..."):
                                    novy_zustatek = round(st.session_state["zustatek"] - cena_koupit, 2)
                                    novy_stav_aktiva = round(stav_aktiva_ted + pocet_koupit, 4)
                                    
                                    jmena_sloupec = db.col_values(1)
                                    cislo_radku = jmena_sloupec.index(st.session_state["jmeno"]) + 1
                                    hlavicky = db.row_values(1)
                                    cislo_sloupce_aktiva = hlavicky.index(sloupec_db) + 1
                                    
                                    db.update_cell(cislo_radku, 3, novy_zustatek) 
                                    db.update_cell(cislo_radku, cislo_sloupce_aktiva, novy_stav_aktiva)
                                    
                                    st.session_state["zustatek"] = novy_zustatek
                                    st.success("✅ Nákup proběhl úspěšně!")
                                    st.rerun()
                            else:
                                st.error("❌ Nemáš dostatek prostředků.")
                
                with col_prodej:
                    st.write("### 💰 Prodat")
                    st.write(f"Vlastníš: **{hezke_kusy(stav_aktiva_ted)} ks**")
                    pocet_prodat = st.number_input("Kusů k prodeji", min_value=0.0, max_value=float(stav_aktiva_ted) if stav_aktiva_ted > 0 else 0.0, step=krok_formulare, format=format_cisla, value=0.0, key="prodej")
                    cena_prodat = round(pocet_prodat * aktualni_cena, 2)
                    st.write(f"Získáš: **{cena_prodat:.2f} Kč**")
                    
                    if st.button("Potvrdit prodej"):
                        if pocet_prodat > 0 and pocet_prodat <= stav_aktiva_ted:
                            with st.spinner("Zapisuji do databáze..."):
                                novy_zustatek = round(st.session_state["zustatek"] + cena_prodat, 2)
                                novy_stav_aktiva = round(stav_aktiva_ted - pocet_prodat, 4)
                                
                                jmena_sloupec = db.col_values(1)
                                cislo_radku = jmena_sloupec.index(st.session_state["jmeno"]) + 1
                                hlavicky = db.row_values(1)
                                cislo_sloupce_aktiva = hlavicky.index(sloupec_db) + 1
                                
                                db.update_cell(cislo_radku, 3, novy_zustatek)
                                db.update_cell(cislo_radku, cislo_sloupce_aktiva, novy_stav_aktiva)
                                
                                st.session_state["zustatek"] = novy_zustatek
                                st.success("✅ Prodej proběhl úspěšně!")
                                st.rerun()

            except Exception as e:
                st.warning(f"Chyba při stahování dat: {e}")

    # ---------------- ZÁLOŽKA: PORTFOLIO ----------------
    with tab_portfolio:
        st.subheader("💼 Tvůj majetek")
        
        if moje_data:
            with st.spinner("Oceňuji tvůj majetek podle aktuálních kurzů..."):
                try:
                    kurz_usd_czk = yf.Ticker("CZK=X").history(period="1d")['Close'].iloc[-1]
                except:
                    kurz_usd_czk = 23.0 
                
                hodnota_aktiv_celkem = 0.0
                ma_neco = False
                
                st.write("**Aktuálně držíš tyto cenné papíry a krypto:**")
                
                for nazev, (ticker_symbol, mena, db_sloupec) in AKTIVA.items():
                    mnozstvi = bezpecny_float(moje_data.get(db_sloupec, 0))
                    if mnozstvi > 0:
                        ma_neco = True
                        try:
                            cena_aktiva = yf.Ticker(ticker_symbol).history(period="1d")['Close'].iloc[-1]
                            if mena == "USD":
                                cena_aktiva *= kurz_usd_czk
                                
                            hodnota_polozky = round(mnozstvi * cena_aktiva, 2)
                            hodnota_aktiv_celkem += hodnota_polozky
                            
                            st.write(f"🔸 **{nazev}**: {hezke_kusy(mnozstvi)} ks *(hodnota cca {hodnota_polozky:.2f} Kč)*")
                        except:
                            st.write(f"🔸 **{nazev}**: {hezke_kusy(mnozstvi)} ks *(cenu nelze právě teď načíst)*")
                
                if not ma_neco:
                    st.info("Zatím nic nevlastníš. Běž na burzu a udělej svůj první obchod!")
                
                st.divider()
                
                celkovy_majetek = round(st.session_state["zustatek"] + hodnota_aktiv_celkem, 2)
                # Zisk/Ztráta se po úpravě počítá oproti 20 000 Kč
                zisk_ztrata = round(celkovy_majetek - 20000.0, 2)
                
                st.metric(
                    label="🏆 CELKOVÁ HODNOTA MAJETKU", 
                    value=f"{celkovy_majetek:.2f} Kč", 
                    delta=f"{zisk_ztrata:.2f} Kč od začátku"
                )
