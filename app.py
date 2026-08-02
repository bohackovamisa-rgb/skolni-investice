import streamlit as st
import yfinance as yf
import gspread
import json

st.set_page_config(page_title="Investiční simulátor", layout="centered")

# --- 1. PAMĚŤ APLIKACE (SESSION STATE) ---
# Toto zajistí, že si aplikace pamatuje, kdo je přihlášený
if "prihlasen" not in st.session_state:
    st.session_state["prihlasen"] = False
    st.session_state["jmeno"] = ""
    st.session_state["zustatek"] = 0

# --- 2. PŘIPOJENÍ K DATABÁZI ---
@st.cache_resource
def pripojit_databazi():
    tajemstvi = json.loads(st.secrets["google_credentials"])
    client = gspread.service_account_from_dict(tajemstvi)
    sheet = client.open("Skolni_Investice_DB").sheet1
    return sheet

try:
    db = pripojit_databazi()
except Exception as e:
    st.error(f"❌ Chyba při připojování databáze: {e}")
    st.stop()

# ==========================================
# --- A: OBRAZOVKA PRO NEPŘIHLÁŠENÉ ---
# ==========================================
if not st.session_state["prihlasen"]:
    st.title("📈 Školní investiční simulátor")
    tab1, tab2 = st.tabs(["🔐 Přihlášení", "📝 Nová registrace"])

    with tab1:
        st.subheader("Přihlášení")
        login_jmeno = st.text_input("Jméno (přesně jako v tabulce):")
        login_pin = st.text_input("PIN:", type="password")

        if st.button("Přihlásit se"):
            zaznamy = db.get_all_records()
            nalezen = False
            for radek in zaznamy:
                if str(radek["Jmeno"]) == login_jmeno and str(radek["PIN"]) == login_pin:
                    nalezen = True
                    # Uložíme údaje do paměti a obnovíme stránku
                    st.session_state["prihlasen"] = True
                    st.session_state["jmeno"] = login_jmeno
                    st.session_state["zustatek"] = radek["Zustatek"]
                    st.rerun() # Toto příkazem znovu načte aplikaci s přihlášeným uživatelem
            
            if not nalezen:
                st.error("Chybné jméno nebo PIN.")

    with tab2:
        st.subheader("Nová registrace")
        reg_jmeno = st.text_input("Tvé jméno:")
        reg_pin = st.text_input("Vymysli si PIN:", type="password")
        if st.button("Zaregistrovat"):
            zaznamy = db.get_all_records()
            jmena = [str(r["Jmeno"]) for r in zaznamy]
            if reg_jmeno in jmena:
                st.error("Toto jméno už existuje.")
            else:
                db.append_row([reg_jmeno, reg_pin, 10000, 0, 0, 0, 0, 0])
                st.success("Účet vytvořen! Nyní se můžeš přihlásit v záložce vedle.")

# ==========================================
# --- B: OBRAZOVKA PRO PŘIHLÁŠENÉ (BURZA) ---
# ==========================================
else:
    # Hlavička s pozdravem a tlačítkem pro odhlášení
    sloupec1, sloupec2 = st.columns([3, 1])
    with sloupec1:
        st.title(f"Vítej, {st.session_state['jmeno']}! 👋")
    with sloupec2:
        if st.button("Odhlásit se"):
            st.session_state["prihlasen"] = False
            st.rerun()

    # Zobrazení aktuálního zůstatku
    st.metric(label="Dostupné prostředky", value=f"{st.session_state['zustatek']} Kč")
    
    st.divider()
    
    # První ukázka živých dat z burzy
    st.subheader("Aktuální ceny na burze")
    
    with st.spinner("Stahuji živá data z Wall Street..."):
        try:
            # Stáhneme aktuální cenu Apple
            apple = yf.Ticker("AAPL")
            cena_usd = apple.history(period="1d")['Close'].iloc[-1]
            # Zjednodušený převod na CZK (např. kurz 23 Kč za dolar)
            cena_czk = int(cena_usd * 23)
            
            st.info(f"🍏 **Apple (AAPL)**: Aktuální cena je **{cena_czk} Kč** za 1 akcii.")
        except Exception as e:
            st.warning("Cenu se nepodařilo načíst, zkus to za chvíli.")

    st.write("*(Tady v dalším kroku přidáme tlačítka pro nákup a prodej!)*")
