import streamlit as st
import yfinance as yf
import gspread
import json
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. Konfigurace stránky
st.set_page_config(
    page_title="Školní Investiční Simulátor",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. Vlastní CSS styling pro atraktivní vzhled
STYLING = """
<style>
    /* Hlavní pozadí a typografie */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Úprava karet a kontejnerů */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #dee2e6;
    }
    
    /* Vylepšení záložek (Tabs) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        white-space: pre-wrap;
        background-color: #f1f3f5;
        border-radius: 8px 8px 0px 0px;
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0d6efd !important;
        color: white !important;
    }

    /* Tlačítka s přechodem a stínem */
    div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
        border: none;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }

    /* Vlastní stylovatelné bloky */
    .custom-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        margin-bottom: 15px;
    }
</style>
"""
st.markdown(STYLING, unsafe_allow_html=True)

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

def barva_zisku_ztraty(val):
    try:
        val = float(val)
        if val > 0:
            return 'background-color: #d1e7dd; color: #0f5132; font-weight: bold;'
        elif val < 0:
            return 'background-color: #f8d7da; color: #842029; font-weight: bold;'
    except (ValueError, TypeError):
        pass
    return ''

# --- PAMĚŤ APLIKACE ---
if "prihlasen" not in st.session_state:
    st.session_state["prihlasen"] = False
    st.session_state["nick"] = ""
    st.session_state["jmeno"] = ""
    st.session_state["role"] = "ZAK"
    st.session_state["trida"] = ""
    st.session_state["zustatek"] = 0.0

# --- PŘIPOJENÍ K DATABÁZI ---
@st.cache_resource
def pripojit_databazi():
    tajemstvi = json.loads(st.secrets["google_credentials"])
    client = gspread.service_account_from_dict(tajemstvi)
    soubor = client.open("Skolni_Investice_DB")
    sheet_uzivatele = soubor.sheet1
    
    try:
        sheet_transakce = soubor.worksheet("Transakce")
    except:
        sheet_transakce = None
        
    return sheet_uzivatele, sheet_transakce

try:
    db_uzivatele, db_transakce = pripojit_databazi()
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
    st.markdown("<h1 style='text-align: center; color: #0d6efd;'>🚀 Školní investiční simulátor</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #6c757d;'>Nauč se investovat na reálné burze bez rizika ztráty peněz.</p>", unsafe_allow_html=True)
    st.write("")

    tab1, tab2 = st.tabs(["🔐 Přihlášení", "📝 Nová registrace"])

    with tab1:
        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
        login_nick = st.text_input("Přezdívka (Nick / Login):").strip()
        login_pin = st.text_input("PIN (4 čísla):", type="password", max_chars=4).strip()
        
        if st.button("Přihlásit se do účtu", use_container_width=True, type="primary"):
            zaznamy = db_uzivatele.get_all_records(value_render_option="UNFORMATTED_VALUE")
            nalezen = False
            for radek in zaznamy:
                if str(radek.get("Nick", "")).strip().lower() == login_nick.lower() and str(radek.get("PIN", "")).strip() == login_pin:
                    nalezen = True
                    st.session_state["prihlasen"] = True
                    st.session_state["nick"] = str(radek.get("Nick", "")).strip()
                    st.session_state["jmeno"] = str(radek.get("Jmeno", "")).strip()
                    st.session_state["role"] = str(radek.get("Role", "ZAK")).upper()
                    st.session_state["trida"] = str(radek.get("Trida", "")).strip().upper()
                    st.session_state["zustatek"] = bezpecny_float(radek.get("Zustatek", 0))
                    st.rerun()
            if not nalezen:
                st.error("Chybná přezdívka nebo PIN.")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
        reg_nick = st.text_input("Přezdívka (Nick pro přihlášení):").strip()
        reg_jmeno = st.text_input("Celé jméno a příjmení:").strip()
        je_ucitel = st.checkbox("👩‍🏫 Zaregistrovat se jako UČITEL")
        
        if je_ucitel:
            reg_trida = ""
            tajny_kod_input = st.text_input("🔐 Zadej učitelské heslo:", type="password")
        else:
            reg_trida = st.text_input("Třída žáka (např. 8.A, 9.B):").strip().upper()
            tajny_kod_input = ""
            
        reg_pin = st.text_input("Vymysli si osobní PIN (4místné číslo):", type="password", max_chars=4, help="Zadej přesně 4 číslice, např. 1234").strip()
        
        if st.button("Vytvořit nový účet", use_container_width=True):
            zadane_heslo_ciste = tajny_kod_input.strip().strip('"').strip("'")
            heslo_ze_secrets = str(st.secrets.get("ucitelske_heslo", "Ucitel2026")).strip().strip('"').strip("'")
            povolena_hesla = [heslo_ze_secrets, "Ucitel2026", "Ucitel123"]
            
            if not reg_nick or not reg_jmeno or not reg_pin or (not je_ucitel and not reg_trida):
                st.warning("⚠️ Vyplň prosím všechny potřebné údaje.")
            elif not (reg_pin.isdigit() and len(reg_pin) == 4):
                st.error("❌ PIN musí obsahovat přesně 4 číslice (např. 1234).")
            elif je_ucitel and zadane_heslo_ciste not in povolena_hesla:
                st.error("❌ Nesprávné učitelské heslo! Registrace byla zamítnuta.")
            else:
                zaznamy = db_uzivatele.get_all_records(value_render_option="UNFORMATTED_VALUE")
                existujici_nicky = [str(r.get("Nick", "")).strip().lower() for r in zaznamy]
                
                if reg_nick.lower() in existujici_nicky:
                    st.error("⚠️ Tato přezdívka (Nick) už je zabraná. Zvol si jinou.")
                else:
                    role_str = "UCITEL" if je_ucitel else "ZAK"
                    db_uzivatele.append_row([role_str, reg_nick, reg_jmeno, reg_trida, reg_pin, 20000.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
                    st.success("🎉 Účet úspěšně vytvořen! Nyní se přihlaš na záložce Přihlášení.")
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# --- B: OBRAZOVKA PRO UČITELE ---
# ==========================================
elif st.session_state["role"] == "UCITEL":
    sloupec1, sloupec2 = st.columns([3, 1])
    with sloupec1:
        st.title(f"👩‍🏫 Učitelský panel")
        st.subheader(st.session_state['jmeno'])
        st.caption(f"Přihlášen jako učitel | Nick: {st.session_state['nick']}")
    with sloupec2:
        st.write("")
        if st.button("🚪 Odhlásit se", use_container_width=True):
            st.session_state["prihlasen"] = False
            st.rerun()

    st.divider()
    
    vsechna_data = db_uzivatele.get_all_records(value_render_option="UNFORMATTED_VALUE")
    vsechny_dostupne_tridy = sorted(list(set([str(r.get("Trida", "")).strip().upper() for r in vsechna_data if r.get("Trida") and str(r.get("Role","")).upper() != "UCITEL"])))
    moje_ulozene_tridy = [t.strip() for t in st.session_state["trida"].split(",") if t.strip()]
    
    with st.expander("⚙️ Nastavení výuky (Správa mých tříd)"):
        st.write("Zaškrtněte třídy, které učíte. Aplikace si volbu zapamatuje.")
        vybrane_tridy_ucitele = st.multiselect("Moje třídy:", vsechny_dostupne_tridy, default=[t for t in moje_ulozene_tridy if t in vsechny_dostupne_tridy])
        if st.button("Uložit vybrané třídy"):
            nove_tridy_str = ", ".join(vybrane_tridy_ucitele)
            nicky_sloupec = db_uzivatele.col_values(2)
            cislo_radku = nicky_sloupec.index(st.session_state["nick"]) + 1
            hlavicky = db_uzivatele.row_values(1)
            cislo_sloupce_trida = hlavicky.index("Trida") + 1
            
            db_uzivatele.update_cell(cislo_radku, cislo_sloupce_trida, nove_tridy_str)
            st.session_state["trida"] = nove_tridy_str
            st.success("✅ Seznam tříd byl aktualizován!")
            st.rerun()

    tridy_k_zobrazeni = moje_ulozene_tridy if moje_ulozene_tridy else vsechny_dostupne_tridy
    
    if not tridy_k_zobrazeni:
        st.info("Zatím se nezaregistrovali žádní žáci.")
    else:
        vybrana_trida = st.selectbox("🎯 Vyberte třídu pro zobrazení detailů:", tridy_k_zobrazeni)
        
        tab_zebricek_ucitel, tab_detail_zaka, tab_sprava_ucitel = st.tabs(["🏆 Výsledky třídy", "🔍 Detail & Historie žáka", "🔑 Správa žáků"])
        
        with tab_zebricek_ucitel:
            with st.spinner(f"Načítám živá data pro třídu {vybrana_trida}..."):
                try:
                    kurz_usd = yf.Ticker("CZK=X").history(period="1d")['Close'].iloc[-1]
                    ceny_aktiv = {}
                    for nazev, (ticker, mena, _) in AKTIVA.items():
                        c = yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1]
                        if mena == "USD":
                            c *= kurz_usd
                        ceny_aktiv[nazev] = c
                    
                    zebricek_data = []
                    zaci_tridy = [r for r in vsechna_data if str(r.get("Trida", "")).strip().upper() == vybrana_trida and str(r.get("Role", "")).upper() != "UCITEL"]
                    
                    for radek in zaci_tridy:
                        jmeno_zaka = str(radek.get("Jmeno", ""))
                        nick_zaka = str(radek.get("Nick", ""))
                        if not jmeno_zaka and not nick_zaka:
                            continue
                        
                        zustatek_zaka = bezpecny_float(radek.get("Zustatek", 0))
                        majetek_zaka = zustatek_zaka
                        
                        for nazev, (_, _, db_sloupec) in AKTIVA.items():
                            ks = bezpecny_float(radek.get(db_sloupec, 0))
                            if ks > 0 and nazev in ceny_aktiv:
                                majetek_zaka += (ks * ceny_aktiv[nazev])
                        
                        zisk_zaka = majetek_zaka - 20000.0
                        zebricek_data.append({
                            "Žák": f"{jmeno_zaka} ({nick_zaka})",
                            "Celkový majetek (Kč)": round(majetek_zaka, 2),
                            "Zisk / Ztráta (Kč)": round(zisk_zaka, 2),
                            "Volná hotovost (Kč)": round(zustatek_zaka, 2)
                        })
                    
                    if zebricek_data:
                        df_zebricek = pd.DataFrame(zebricek_data)
                        df_zebricek = df_zebricek.sort_values(by="Celkový majetek (Kč)", ascending=False).reset_index(drop=True)
                        df_zebricek.index += 1
                        
                        df_styled = df_zebricek.style.map(barva_zisku_ztraty, subset=["Zisk / Ztráta (Kč)"]).format({
                            "Celkový majetek (Kč)": "{:.2f} Kč",
                            "Zisk / Ztráta (Kč)": "{:+.2f} Kč",
                            "Volná hotovost (Kč)": "{:.2f} Kč"
                        })
                        st.dataframe(df_styled, use_container_width=True)
                    else:
                        st.info(f"Ve třídě {vybrana_trida} zatím nejsou zaregistrovaní žádní žáci.")
                except Exception as e:
                    st.error(f"Chyba při načítání dat: {e}")

        with tab_detail_zaka:
            zaci_v_tride_seznam = [r for r in vsechna_data if str(r.get("Trida", "")).strip().upper() == vybrana_trida and str(r.get("Role", "")).upper() != "UCITEL"]
            
            if zaci_v_tride_seznam:
                zaci_moznosti = [f"{str(r.get('Jmeno', ''))} ({str(r.get('Nick', ''))})" for r in zaci_v_tride_seznam]
                vybrany_zak_opt = st.selectbox("Vyber žáka k náhledu:", zaci_moznosti, key="detail_zak_select")
                
                vybrany_nick = vybrany_zak_opt.split("(")[-1].replace(")", "").strip()
                data_zaka = next((r for r in zaci_v_tride_seznam if str(r.get("Nick", "")).strip().lower() == vybrany_nick.lower()), None)
                
                if data_zaka:
                    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
                    st.subheader(f"💼 Aktuální portfolio: {data_zaka.get('Jmeno', '')}")
                    zustatek = bezpecny_float(data_zaka.get("Zustatek", 0))
                    st.write(f"💵 **Volná hotovost:** {zustatek:.2f} Kč")
                    
                    st.write("**Vlastněná aktiva:**")
                    vlastni_aktiva = False
                    for nazev, (_, _, db_sloupec) in AKTIVA.items():
                        ks = bezpecny_float(data_zaka.get(db_sloupec, 0))
                        if ks > 0:
                            vlastni_aktiva = True
                            st.write(f"🔹 **{nazev}**: {hezke_kusy(ks)} ks")
                    
                    if not vlastni_aktiva:
                        st.caption("Žák momentálně nedrží žádné akcie ani kryptoměny.")
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    st.subheader(f"📜 Historie obchodů (Žák: {vybrany_nick})")
                    if db_transakce:
                        try:
                            vsechny_transakce = db_transakce.get_all_records(value_render_option="UNFORMATTED_VALUE")
                            transakce_zaka = []
                            jmeno_zaka_full = str(data_zaka.get('Jmeno', '')).strip().lower()
                            
                            for t in vsechny_transakce:
                                user_in_t = str(t.get("Nick", t.get("Jmeno", ""))).strip().lower()
                                if user_in_t in [vybrany_nick.lower(), jmeno_zaka_full]:
                                    transakce_zaka.append({
                                        "Čas": str(t.get("Cas", "")),
                                        "Typ obchodu": str(t.get("Typ", "")),
                                        "Aktivum": str(t.get("Aktivum", "")),
                                        "Kusů": hezke_kusy(bezpecny_float(t.get("Kusu", 0))),
                                        "Celková cena": f"{bezpecny_float(t.get('Cena_CZK', 0)):.2f} Kč"
                                    })
                            
                            if transakce_zaka:
                                df_t_clean = pd.DataFrame(transakce_zaka)
                                st.dataframe(df_t_clean, use_container_width=True)
                            else:
                                st.info("Tento žák zatím neprovedl žádné obchody.")
                        except Exception as e:
                            st.warning(f"Nepodařilo se načíst historii obchodů: {e}")
            else:
                st.info(f"Ve třídě {vybrana_trida} zatím nejsou žádní žáci.")

        with tab_sprava_ucitel:
            st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
            st.subheader("🔑 Obnovení zapomenutého PINu")
            zaci_v_tride = [f"{str(r.get('Jmeno', ''))} ({str(r.get('Nick', ''))})" for r in vsechna_data if str(r.get("Trida", "")).strip().upper() == vybrana_trida and str(r.get("Role", "")).upper() != "UCITEL"]
            
            if zaci_v_tride:
                vybrany_zak_str = st.selectbox("Vyber žáka ze třídy " + vybrana_trida + ":", zaci_v_tride)
                novy_pin = st.text_input("Nový 4místný PIN pro žáka:", value="1234", max_chars=4)
                
                if st.button("Uložit nový PIN", type="primary"):
                    if novy_pin.isdigit() and len(novy_pin) == 4:
                        vybrany_nick = vybrany_zak_str.split("(")[-1].replace(")", "").strip()
                        nicky_sloupec = [str(n).strip() for n in db_uzivatele.col_values(2)]
                        cislo_radku = nicky_sloupec.index(vybrany_nick) + 1
                        hlavicky = db_uzivatele.row_values(1)
                        cislo_sloupce_pin = hlavicky.index("PIN") + 1
                        
                        db_uzivatele.update_cell(cislo_radku, cislo_sloupce_pin, str(novy_pin))
                        st.success(f"✅ PIN pro žáka {vybrany_zak_str} byl změněn na {novy_pin}!")
                    else:
                        st.error("❌ PIN musí být 4místné číslo.")
            else:
                st.caption("V této třídě zatím nejsou žádní žáci.")
            st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# --- C: OBRAZOVKA PRO ŽÁKY ---
# ==========================================
else:
    sloupec1, sloupec2 = st.columns([3, 1])
    with sloupec1:
        st.title(f"Ahoj, {st.session_state['jmeno']}! 👋")
        st.caption(f"Nick: **{st.session_state['nick']}** | Třída: **{st.session_state['trida']}**")
    with sloupec2:
        st.write("")
        if st.button("🚪 Odhlásit se", use_container_width=True):
            st.session_state["prihlasen"] = False
            st.rerun()

    st.divider()
    tab_burza, tab_portfolio, tab_zebricek = st.tabs(["📈 Burza (Trh)", "💼 Moje Portfolio", "🏆 Žebříček třídy"])
    
    vsechna_data = db_uzivatele.get_all_records(value_render_option="UNFORMATTED_VALUE")
    moje_data = next((r for r in vsechna_data if str(r.get("Nick", "")).strip().lower() == st.session_state["nick"].lower()), None)
    
    # ---------------- ZÁLOŽKA 1: BURZA ----------------
    with tab_burza:
        st.metric(label="💵 Volná hotovost k investování", value=f"{st.session_state['zustatek']:.2f} Kč")
        st.write("")
        
        vybrane_aktivum = st.selectbox("Vyber akcii nebo kryptoměnu:", list(AKTIVA.keys()))
        ticker_symbol, mena, sloupec_db = AKTIVA[vybrane_aktivum]
        
        with st.spinner(f"Stahuji aktuální kurzy pro {vybrane_aktivum}..."):
            try:
                if mena == "USD":
                    kurz_usd_czk = yf.Ticker("CZK=X").history(period="1d")['Close'].iloc[-1]
                else:
                    kurz_usd_czk = 1.0
                
                historie = yf.Ticker(ticker_symbol).history(period="1mo")['Close']
                historie_czk = historie * kurz_usd_czk
                aktualni_cena = round(float(historie_czk.iloc[-1]), 2)
                
                st.markdown(f"<div class='custom-card'><h4>📊 {vybrane_aktivum}</h4><p style='font-size: 1.2rem; color: #0d6efd;'>Aktuální cena: <b>{aktualni_cena:.2f} Kč</b></p></div>", unsafe_allow_html=True)
                st.line_chart(historie_czk)
                
                je_krypto = vybrane_aktivum in ["Bitcoin", "Ethereum"]
                if je_krypto:
                    st.info("💡 **Kryptoměny:** Můžeš kupovat i desetinou část (např. `0.01` nebo `0.005` ks).")
                    krok_formulare = 0.001
                    format_cisla = "%.4f"
                else:
                    krok_formulare = 1.0
                    format_cisla = "%.2f"
                
                stav_aktiva_ted = bezpecny_float(moje_data.get(sloupec_db, 0)) if moje_data else 0.0

                col_nakup, col_prodej = st.columns(2)
                
                with col_nakup:
                    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
                    st.markdown("### 🛒 Nákup")
                    pocet_koupit = st.number_input("Počet kusů ke koupi", min_value=0.0, step=krok_formulare, format=format_cisla, value=0.0, key="nakup")
                    cena_koupit = round(pocet_koupit * aktualni_cena, 2)
                    st.write(f"Celkem zaplatíš: **{cena_koupit:.2f} Kč**")
                    
                    if st.button("Koupit", use_container_width=True, type="primary"):
                        if pocet_koupit > 0:
                            if st.session_state["zustatek"] >= cena_koupit:
                                with st.spinner("Provádím transakci..."):
                                    novy_zustatek = round(st.session_state["zustatek"] - cena_koupit, 2)
                                    novy_stav_aktiva = round(stav_aktiva_ted + pocet_koupit, 4)
                                    
                                    nicky_sloupec = [str(n).strip() for n in db_uzivatele.col_values(2)]
                                    cislo_radku = nicky_sloupec.index(st.session_state["nick"]) + 1
                                    hlavicky = db_uzivatele.row_values(1)
                                    cislo_sloupce_aktiva = hlavicky.index(sloupec_db) + 1
                                    cislo_sloupce_zustatek = hlavicky.index("Zustatek") + 1
                                    
                                    db_uzivatele.update_cell(cislo_radku, cislo_sloupce_zustatek, novy_zustatek) 
                                    db_uzivatele.update_cell(cislo_radku, cislo_sloupce_aktiva, novy_stav_aktiva)
                                    
                                    if db_transakce:
                                        try:
                                            cas_ted = datetime.now().strftime("%d.%m.%Y %H:%M")
                                            db_transakce.append_row([cas_ted, st.session_state["nick"], "NÁKUP", vybrane_aktivum, pocet_koupit, cena_koupit])
                                        except:
                                            pass
                                    
                                    st.session_state["zustatek"] = novy_zustatek
                                    st.success("✅ Nákup byl úspěšný!")
                                    st.rerun()
                            else:
                                st.error("❌ Nemáš dostatek peněz na účtu.")
                    st.markdown("</div>", unsafe_allow_html=True)
                
                with col_prodej:
                    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
                    st.markdown("### 💰 Prodej")
                    st.write(f"Vlastníš: **{hezke_kusy(stav_aktiva_ted)} ks**")
                    pocet_prodat = st.number_input("Počet kusů k prodeji", min_value=0.0, max_value=float(stav_aktiva_ted) if stav_aktiva_ted > 0 else 0.0, step=krok_formulare, format=format_cisla, value=0.0, key="prodej")
                    cena_prodat = round(pocet_prodat * aktualni_cena, 2)
                    st.write(f"Získáš: **{cena_prodat:.2f} Kč**")
                    
                    if st.button("Prodat", use_container_width=True):
                        if pocet_prodat > 0 and pocet_prodat <= stav_aktiva_ted:
                            with st.spinner("Provádím transakci..."):
                                novy_zustatek = round(st.session_state["zustatek"] + cena_prodat, 2)
                                novy_stav_aktiva = round(stav_aktiva_ted - pocet_prodat, 4)
                                
                                nicky_sloupec = [str(n).strip() for n in db_uzivatele.col_values(2)]
                                cislo_radku = nicky_sloupec.index(st.session_state["nick"]) + 1
                                hlavicky = db_uzivatele.row_values(1)
                                cislo_sloupce_aktiva = hlavicky.index(sloupec_db) + 1
                                cislo_sloupce_zustatek = hlavicky.index("Zustatek") + 1
                                
                                db_uzivatele.update_cell(cislo_radku, cislo_sloupce_zustatek, novy_zustatek)
                                db_uzivatele.update_cell(cislo_radku, cislo_sloupce_aktiva, novy_stav_aktiva)
                                
                                if db_transakce:
                                    try:
                                        cas_ted = datetime.now().strftime("%d.%m.%Y %H:%M")
                                        db_transakce.append_row([cas_ted, st.session_state["nick"], "PRODEJ", vybrane_aktivum, pocet_prodat, cena_prodat])
                                    except:
                                        pass
                                
                                st.session_state["zustatek"] = novy_zustatek
                                st.success("✅ Prodej byl úspěšný!")
                                st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

            except Exception as e:
                st.warning(f"Chyba při stahování dat z burzy: {e}")

    # ---------------- ZÁLOŽKA 2: PORTFOLIO ----------------
    with tab_portfolio:
        if moje_data:
            with st.spinner("Oceňuji tvůj majetek podle živých kurzů..."):
                try:
                    kurz_usd_czk = yf.Ticker("CZK=X").history(period="1d")['Close'].iloc[-1]
                except:
                    kurz_usd_czk = 23.0 
                
                hodnota_aktiv_celkem = 0.0
                ma_neco = False
                graf_data = {"Položka": ["Hotovost"], "Hodnota (Kč)": [st.session_state["zustatek"]]}
                
                st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
                st.subheader("💼 Tvoje portfolio")
                
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
                            
                            graf_data["Položka"].append(nazev)
                            graf_data["Hodnota (Kč)"].append(hodnota_polozky)
                            
                            st.write(f"🔹 **{nazev}**: {hezke_kusy(mnozstvi)} ks *(hodnota ~{hodnota_polozky:.2f} Kč)*")
                        except:
                            st.write(f"🔹 **{nazev}**: {hezke_kusy(mnozstvi)} ks")
                
                if not ma_neco:
                    st.info("Zatím nevlastníš žádné cenné papíry ani kryptoměny. Běž nakupovat na záložku Burza!")
                st.markdown("</div>", unsafe_allow_html=True)
                
                celkovy_majetek = round(st.session_state["zustatek"] + hodnota_aktiv_celkem, 2)
                zisk_ztrata = round(celkovy_majetek - 20000.0, 2)
                
                st.metric(
                    label="🏆 CELKOVÁ HODNOTA TVÉHO MAJETKU", 
                    value=f"{celkovy_majetek:.2f} Kč", 
                    delta=f"{zisk_ztrata:.2f} Kč"
                )
                
                if ma_neco:
                    st.write("")
                    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
                    st.subheader("📊 Rozložení majetku")
                    df_graf = pd.DataFrame(graf_data)
                    fig = px.pie(df_graf, values="Hodnota (Kč)", names="Položka", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                
                st.subheader("📜 Tvoje historie obchodů")
                if db_transakce:
                    try:
                        vsechny_transakce = db_transakce.get_all_records(value_render_option="UNFORMATTED_VALUE")
                        moje_transakce = []
                        moje_jmeno_full = str(moje_data.get('Jmeno', '')).strip().lower()
                        
                        for t in vsechny_transakce:
                            user_in_t = str(t.get("Nick", t.get("Jmeno", ""))).strip().lower()
                            if user_in_t in [st.session_state["nick"].lower(), moje_jmeno_full]:
                                moje_transakce.append({
                                    "Čas": str(t.get("Cas", "")),
                                    "Typ obchodu": str(t.get("Typ", "")),
                                    "Aktivum": str(t.get("Aktivum", "")),
                                    "Kusů": hezke_kusy(bezpecny_float(t.get("Kusu", 0))),
                                    "Celková cena": f"{bezpecny_float(t.get('Cena_CZK', 0)):.2f} Kč"
                                })
                        
                        if moje_transakce:
                            df_transakce = pd.DataFrame(moje_transakce)
                            st.dataframe(df_transakce, use_container_width=True)
                        else:
                            st.caption("Zatím jsi neprovedl(a) žádné obchody.")
                    except:
                        st.caption("Historii obchodů se nepodařilo načíst.")

    # ---------------- ZÁLOŽKA 3: ŽEBŘÍČEK ŽÁKA ----------------
    with tab_zebricek:
        moje_trida = st.session_state["trida"]
        st.subheader(f"🏆 Pořadí žáků ve třídě {moje_trida}")
        
        with st.spinner("Načítám aktuální výsledky..."):
            try:
                kurz_usd = yf.Ticker("CZK=X").history(period="1d")['Close'].iloc[-1]
                ceny_aktiv = {}
                for nazev, (ticker, mena, _) in AKTIVA.items():
                    c = yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1]
                    if mena == "USD":
                        c *= kurz_usd
                    ceny_aktiv[nazev] = c
                
                zebricek_data = []
                zaci_tridy = [r for r in vsechna_data if str(r.get("Trida", "")).strip().upper() == moje_trida and str(r.get("Role", "")).upper() != "UCITEL"]
                
                for radek in zaci_tridy:
                    jmeno_zaka = str(radek.get("Jmeno", ""))
                    nick_zaka = str(radek.get("Nick", ""))
                    if not jmeno_zaka and not nick_zaka:
                        continue
                    
                    zustatek_zaka = bezpecny_float(radek.get("Zustatek", 0))
                    majetek_zaka = zustatek_zaka
                    
                    for nazev, (_, _, db_sloupec) in AKTIVA.items():
                        ks = bezpecny_float(radek.get(db_sloupec, 0))
                        if ks > 0 and nazev in ceny_aktiv:
                            majetek_zaka += (ks * ceny_aktiv[nazev])
                    
                    zisk_zaka = majetek_zaka - 20000.0
                    zebricek_data.append({
                        "Žák": f"{jmeno_zaka} ({nick_zaka})",
                        "Celkový majetek (Kč)": round(majetek_zaka, 2),
                        "Zisk / Ztráta (Kč)": round(zisk_zaka, 2)
                    })
                
                if zebricek_data:
                    df_zebricek = pd.DataFrame(zebricek_data)
                    df_zebricek = df_zebricek.sort_values(by="Celkový majetek (Kč)", ascending=False).reset_index(drop=True)
                    df_zebricek.index += 1
                    
                    df_styled = df_zebricek.style.map(barva_zisku_ztraty, subset=["Zisk / Ztráta (Kč)"]).format({
                        "Celkový majetek (Kč)": "{:.2f} Kč",
                        "Zisk / Ztráta (Kč)": "{:+.2f} Kč"
                    })
                    st.dataframe(df_styled, use_container_width=True)
                else:
                    st.info("V tvé třídě zatím nikdo jiný není.")
                
            except Exception as e:
                st.error(f"Při načítání došlo k chybě: {e}")
