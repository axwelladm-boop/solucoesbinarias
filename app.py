import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import numpy as np
import streamlit.components.v1 as components
import base64

# ─────────────────────────────────────────────
#  CONFIGURAÇÕES DE PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(page_title="AXWELL PRO | Analista Sniper", layout="wide", initial_sidebar_state="expanded")

# Função para converter imagem local para Base64 (Evita erro no GitHub)
def get_image_base64(path):
    try:
        with open(path, "rb") as image_file:
            return f"data:image/png;base64,{base64.b64encode(image_file.read()).decode()}"
    except:
        return ""

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@400;600&display=swap');
html,body,[class*="css"]{font-family:'Rajdhani',sans-serif;color:#e0e0e0;}
.main{background-color:#080b14;}.block-container{padding-top:1.5rem;}
.axwell-header{text-align:center;padding:18px 0 8px;border-bottom:1px solid #00ffcc33;margin-bottom:24px;}
.axwell-header h1{font-family:'Orbitron',monospace;font-size:2.2rem;font-weight:900;color:#00ffcc;letter-spacing:4px;margin:0;text-shadow:0 0 20px #00ffcc66;}
.axwell-header p{color:#607090;font-size:0.85rem;margin-top:4px;letter-spacing:2px;}
.logo-img { max-width: 280px; margin-bottom: 10px; filter: drop-shadow(0 0 10px #00ffcc33); }
.metric-card{background:linear-gradient(135deg,#0d1520 60%,#0a1a1a);border:1px solid #00ffcc33;border-radius:12px;padding:16px 20px;margin-bottom:8px;}
.metric-card .label{color:#607090;font-size:0.75rem;letter-spacing:1px;text-transform:uppercase;}
.metric-card .value{font-family:'Orbitron',monospace;font-size:1.5rem;color:#00ffcc;font-weight:700;}
.metric-card .delta{font-size:0.8rem;margin-top:2px;}
.signal-call{background:linear-gradient(135deg,#0a2010,#062810);border:1px solid #00ff8844;border-left:4px solid #00ff88;border-radius:10px;padding:14px 18px;margin:8px 0;}
.signal-put{background:linear-gradient(135deg,#200a0a,#280606);border:1px solid #ff444444;border-left:4px solid #ff4444;border-radius:10px;padding:14px 18px;margin:8px 0;}
.signal-wait{background:#0d1520;border:1px solid #607090;border-left:4px solid #607090;border-radius:10px;padding:14px 18px;margin:8px 0;}
.signal-title{font-family:'Orbitron',monospace;font-size:1rem;font-weight:700;letter-spacing:1px;}
.score-bar-bg{background:#1a1f2e;border-radius:6px;height:8px;margin-top:6px;overflow:hidden;}
.score-bar-fill{height:8px;border-radius:6px;}
.badge{display:inline-block;padding:2px 10px;border-radius:20px;font-size:0.72rem;font-weight:600;letter-spacing:1px;text-transform:uppercase;}
.badge-alto{background:#ff222222;color:#ff4444;border:1px solid #ff4444;}
.badge-medio{background:#ffaa0022;color:#ffaa00;border:1px solid #ffaa00;}
.badge-baixo{background:#00ff8822;color:#00ff88;border:1px solid #00ff88;}
section[data-testid="stSidebar"]{background:#0a0e18;border-right:1px solid #1a2030;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────
BANCA_INICIAL = 70.0

if 'banca' not in st.session_state:
    st.session_state.update({
        'banca': BANCA_INICIAL, 'banca_max': BANCA_INICIAL,
        'total_wins': 0, 'total_losses': 0,
        'sequencia': 0, 'melhor_sequencia': 0, 'pior_sequencia': 0,
        'logs': pd.DataFrame(columns=['Hora','Ativo','Direção','Resultado','Valor','P&L','Saldo']),
        'resultados_sniper': {},
        'analisado': False,
    })

# ─────────────────────────────────────────────
#  INDICADORES TÉCNICOS
# ─────────────────────────────────────────────
def calcular_indicadores(df):
    c = df['Close']; h = df['High']; l = df['Low']
    df = df.copy()
    # RSI
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs))
    # EMAs
    df['EMA_8'] = c.ewm(span=8, adjust=False).mean()
    df['EMA_20'] = c.ewm(span=20, adjust=False).mean()
    df['EMA_50'] = c.ewm(span=50, adjust=False).mean()
    # MACD
    e12 = c.ewm(span=12, adjust=False).mean()
    e26 = c.ewm(span=26, adjust=False).mean()
    df['MACD'] = e12 - e26
    df['MACD_SIGNAL'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_HIST'] = df['MACD'] - df['MACD_SIGNAL']
    # BB
    m = c.rolling(20).mean(); s = c.rolling(20).std()
    df['BB_UPPER'], df['BB_LOWER'] = m + 2*s, m - 2*s
    # Outros
    lo = l.rolling(14).min(); hi = h.rolling(14).max()
    df['STOCH_K'] = 100 * (c - lo) / (hi - lo).replace(0, np.nan)
    df['ATR'] = pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1).rolling(14).mean()
    return df.dropna()

# ─────────────────────────────────────────────
#  LOGICA DE SCORE & STATUS
# ─────────────────────────────────────────────
def calcular_score(df):
    if df is None or len(df) < 2: return 0, 0
    row = df.iloc[-1]; sc = sp = 0
    if row['RSI'] < 30: sc += 30
    elif row['RSI'] > 70: sp += 30
    if row['EMA_8'] > row['EMA_20']: sc += 20
    else: sp += 20
    if row['MACD_HIST'] > 0: sc += 25
    else: sp += 25
    if row['Close'] < row['BB_LOWER']: sc += 25
    elif row['Close'] > row['BB_UPPER']: sp += 25
    return min(sc, 100), min(sp, 100)

def status_mercado():
    agora = datetime.utcnow()
    h = agora.hour + agora.minute/60
    # Simplificação para exemplo
    if 10 <= h <= 14: return ["Londres", "NY"], "🟢 ALTA", "#00ffcc", "Overlap Ativo", h-3
    return ["Ásia"], "🟡 MÉDIA", "#ffaa00", "Liquidez Normal", h-3

# ─────────────────────────────────────────────
#  SIDEBAR & HEADER
# ─────────────────────────────────────────────
logo_b64 = get_image_base64("logo.png")
header_html = f"""
<div class="axwell-header">
    {f'<img src="{logo_b64}" class="logo-img">' if logo_b64 else '<h1>⬡ AXWELL PRO</h1>'}
    <p>SISTEMA DE INTELIGÊNCIA QUANTITATIVA | AX SOLUÇÕES BINÁRIAS</p>
</div>"""
st.markdown(header_html, unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🛡️ GESTÃO DE BANCA")
    st.metric("Saldo Atual", f"${st.session_state.banca:.2f}", f"{st.session_state.banca - BANCA_INICIAL:+.2f}")
    
    st.divider()
    ativos_sel = st.multiselect("Ativos", ["EURUSD=X", "GBPUSD=X", "BTC-USD", "ETH-USD"], default=["EURUSD=X", "BTC-USD"])
    tf_sel = st.selectbox("Timeframe", ["1m", "5m", "15m", "1h"], index=1)
    val_entrada = st.number_input("Entrada ($)", 1.0, 1000.0, 2.0)
    payout_pct = st.slider("Payout %", 70, 95, 87)
    
    if st.button("🔄 Resetar Sistema"):
        st.session_state.clear()
        st.rerun()

# ─────────────────────────────────────────────
#  CONTEÚDO PRINCIPAL (TABS)
# ─────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🎯 Sniper Board", "📊 Gráficos", "📈 Performance"])

with tab1:
    ativas, qual, q_cor, desc, h_br = status_mercado()
    st.markdown(f"""<div style='border-left:4px solid {q_cor}; padding-left:15px;'>
                <h4>Mercado: {qual}</h4><p>{desc} | Sessões: {', '.join(ativas)}</p></div>""", unsafe_allow_html=True)
    
    if st.button("🔍 ESCANEAR MERCADO AGORA"):
        with st.spinner("Analisando confluências..."):
            for ativo in ativos_sel:
                df = yf.download(ativo, period="1d", interval=tf_sel, progress=False)
                if not df.empty:
                    df = calcular_indicadores(df)
                    sc, sp = calcular_score(df)
                    
                    col_a, col_b = st.columns([1, 2])
                    with col_a:
                        st.subheader(ativo)
                        st.write(f"Preço: {df['Close'].iloc[-1]:.5f}")
                    with col_b:
                        if sc > 70:
                            st.markdown(f'<div class="signal-call"><span class="signal-title">💎 COMPRA FORTE (CALL)</span><br>Score: {sc}/100</div>', unsafe_allow_html=True)
                        elif sp > 70:
                            st.markdown(f'<div class="signal-put"><span class="signal-title">📉 VENDA FORTE (PUT)</span><br>Score: {sp}/100</div>', unsafe_allow_html=True)
                        else:
                            st.markdown('<div class="signal-wait">Aguardando sinal claro...</div>', unsafe_allow_html=True)
                    st.divider()

with tab2:
    if ativos_sel:
        ativo_graf = st.selectbox("Ver Gráfico", ativos_sel)
        df_g = yf.download(ativo_graf, period="1d", interval=tf_sel)
        if not df_g.empty:
            fig = go.Figure(data=[go.Candlestick(x=df_g.index, open=df_g['Open'], high=df_g['High'], low=df_g['Low'], close=df_g['Close'])])
            fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,b=0,t=0))
            st.plotly_chart(fig, use_container_width=True)

with tab3:
    c1, c2, c3 = st.columns(3)
    c1.metric("Wins", st.session_state.total_wins)
    c2.metric("Losses", st.session_state.total_losses)
    winrate = (st.session_state.total_wins / (st.session_state.total_wins + st.session_state.total_losses + 0.1)) * 100
    c3.metric("WinRate", f"{winrate:.1f}%")
    st.dataframe(st.session_state.logs, use_container_width=True)
