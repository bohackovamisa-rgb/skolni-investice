import streamlit as st
import yfinance as yf
import gspread
import json

st.set_page_config(page_title="Investiční simulátor", layout="centered")
st.title("📈 Školní investiční simulátor")

# 1. Funkce pro bezpečné připojení k databázi
@st.cache_resource
def pripojit_databazi():
    # Načteme tajný klíč ze Streamlit Secrets
    tajemstvi = json.loads(st.secrets["google_credentials"])
    # Přihlásíme se k bota
    client = gspread.service_account_from_dict(tajemstvi)
    # Otevřeme naši tabulku a vybereme první list
    sheet = client.open("Skolni_Investice_DB").sheet1
    return sheet

# Spustíme připojení
try:
    db = pripojit_databazi()
    st.success("✅ Databáze (Google Tabulka) úspěšně připojena!")
except Exception as e:
    st.error(f"❌ Chyba při připojování databáze: {e}")
    st.stop() # Zastaví aplikaci, pokud se nelze připojit

st.divider()

# 2. Základní přihlašovací formulář pro žáky
st.subheader("Přihlášení žáka")
jmeno = st.text_input("Zadej své jméno (přesně jako v tabulce):")
pin = st.text_input("Zadej PIN:", type="password")

if st.button("Přihlásit se"):
    # Stáhneme všechny záznamy z tabulky
    zaznamy = db.get_all_records()
    
    # Zkusíme najít žáka podle jména a PINu
    uzivatel_nalezen = False
    for radek in zaznamy:
        if str(radek["Jmeno"]) == jmeno and str(radek["PIN"]) == pin:
            uzivatel_nalezen = True
            st.write(f"Vítej, **{jmeno}**!")
            st.write(f"Tvůj aktuální zůstatek: **{radek['Zustatek']} Kč**")
            # Tady později přidáme logiku nákupu a prodeje
            break
            
    if not uzivatel_nalezen:
        st.error("Chybné jméno nebo PIN. Zkus to znovu.")
