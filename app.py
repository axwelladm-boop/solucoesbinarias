import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np

# ── CONFIGURAÇÃO DA PÁGINA (Sempre a primeira linha de código) ──
st.set_page_config(page_title="Axwell Pro", layout="wide", initial_sidebar_state="expanded")

# ── ESTILIZAÇÃO CSS (Otimizada para carregar mais rápido) ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Rajdhani:wght@400;600&display=swap');
html,body,[class*="css"]{font-family:'Rajdhani',sans-serif;color:#e0e0e0;}
.main{background:#080b14;}.block-container{padding-top:1rem;}
.axwell-header{text-align:center;padding:14px 0 6px;border-bottom:1px solid #00ffcc33;margin-bottom:20px;}
.axwell-header h1{font-family:'Orbitron',monospace;font-size:2rem;font-weight:900;color:#00ffcc;letter-spacing:4px;margin:0;}
.axwell-header p{color:#607090;font-size:0.8rem;margin-top:4px;letter-spacing:2px;}
.card{background:#0d1520;border:1px solid #00ffcc22;border-radius:10px;padding:14px 18px;margin-bottom:8px;}
.card .lbl{color:#607090;font-size:0.7rem;letter-spacing:1px;text-transform:uppercase;}
.card .val{font-family:'Orbitron',monospace;font-size:1.4rem;color:#00ffcc;font-weight:700;}
.card .dlt{font-size:0.8rem;margin-top:2px;}
.sig-call{background:#06180e;border:1px solid #00ff8844;border-left:4px solid #00ff88;border-radius:10px;padding:16px;margin:8px 0;}
.sig-put{background:#180606;border:1px solid #ff444444;border-left:4px solid #ff4444;border-radius:10px;padding:16px;margin:8px 0;}
.sig-wait{background:#0d1520;border:1px solid #607090;border-left:4px solid #607090;border-radius:10px;padding:16px;margin:8px 0;}
.sig-title{font-family:'Orbitron',monospace;font-size:0.9rem;font-weight:700;letter-spacing:1px;}
.bar-bg{background:#1a1f2e;border-radius:4px;height:7px;margin-top:5px;overflow:hidden;}
.bar-fill{height:7px;border-radius:4px;}
.sess-box{background:#0d1520;border:1px solid #1a2030;border-radius:10px;padding:14px 18px;margin-bottom:16px;}
section[data-testid="stSidebar"]{background:#0a0e18;border-right:1px solid #1a2030;}
.stTabs [data-baseweb="tab-list"]{background:#0a0e18;border-bottom:1px solid #1a2030;}
.stTabs [data-baseweb="tab"]{font-family:'Rajdhani',sans-serif;color:#607090;}
.stTabs [aria-selected="true"]{color:#00ffcc !important;border-bottom:2px solid #00ffcc !important;background:#0d1520;}
.stButton>button{border-radius:8px;font-family:'Orbitron',monospace;font-size:0.75rem;font-weight:700;letter-spacing:1px;height:3em;border:none;}
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ──
BANCA_INICIAL = 70.0
ATIVOS = {
    "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "JPY=X",
    "AUDUSD": "AUDUSD=X", "BTC/USD": "BTC-USD",  "ETH/USD": "ETH-USD",
    "SOL/USD": "SOL-USD",  "Ouro":    "GC=F",      "Petróleo": "CL=F",
    "S&P 500": "^GSPC",    "Nasdaq":  "^IXIC",
}
TIMEFRAMES = {
    "1 min":  ("1d",  "1m"),
    "5 min":  ("5d",  "5m"),
    "15 min": ("1mo", "15m"),
    "1 hora": ("3mo", "1h"),
}
EXPIRACAO_SEG = {
    "30 segundos": 30,
    "1 minuto":    60,
    "2 minutos":   120,
    "5 minutos":   300,
    "30 minutos":  1800,
}

# ── SESSION STATE ──
def init():
    if 'banca' not in st.session_state:
        st.session_state.update({
            'banca': BANCA_INICIAL, 'banca_max': BANCA_INICIAL,
            'wins': 0, 'losses': 0, 'seq': 0, 'best_seq': 0, 'worst_seq': 0,
            'logs': pd.DataFrame(columns=['Hora','Ativo','Direção','Resultado','Valor','P&L','Saldo']),
            'resultados': {}, 'analisado': False
        })
init()

# ── INDICADORES ──
def ema(s, n): return s.ewm(span=n, adjust=False).mean()
def rsi(s, n=14):
    d = s.diff()
    g = d.clip(lower=0).rolling(n).mean()
    l = (-d.clip(upper=0)).rolling(n).mean()
    return 100 - 100/(1 + g/l.replace(0,np.nan))
def macd(s):
    m = ema(s,12)-ema(s,26); sg = ema(m,9); return m, sg, m-sg
def bbands(s, n=20):
    m = s.rolling(n).mean(); sd = s.rolling(n).std()
    return m+2*sd, m, m-2*sd
def stoch(h, l, c, k=14, d=3):
    lo = l.rolling(k).min(); hi = h.rolling(k).max()
    sk = 100*(c-lo)/(hi-lo).replace(0,np.nan)
    return sk, sk.rolling(d).mean()
def atr(h, l, c, n=14):
    tr = pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    return tr.rolling(n).mean()

def calcular(df):
    df = df.copy()
    c,h,l = df['Close'], df['High'], df['Low']
    df['RSI']  = rsi(c)
    df['E8']   = ema(c,8); df['E20'] = ema(c,20); df['E50'] = ema(c,50)
    df['MACD'], df['MSIG'], df['MHIST'] = macd(c)
    df['BBU'], df['BBM'], df['BBL'] = bbands(c)
    df['SK'], df['SD'] = stoch(h,l,c)
    df['ATR'] = atr(h,l,c)
    return df.dropna()

def score(df):
    if df is None or len(df)<2: return 0,0
    r = df.iloc[-1]; p = df.iloc[-2]
    sc=sp=0
    rs = r.get('RSI', 50)
    if rs<30: sc+=20
    elif rs<40: sc+=10
    elif rs>70: sp+=20
    elif rs>60: sp+=10
    if r.get('E8',0)>r.get('E20',0): sc+=15
    else: sp+=15
    if r.get('E20',0)>r.get('E50',0): sc+=10
    else: sp+=10
    hn=r.get('MHIST',0); hp=p.get('MHIST',0)
    if hn>0 and hn>hp: sc+=20
    elif hn<0 and hn<hp: sp+=20
    cl=r.get('Close',0); bl=r.get('BBL',0); bu=r.get('BBU',0)
    if bl and cl<bl*1.001: sc+=20
    elif bu and cl>bu*0.999: sp+=20
    k=r.get('SK',50); d=r.get('SD',50)
    if k<20 and k>d: sc+=15
    elif k>80 and k<d: sp+=15
    return int(min(sc,100)), int(min(sp,100))

@st.cache_data(ttl=60) # Adicionado Cache para não ser bloqueado pelo Yahoo Finance
def buscar(ticker, period, interval):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        if df.empty or len(df)<50: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[['Open','High','Low','Close']].copy() # Volume removido por instabilidade em alguns ativos
        return calcular(df)
    except: return None

# ── SESSÕES ──
def sessoes():
    now = datetime.utcnow()
    h_utc = now.hour + now.minute/60
    h_brt = (h_utc-3)%24
    ativas = []
    if 0<=h_utc<9: ativas.append("🌏 Ásia")
    if 8<=h_utc<17: ativas.append("🇬🇧 Londres")
    if 13<=h_utc<22: ativas.append("🇺🇸 Nova York")
    q,qc,desc = "🔴 BAIXA","#ff4444","Baixa liquidez"
    if 13<=h_utc<17: q,qc,desc = "🟢 ALTA","#00ff88","🔥 Overlap Londres+NY"
    elif 8<=h_utc<9: q,qc,desc = "🟢 ALTA","#00ffcc","Abertura Londres"
    elif 20<=h_utc<22: q,qc,desc = "🟡 MÉDIA","#ffaa00","Fechamento NY"
    return " · ".join(ativas) or "Nenhuma", q, qc, desc, h_brt

# ── HELPERS ──
def kelly(wr, pay):
    if wr<=0 or pay<=0: return 0.0
    return max(0.0,(wr*pay-(1-wr))/pay)

def dd():
    bm = st.session_state.banca_max
    return ((bm-st.session_state.banca)/bm*100) if bm>0 else 0.0

def reg(ativo, direcao, resultado, valor, pp):
    pnl = valor*(pp/100) if resultado=="WIN" else -valor
    st.session_state.banca += pnl
    st.session_state.banca_max = max(st.session_state.banca_max, st.session_state.banca)
    if resultado=="WIN":
        st.session_state.wins+=1
        st.session_state.seq = max(0,st.session_state.seq)+1
        st.session_state.best_seq = max(st.session_state.best_seq, st.session_state.seq)
    else:
        st.session_state.losses+=1
        st.session_state.seq = min(0,st.session_state.seq)-1
        st.session_state.worst_seq = min(st.session_state.worst_seq, st.session_state.seq)
    
    new_log = pd.DataFrame([{
        'Hora': datetime.now().strftime("%H:%M:%S"), 'Ativo': ativo, 'Direção': direcao,
        'Resultado': resultado, 'Valor': valor, 'P&L': round(pnl,2), 'Saldo': round(st.session_state.banca,2)
    }])
    st.session_state.logs = pd.concat([st.session_state.logs, new_log], ignore_index=True)

def card(lbl,val,dlt="",dc="#607090"):
    d = f'<div class="dlt" style="color:{dc}">{dlt}</div>' if dlt else ""
    return f'<div class="card"><div class="lbl">{lbl}</div><div class="val">{val}</div>{d}</div>'

# ── HEADER ──
st.markdown("""<div class="axwell-header"><h1>⬡ AXWELL PRO</h1><p>ANALISTA SNIPER v4.0 | ROYAL CAPITAL</p></div>""", unsafe_allow_html=True)

# ── SIDEBAR ──
with st.sidebar:
    st.markdown("### 🛡️ BANCA")
    total_ops = st.session_state.wins + st.session_state.losses
    wr = st.session_state.wins/total_ops if total_ops>0 else 0
    dda = dd()
    bd = st.session_state.banca - BANCA_INICIAL
    dc = "#00ff88" if bd>=0 else "#ff4444"
    st.markdown(card("Saldo Atual",f"${st.session_state.banca:.2f}",f"{'▲' if bd>=0 else '▼'} ${abs(bd):.2f}",dc), unsafe_allow_html=True)
    
    col_a, col_b = st.columns(2)
    col_a.markdown(card("Drawdown",f"{dda:.1f}%",dc="#ff4444" if dda>10 else "#00ff88"), unsafe_allow_html=True)
    col_b.markdown(card("Win Rate",f"{wr*100:.0f}%",dc="#00ff88" if wr>=0.5 else "#ff4444"), unsafe_allow_html=True)

    st.divider()
    st.markdown("### ⚙️ PARÂMETROS")
    ativos_sel = st.multiselect("Ativos", list(ATIVOS.keys()), default=["EURUSD","BTC/USD"])
    tf_sel = st.selectbox("Timeframe", list(TIMEFRAMES.keys()), index=1)
    val_entrada = st.number_input("Entrada ($)", 1.0, 1000.0, 2.0)
    payout_pct = st.slider("Payout (%)", 70, 95, 87)
    expiracao = st.selectbox("⏱ Expiração", list(EXPIRACAO_SEG.keys()), index=1)
    period, interval = TIMEFRAMES[tf_sel]

    if st.button("🔄 Resetar Tudo", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ── ABAS ──
t1, t2, t3, t4 = st.tabs(["🎯 Sniper Board", "📊 Gráfico", "📈 Performance", "🛡️ Risco"])

with t1:
    s_ativas, s_qual, s_qcor, s_desc, h_brt = sessoes()
    st.markdown(f"""<div class="sess-box" style="border-left:4px solid {s_qcor}">
        <div style="display:flex;gap:20px;align-items:center">
            <div><small>HORA BRT</small><br><b>{int(h_brt):02d}:{int((h_brt%1)*60):02d}</b></div>
            <div><small>SESSÕES</small><br><span style="color:#00ffcc">{s_ativas}</span></div>
            <div><small>QUALIDADE</small><br><b style="color:{s_qcor}">{s_qual}</b></div>
        </div></div>""", unsafe_allow_html=True)

    if st.button("🔍 ANALISAR AGORA", use_container_width=True):
        st.session_state.analisado = True
        with st.spinner("Analisando..."):
            for nome in ativos_sel:
                st.session_state.resultados[nome] = buscar(ATIVOS[nome], period, interval)

    if st.session_state.analisado:
        cols = st.columns(min(len(ativos_sel), 3))
        for i, nome in enumerate(ativos_sel):
            df = st.session_state.resultados.get(nome)
            with cols[i % len(cols)]:
                if df is not None:
                    sc_c, sc_p = score(df)
                    last = df.iloc[-1]
                    st.markdown(card(nome, f"{last['Close']:.5f}"), unsafe_allow_html=True)
                    
                    if sc_c >= 70 or sc_p >= 70:
                        tipo = "CALL" if sc_c > sc_p else "PUT"
                        cor = "#00ff88" if tipo == "CALL" else "#ff4444"
                        st.markdown(f"""<div class="sig-{tipo.lower()}">
                            <div class="sig-title">{tipo} ▲</div>
                            <div style="font-size:1.5rem;font-weight:900;color:{cor}">ENTRAR AGORA</div>
                            <small>Confiança: {max(sc_c, sc_p)}%</small>
                            <div class="bar-bg"><div class="bar-fill" style="width:{max(sc_c,sc_p)}%;background:{cor}"></div></div>
                        </div>""", unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="sig-wait">Aguardando sinal...</div>', unsafe_allow_html=True)

with t2:
    ativo_g = st.selectbox("Ativo para gráfico", list(ATIVOS.keys()))
    if st.button("Carregar Gráfico"):
        p, i = TIMEFRAMES[tf_sel]
        dfg = buscar(ATIVOS[ativo_g], p, i)
        if dfg is not None:
            fig = go.Figure(data=[go.Candlestick(x=dfg.index, open=dfg['Open'], high=dfg['High'], low=dfg['Low'], close=dfg['Close'])])
            fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,b=0,t=0))
            st.plotly_chart(fig, use_container_width=True)

with t3:
    if not st.session_state.logs.empty:
        st.dataframe(st.session_state.logs, use_container_width=True)
        st.line_chart(st.session_state.logs['Saldo'])
    else:
        st.info("Nenhuma operação registrada.")

with t4:
    st.subheader("Calculadora de Risco")
    k_val = kelly(wr, payout_pct/100)
    st.write(f"Sugerido pelo critério de Kelly: **${st.session_state.banca * k_val:.2f}**")
