import streamlit as st
import yfinance as yf
import gspread
import json

st.set_page_config(page_title="Investiční simulátor", layout="centered")
st.title("📈 Školní investiční simulátor")

# 1. Funkce pro bezpečné připojení k databázi
@st.cache_resource
def pripojit_databazi():
    tajemstvi = json.loads(st.secrets["google_credentials"])
    client = gspread.service_account_from_dict(tajemstvi)
    sheet = client.open("Skolni_Investice_DB").sheet1
    return sheet

try:
    db = pripojit_databazi()
    # Zelené hlášení o připojení už můžeme skrýt, ať to žáky neruší. 
    # Necháme ho tu jen zakomentované, kdybys ho někdy potřebovala.
    # st.success("✅ Databáze úspěšně připojena!")
except Exception as e:
    st.error(f"❌ Chyba při připojování databáze: {e}")
    st.stop()

st.divider()

# Vytvoření dvou záložek
tab1, tab2 = st.tabs(["🔐 Přihlášení", "📝 Nová registrace"])

# --- ZÁLOŽKA 1: PŘIHLÁŠENÍ ---
with tab1:
    st.subheader("Přihlášení žáka")
    login_jmeno = st.text_input("Zadej své jméno (přesně jako při registraci):", key="log_jmeno")
    login_pin = st.text_input("Zadej PIN:", type="password", key="log_pin")

    if st.button("Přihlásit se"):
        if not login_jmeno or not login_pin:
            st.warning("Prosím, vyplň jméno i PIN.")
        else:
            zaznamy = db.get_all_records()
            uzivatel_nalezen = False
            
            for radek in zaznamy:
                if str(radek["Jmeno"]) == login_jmeno and str(radek["PIN"]) == login_pin:
                    uzivatel_nalezen = True
                    st.success(f"Vítej, **{login_jmeno}**!")
                    st.write(f"Tvůj aktuální zůstatek: **{radek['Zustatek']} Kč**")
                    # (Tady později naprogramujeme samotné obchodování)
                    break
                    
            if not uzivatel_nalezen:
                st.error("Chybné jméno nebo PIN. Zkus to znovu.")

# --- ZÁLOŽKA 2: REGISTRACE ---
with tab2:
    st.subheader("Vytvoření nového účtu")
    reg_jmeno = st.text_input("Zadej jméno a příjmení (např. Jan Novák):")
    reg_pin = st.text_input("Vymysli si PIN (doporučujeme 4 čísla):", type="password", key="reg_pin")
    reg_pin_kontrola = st.text_input("Zadej PIN ještě jednou pro kontrolu:", type="password")

    if st.button("Zaregistrovat se"):
        if not reg_jmeno or not reg_pin:
            st.warning("Musíš vyplnit všechny údaje.")
        elif reg_pin != reg_pin_kontrola:
            st.error("Zadané PINy se neshodují! Zkus to znovu.")
        else:
            # Stáhneme data, abychom zkontrolovali, jestli už jméno neexistuje
            zaznamy = db.get_all_records()
            jmena_v_db = [str(radek["Jmeno"]) for radek in zaznamy]
            
            if reg_jmeno in jmena_v_db:
                st.error("Tohle jméno už v systému je. Zkus si za jméno přidat třeba začáteční písmeno příjmení.")
            else:
                # Připravíme si nový řádek do tabulky 
                # (Pořadí: Jmeno, PIN, Zustatek, AAPL, TSLA, CEZ, BTC, MSFT)
                novy_radek = [reg_jmeno, reg_pin, 10000, 0, 0, 0, 0, 0]
                
                # Zápis do Google Tabulky!
                db.append_row(novy_radek)
                st.balloons() # Pro radost přidáme balónky :-)
                st.success(f"Účet pro **{reg_jmeno}** byl úspěšně vytvořen s rozpočtem 10 000 Kč! Překlikni nahoře na 'Přihlášení' a můžeš začít.")
