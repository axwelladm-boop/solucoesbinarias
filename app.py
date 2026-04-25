import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import numpy as np
import base64

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Axwell Pro Ultra", layout="wide", initial_sidebar_state="expanded")

# --- FUNÇÃO PARA ALERTA SONORO ---
def play_sound():
    # Som de bip curto em base64 para evitar dependência de arquivos externos
    b64 = "SUQzBAAAAAAAF1RFTkMAAAALAAADTGF2ZjU4LjI5LjEwMAD/+000AAAAAAAAAAAAAAAAAAAAAAA=" # Exemplo simplificado
    audio_html = f"""
        <audio autoplay>
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
    """
    # Usando um som de sistema padrão via JavaScript para maior compatibilidade
    st.components.v1.html(
        """<script>
        var context = new (window.AudioContext || window.webkitAudioContext)();
        var oscillator = context.createOscillator();
        oscillator.type = 'sine';
        oscillator.frequency.setValueAtTime(880, context.currentTime);
        oscillator.connect(context.destination);
        oscillator.start();
        setTimeout(function(){ oscillator.stop(); }, 200);
        </script>""", height=0
    )

# --- CSS PERSONALIZADO (INCLUINDO NOVOS CARDS DE TEMPO REAL) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Rajdhani:wght@400;600&display=swap');
html,body,[class*="css"]{font-family:'Rajdhani',sans-serif;color:#e0e0e0;}
.main{background:#080b14;}
.axwell-header{text-align:center;padding:15px;border-bottom:2px solid #00ffcc;margin-bottom:20px;background:rgba(0,255,204,0.05);}
.axwell-header h1{font-family:'Orbitron',monospace;color:#00ffcc;letter-spacing:5px;margin:0;}
.card{background:#0d1520;border:1px solid #00ffcc22;border-radius:10px;padding:15px;margin-bottom:10px;}
.val-signal{font-family:'Orbitron',monospace;font-size:1.8rem;font-weight:900;text-align:center;}
.best-time{background:linear-gradient(90deg, #0f2027, #203a43, #2c5364);padding:10px;border-radius:5px;text-align:center;border:1px solid #00ffcc;}
</style>
""", unsafe_allow_html=True)

# --- CONSTANTES E SESSÃO ---
BANCA_INICIAL = 70.0
ATIVOS = {
    "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "JPY=X",
    "AUDUSD": "AUDUSD=X", "BTC/USD": "BTC-USD", "ETH/USD": "ETH-USD",
    "Ouro": "GC=F", "S&P 500": "^GSPC"
}
TIMEFRAMES = {"1 min": ("1d", "1m"), "5 min": ("5d", "5m"), "15 min": ("1mo", "15m")}

if 'banca' not in st.session_state:
    st.session_state.update({
        'banca': BANCA_INICIAL, 'banca_max': BANCA_INICIAL,
        'wins': 0, 'losses': 0, 'logs': pd.DataFrame(columns=['Hora','Ativo','Direção','Resultado','P&L']),
        'resultados': {}, 'analisado': False
    })

# --- INDICADORES TÉCNICOS ---
def calcular_indicadores(df):
    c = df['Close']
    df['EMA8'] = c.ewm(span=8).mean()
    df['EMA20'] = c.ewm(span=20).mean()
    # RSI
    delta = c.diff(); gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss; df['RSI'] = 100 - (100 / (1 + rs))
    # Bollinger
    df['MA20'] = c.rolling(20).mean(); df['STD'] = c.rolling(20).std()
    df['BBU'] = df['MA20'] + (df['STD'] * 2); df['BBL'] = df['MA20'] - (df['STD'] * 2)
    return df.dropna()

# --- LÓGICA DE MELHOR HORÁRIO (TEMPO REAL) ---
def get_market_timing():
    now = datetime.now()
    hour = now.hour
    # Horários de pico de liquidez (Overlap Londres/NY) são os melhores para GANHOS REAIS
    if 10 <= hour <= 14:
        return "💎 ALTA PRECISÃO (LONDRES + NY)", "#00ffcc"
    elif 5 <= hour <= 9:
        return "✅ BOM (ABERTURA LONDRES)", "#00ff88"
    elif 19 <= hour <= 23:
        return "🟡 MÉDIO (ÁSIA)", "#ffaa00"
    else:
        return "⚠️ BAIXA VOLATILIDADE", "#607090"

# --- ENGINE DE SINAIS + BIP ---
def analisar_sniper(df):
    last = df.iloc[-1]
    score_call = 0
    score_put = 0
    
    # Condições de Compra (CALL)
    if last['Close'] <= last['BBL']: score_call += 30
    if last['RSI'] < 30: score_call += 30
    if last['EMA8'] > last['EMA20']: score_call += 40
    
    # Condições de Venda (PUT)
    if last['Close'] >= last['BBU']: score_put += 30
    if last['RSI'] > 70: score_put += 30
    if last['EMA8'] < last['EMA20']: score_put += 40
    
    return score_call, score_put

# --- INTERFACE ---
st.markdown('<div class="axwell-header"><h1>⬡ AXWELL PRO SNIPER</h1></div>', unsafe_allow_html=True)

# Barra de Horário em Tempo Real
timing, color = get_market_timing()
st.markdown(f'<div class="best-time">SITUAÇÃO DO MERCADO AGORA: <b style="color:{color}">{timing}</b></div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("🛡️ Gestão Axwell")
    st.metric("Saldo", f"${st.session_state.banca:.2f}")
    ativos_sel = st.multiselect("Ativos", list(ATIVOS.keys()), default=["EURUSD", "BTC/USD"])
    tf_sel = st.selectbox("Timeframe", list(TIMEFRAMES.keys()))
    payout = st.slider("Payout %", 70, 95, 87)
    
    if st.button("🔄 Resetar"):
        st.session_state.clear()
        st.rerun()

# --- EXECUÇÃO ---
col1, col2 = st.columns([2, 1])

with col1:
    if st.button("🔍 ESCANEAR OPORTUNIDADES EM TEMPO REAL", use_container_width=True):
        st.session_state.analisado = True
        with st.spinner("Analisando BIPS e Sinais..."):
            for nome in ativos_sel:
                periodo, intervalo = TIMEFRAMES[tf_sel]
                df = yf.download(ATIVOS[nome], period=periodo, interval=intervalo, progress=False)
                if not df.empty:
                    df = calcular_indicadores(df)
                    sc, sp = analisar_sniper(df)
                    st.session_state.resultados[nome] = {'call': sc, 'put': sp, 'price': df.iloc[-1]['Close']}
                    
                    # DISPARO DO BIP SE O SINAL FOR FORTE (>80%)
                    if sc >= 80 or sp >= 80:
                        play_sound()

if st.session_state.analisado:
    res_cols = st.columns(len(ativos_sel))
    for i, nome in enumerate(ativos_sel):
        data = st.session_state.resultados.get(nome)
        if data:
            with res_cols[i]:
                st.markdown(f'<div class="card">', unsafe_allow_html=True)
                st.write(f"**{nome}**")
                st.write(f"Preço: {data['price']:.5f}")
                
                if data['call'] >= 80:
                    st.markdown(f'<div class="val-signal" style="color:#00ff88">COMPRA<br>{data["call"]}%</div>', unsafe_allow_html=True)
                    st.toast(f"🚨 SINAL DE COMPRA: {nome}", icon="🚀")
                elif data['put'] >= 80:
                    st.markdown(f'<div class="val-signal" style="color:#ff4444">VENDA<br>{data["put"]}%</div>', unsafe_allow_html=True)
                    st.toast(f"🚨 SINAL DE VENDA: {nome}", icon="📉")
                else:
                    st.write("Aguardando Sniper...")
                st.markdown('</div>', unsafe_allow_html=True)

# --- HISTÓRICO E GRÁFICOS ---
with st.expander("📊 Performance e Gráfico Detalhado"):
    if st.session_state.analisado:
        # Exemplo com o primeiro ativo selecionado
        ativo_f = ativos_sel[0]
        df_plot = yf.download(ATIVOS[ativo_f], period="1d", interval="5m", progress=False)
        fig = go.Figure(data=[go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'])])
        fig.update_layout(template="plotly_dark", title=f"Monitoramento Real: {ativo_f}")
        st.plotly_chart(fig, use_container_width=True)
