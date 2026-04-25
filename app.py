import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="AXWELL PRO | Sniper Quant", layout="wide")

# --- COMPONENTE DE ALERTA SONORO ---
def play_sound():
    sound_html = """
    <audio autoplay>
    <source src="https://files.freemusicarchive.org/storage-freemusicarchive-org/music/no_curator/Tours/Enthusiast/Tours_-_01_-_Enthusiast.mp3" type="audio/mp3">
    </audio>
    """
    st.components.v1.html(sound_html, height=0)

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&display=swap');
    .stApp { background-color: #05080d; color: #e0e0e0; }
    .signal-card { padding: 20px; border-radius: 15px; text-align: center; border: 2px solid #00ffcc; background: #0a111e; }
    .buy { color: #00ff88; text-shadow: 0 0 10px #00ff88; font-family: 'Orbitron'; }
    .sell { color: #ff4444; text-shadow: 0 0 10px #ff4444; font-family: 'Orbitron'; }
</style>
""", unsafe_allow_html=True)

# --- INICIALIZAÇÃO DO BANCO DE DADOS ---
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Hora', 'Ativo', 'Resultado', 'Valor', 'Minuto'])
if 'banca' not in st.session_state:
    st.session_state.banca = 70.0

# --- LÓGICA DE ANÁLISE QUANTITATIVA ---
def sniper_analysis(ticker):
    df = yf.download(ticker, period="1d", interval="1m", progress=False)
    if df.empty: return None
    
    # Cálculo de RSI Rápido
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=7).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=7).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    last_rsi = rsi.iloc[-1]
    last_price = df['Close'].iloc[-1]
    
    # Próximo minuto redondo (Horário de entrada)
    proxima_entrada = (datetime.now() + timedelta(minutes=1)).replace(second=0, microsecond=0)
    
    return {"rsi": last_rsi, "price": last_price, "time": proxima_entrada}

# --- INTERFACE SIDEBAR ---
with st.sidebar:
    st.title("⚙️ DASHBOARD")
    ativo = st.selectbox("Selecione o Ativo", ["EURUSD=X", "GBPUSD=X", "BTC-USD", "ETH-USD"])
    tempo_op = st.selectbox("Tempo de Expiração", ["30s", "1 min", "2 min", "5 min", "30 min"])
    valor = st.number_input("Valor da Entrada ($)", 1.0, 1000.0, 2.0)
    st.divider()
    st.metric("BANCA", f"${st.session_state.banca:.2f}")

# --- CORPO PRINCIPAL ---
t1, t2 = st.tabs(["🎯 SNIPER LIVE", "📊 PERFORMANCE"])

with t1:
    st.subheader("Análise em Tempo Real")
    
    if st.button("🚀 INICIAR VARREDURA SNIPER", use_container_width=True):
        with st.spinner("Sincronizando com o mercado..."):
            res = sniper_analysis(ativo)
            
            if res:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Preço Atual", f"{res['price']:.5f}")
                with col2:
                    st.metric("Força Relativa (RSI)", f"{res['rsi']:.2f}")

                # Lógica de Sinal
                if res['rsi'] < 30 or res['rsi'] > 70:
                    play_sound() # Alerta Sonoro
                    direcao = "COMPRA (CALL)" if res['rsi'] < 30 else "VENDA (PUT)"
                    classe = "buy" if res['rsi'] < 30 else "sell"
                    
                    st.markdown(f"""
                    <div class="signal-card">
                        <h2 class="{classe}">{direcao}</h2>
                        <p>ENTRADA ÀS: <b>{res['time'].strftime('%H:%M:%S')}</b></p>
                        <p>DURAÇÃO: <b>{tempo_op}</b></p>
                        <p style="color: #ffaa00;">⚠️ ALERTA: PREPARE A OPERAÇÃO AGORA!</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("Buscando confluência... Sem sinal claro no momento.")

    st.divider()
    st.subheader("📝 REGISTRAR OPERAÇÃO")
    c1, c2, c3 = st.columns(3)
    res_op = c1.radio("Resultado", ["WIN", "LOSS"])
    if c3.button("SALVAR NO HISTÓRICO"):
        pnl = valor * 0.87 if res_op == "WIN" else -valor
        st.session_state.banca += pnl
        novo_log = {
            'Hora': datetime.now().strftime("%H:%M"),
            'Ativo': ativo,
            'Resultado': res_op,
            'Valor': pnl,
            'Minuto': datetime.now().minute
        }
        st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([novo_log])], ignore_index=True)
        st.success("Registrado!")

with t2:
    if not st.session_state.db.empty:
        st.subheader("📈 Melhor Horário de Ganho")
        
        # Agrupar por minuto para ver onde tem mais WINs
        df_perf = st.session_state.db[st.session_state.db['Resultado'] == 'WIN']
        if not df_perf.empty:
            horarios = df_perf['Hora'].value_counts()
            st.bar_chart(horarios)
            st.write(f"🔥 Seu melhor horário detectado: **{horarios.idxmax()}**")
        
        st.table(st.session_state.db)
    else:
        st.info("Ainda não há dados de performance.")
