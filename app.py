import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Investiční simulátor", layout="centered")
st.title("📈 Školní investiční simulátor")

if 'balance' not in st.session_state:
    st.session_state.balance = 10000.0
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = 0

st.write(f"💰 **Tvůj aktuální zůstatek:** ${st.session_state.balance:.2f}")

ticker_symbol = "AAPL"
ticker = yf.Ticker(ticker_symbol)
current_price = ticker.fast_info['lastPrice']

st.metric(label=f"Aktuální cena {ticker_symbol}", value=f"${current_price:.2f}")

st.subheader("Vývoj ceny za poslední měsíc")
history = ticker.history(period="1mo")
st.line_chart(history['Close'])

st.divider()
st.subheader("Obchodování")

mnozstvi = st.number_input("Kolik akcií chceš koupit?", min_value=1, step=1)
celkova_cena = mnozstvi * current_price

if st.button("Koupit akcie"):
    if st.session_state.balance >= celkova_cena:
        st.session_state.balance -= celkova_cena
        st.session_state.portfolio += mnozstvi
        st.success(f"✅ Úspěšně nakoupeno {mnozstvi} akcií {ticker_symbol}!")
    else:
        st.error("❌ Nemáš dostatek fiktivních prostředků!")

st.write(f"📦 **Vlastníš celkem:** {st.session_state.portfolio} ks akcií {ticker_symbol}")
