import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import numpy as np

st.set_page_config(page_title="Axwell Pro", layout="wide", initial_sidebar_state="expanded")

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

# ── CONSTANTS ──────────────────────────────
BANCA_INICIAL = 70.0

# Estrutura: Nome → (ticker_yfinance, payout%, categoria, é_synthetic)
ATIVOS = {
    # ── CRYPTO OTC ─────────────────────────────────────────────────────
    "Cardano (OTC)":    ("ADA-USD",   89, "🔵 Crypto OTC",   False),
    "Bitcoin (OTC)":    ("BTC-USD",   89, "🔵 Crypto OTC",   False),
    "DYDX (OTC)":       ("DYDX-USD",  89, "🔵 Crypto OTC",   False),
    "ETH/USDT":         ("ETH-USD",   15, "🔵 Crypto",       False),
    "Ethereum (OTC)":   ("ETH-USD",   89, "🔵 Crypto OTC",   False),
    "Solana (OTC)":     ("SOL-USD",   89, "🔵 Crypto OTC",   False),
    "SOL/USDT":         ("SOL-USD",   15, "🔵 Crypto",       False),
    "XRP (OTC)":        ("XRP-USD",   89, "🔵 Crypto OTC",   False),
    "XRP/USDT":         ("XRP-USD",   15, "🔵 Crypto",       False),
    "Volatility 10":    ("BTC-USD",   89, "🔵 Crypto",       True),
    "Volatility 25":    ("ETH-USD",   89, "🔵 Crypto",       True),
    # ── FOREX OTC ──────────────────────────────────────────────────────
    "EUR/GBP":          ("EURGBP=X",  82, "🟡 Forex",        False),
    "EUR/GBP (OTC)":    ("EURGBP=X",  89, "🟡 Forex OTC",    False),
    "EUR/USD":          ("EURUSD=X",  82, "🟡 Forex",        False),
    "EUR/USD (OTC)":    ("EURUSD=X",  89, "🟡 Forex OTC",    False),
    "GBP/USD (OTC)":    ("GBPUSD=X",  89, "🟡 Forex OTC",    False),
    "USD/CAD":          ("CAD=X",     82, "🟡 Forex",        False),
    "USD/JPY":          ("JPY=X",     82, "🟡 Forex",        False),
    "JPY/USD (OTC)":    ("JPY=X",     89, "🟡 Forex OTC",    False),
    # ── STOCKS OTC ─────────────────────────────────────────────────────
    "Apple (OTC)":      ("AAPL",      89, "🟢 Stock OTC",    False),
    "AMEX (OTC)":       ("AXP",       89, "🟢 Stock OTC",    False),
    "Facebook (OTC)":   ("META",      89, "🟢 Stock OTC",    False),
    "Google (OTC)":     ("GOOGL",     89, "🟢 Stock OTC",    False),
    "Intel (OTC)":      ("INTC",      89, "🟢 Stock OTC",    False),
    "McDonald's (OTC)": ("MCD",       89, "🟢 Stock OTC",    False),
    "Microsoft (OTC)":  ("MSFT",      89, "🟢 Stock OTC",    False),
    "S&P 500":          ("^GSPC",     89, "🟢 Stock",        False),
    "Tesla, Inc":       ("TSLA",      89, "🟢 Stock OTC",    False),
    "UKOIL (OTC)":      ("BZ=F",      89, "🟢 Stock OTC",    False),
    # ── SYNTHETICS ─────────────────────────────────────────────────────
    "Bear Market":      ("^VIX",      89, "🔴 Synthetic",    True),
    "Bull Market":      ("^GSPC",     89, "🔴 Synthetic",    True),
}

# Payout padrão por ativo (para sidebar lançar resultado)
def get_payout(nome):
    return ATIVOS[nome][1] if nome in ATIVOS else 89

# Grupos para exibição
CATEGORIAS = {
    "🔵 Crypto OTC":  [k for k,v in ATIVOS.items() if v[2]=="🔵 Crypto OTC"],
    "🔵 Crypto":      [k for k,v in ATIVOS.items() if v[2]=="🔵 Crypto"],
    "🟡 Forex OTC":   [k for k,v in ATIVOS.items() if v[2]=="🟡 Forex OTC"],
    "🟡 Forex":       [k for k,v in ATIVOS.items() if v[2]=="🟡 Forex"],
    "🟢 Stock OTC":   [k for k,v in ATIVOS.items() if v[2]=="🟢 Stock OTC"],
    "🟢 Stock":       [k for k,v in ATIVOS.items() if v[2]=="🟢 Stock"],
    "🔴 Synthetic":   [k for k,v in ATIVOS.items() if v[2]=="🔴 Synthetic"],
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

# ── SESSION STATE ──────────────────────────
def init():
    d = {
        'banca': BANCA_INICIAL, 'banca_max': BANCA_INICIAL,
        'wins': 0, 'losses': 0, 'seq': 0, 'best_seq': 0, 'worst_seq': 0,
        'logs': pd.DataFrame(columns=['Hora','Ativo','Direção','Resultado','Valor','P&L','Saldo']),
        'resultados': {}, 'analisado': False,
    }
    for k, v in d.items():
        if k not in st.session_state:
            st.session_state[k] = v
init()

# ── INDICADORES ────────────────────────────
def ema(s, n):   return s.ewm(span=n, adjust=False).mean()
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
    def g(col, default=0, row=None):
        row = row or r
        v = row.get(col, default)
        return float(v) if not pd.isna(v) else default
    sc=sp=0
    rs = g('RSI',50)
    if rs<30: sc+=20
    elif rs<40: sc+=10
    elif rs>70: sp+=20
    elif rs>60: sp+=10
    if g('E8')>g('E20'): sc+=15
    else: sp+=15
    if g('E20')>g('E50'): sc+=10
    else: sp+=10
    hn=g('MHIST'); hp=float(p.get('MHIST',0)) if not pd.isna(p.get('MHIST',0)) else 0
    if hn>0 and hn>hp: sc+=20
    elif hn<0 and hn<hp: sp+=20
    cl=g('Close'); bl=g('BBL'); bu=g('BBU')
    if bl and cl<bl*1.001: sc+=20
    elif bu and cl>bu*0.999: sp+=20
    k=g('SK',50); d=g('SD',50)
    if k<20 and k>d: sc+=15
    elif k>80 and k<d: sp+=15
    return min(sc,100), min(sp,100)

def buscar(nome, period, interval):
    ticker, payout, categoria, is_synthetic = ATIVOS[nome]
    if is_synthetic:
        # Sintéticos: busca ticker proxy mas sinaliza
        pass
    try:
        df = yf.download(ticker, period=period, interval=interval,
                         progress=False, auto_adjust=True)
        if df.empty or len(df)<50: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[['Open','High','Low','Close','Volume']].copy()
        df = df.apply(pd.to_numeric, errors='coerce').dropna()
        return calcular(df)
    except Exception:
        return None

# ── SESSÕES ────────────────────────────────
def sessoes():
    h_utc = datetime.utcnow().hour + datetime.utcnow().minute/60
    h_brt = (h_utc-3)%24
    ativas = []
    if 0<=h_utc<9:  ativas.append("🌏 Ásia")
    if 8<=h_utc<17: ativas.append("🇬🇧 Londres")
    if 13<=h_utc<22: ativas.append("🇺🇸 Nova York")
    q,qc,desc = "🔴 BAIXA","#ff4444","Baixa liquidez"
    if 13<=h_utc<17: q,qc,desc = "🟢 ALTA","#00ff88","🔥 Overlap Londres+NY — Melhor janela!"
    elif 8<=h_utc<9: q,qc,desc = "🟢 ALTA","#00ffcc","Abertura Londres — Alta volatilidade"
    elif 20<=h_utc<22: q,qc,desc = "🟡 MÉDIA","#ffaa00","Fechamento NY"
    elif not ativas: q,qc,desc = "⚫ FECHADO","#607090","Mercados principais fechados"
    prox = ""
    if h_brt<5:   prox = "🇬🇧 Londres abre às 05h BRT"
    elif h_brt<10: prox = "🔥 Overlap começa às 10h BRT"
    elif h_brt<19: prox = "✅ Você está na janela de operação!"
    else:          prox = "🔥 Overlap amanhã às 10h BRT"
    return " · ".join(ativas) or "Nenhuma", q, qc, desc, prox, h_brt

# ── HELPERS ────────────────────────────────
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
    row = {'Hora':datetime.now().strftime("%H:%M:%S"),'Ativo':ativo,'Direção':direcao,
           'Resultado':resultado,'Valor':valor,'P&L':round(pnl,2),'Saldo':round(st.session_state.banca,2)}
    st.session_state.logs = pd.concat([st.session_state.logs,pd.DataFrame([row])],ignore_index=True)
def card(lbl,val,dlt="",dc="#607090"):
    d = f'<div class="dlt" style="color:{dc}">{dlt}</div>' if dlt else ""
    return f'<div class="card"><div class="lbl">{lbl}</div><div class="val">{val}</div>{d}</div>'

# ── HEADER ─────────────────────────────────
st.markdown("""
<div class="axwell-header">
  <h1>⬡ AXWELL PRO</h1>
  <p>ANALISTA SNIPER v4.0 &nbsp;|&nbsp; ROYAL CAPITAL &nbsp;|&nbsp; INTELIGÊNCIA QUANTITATIVA</p>
</div>""", unsafe_allow_html=True)

# ── SIDEBAR ────────────────────────────────
with st.sidebar:
    st.markdown("### 🛡️ BANCA")
    total_ops = st.session_state.wins + st.session_state.losses
    wr  = st.session_state.wins/total_ops if total_ops>0 else 0
    dda = dd()
    bd  = st.session_state.banca - BANCA_INICIAL
    dc  = "#00ff88" if bd>=0 else "#ff4444"
    st.markdown(card("Saldo Atual",f"${st.session_state.banca:.2f}",
        f"{'▲' if bd>=0 else '▼'} ${abs(bd):.2f} ({bd/BANCA_INICIAL*100:+.1f}%)",dc), unsafe_allow_html=True)
    a,b = st.columns(2)
    with a:
        c2="#ff4444" if dda>15 else "#ffaa00" if dda>8 else "#00ff88"
        st.markdown(card("Drawdown",f"{dda:.1f}%",dc=c2), unsafe_allow_html=True)
    with b:
        c3="#00ff88" if wr>=0.6 else "#ffaa00" if wr>=0.4 else "#ff4444"
        st.markdown(card("Win Rate",f"{wr*100:.0f}%",dc=c3), unsafe_allow_html=True)

    st.divider()
    st.markdown("### ⚙️ PARÂMETROS")

    # Seleção por categoria
    cat_sel = st.selectbox("Categoria", ["Todos"] + list(CATEGORIAS.keys()))
    lista_ativos = list(ATIVOS.keys()) if cat_sel == "Todos" else CATEGORIAS[cat_sel]
    defaults_possiveis = [a for a in ["EUR/USD (OTC)", "Bitcoin (OTC)", "Facebook (OTC)"] if a in lista_ativos]
    ativos_sel  = st.multiselect("Ativos OTC", lista_ativos, default=defaults_possiveis)
    tf_sel      = st.selectbox("Timeframe", list(TIMEFRAMES.keys()), index=1)
    val_entrada = st.number_input("Entrada ($)", 1.0, 100.0, 2.0, step=0.5)

    # Payout automático baseado no ativo selecionado
    if len(ativos_sel) == 1:
        payout_pct = ATIVOS[ativos_sel[0]][1]
        st.markdown(f"""<div style="background:#0d1520;border:1px solid #00ffcc22;border-radius:8px;
            padding:8px 14px;margin:4px 0;font-family:'Orbitron',monospace;color:#00ffcc;font-size:0.9rem">
            Payout: <b>{payout_pct}%</b></div>""", unsafe_allow_html=True)
    else:
        payout_pct = st.slider("Payout (%)", 70, 95, 89)

    expiracao   = st.selectbox("⏱ Expiração", list(EXPIRACAO_SEG.keys()), index=1)
    period, interval = TIMEFRAMES[tf_sel]

    kf = kelly(wr, payout_pct/100)
    kv = st.session_state.banca*kf
    pct_r = (val_entrada/st.session_state.banca*100) if st.session_state.banca>0 else 0
    rl = "ALTO" if pct_r>5 else "MÉDIO" if pct_r>2 else "BAIXO"
    rc = "#ff4444" if pct_r>5 else "#ffaa00" if pct_r>2 else "#00ff88"
    st.markdown(f"""
    <div style="background:#0d1520;border:1px solid #1a2030;border-radius:8px;padding:10px 14px;margin-top:6px">
      <div style="color:#607090;font-size:0.7rem;letter-spacing:1px">KELLY CRITERION</div>
      <div style="font-family:'Orbitron',monospace;color:#00ffcc;font-size:0.95rem;margin:3px 0">${kv:.2f}
        <span style="font-size:0.7rem;color:#607090">({kf*100:.1f}%)</span></div>
      <span style="background:{rc}22;color:{rc};border:1px solid {rc};padding:1px 8px;border-radius:20px;font-size:0.68rem;font-weight:700">Risco: {rl}</span>
    </div>""", unsafe_allow_html=True)
    if dda>=20: st.error("⛔ DRAWDOWN CRÍTICO!")
    elif dda>=10: st.warning("⚠️ Drawdown elevado.")

    st.divider()
    st.markdown("### 📋 RESULTADO")
    am = st.selectbox("Ativo", list(ATIVOS.keys()), key="am")
    dm = st.radio("Direção", ["CALL ▲","PUT ▼"], horizontal=True)
    payout_manual = ATIVOS[am][1]
    st.caption(f"Payout automático: **{payout_manual}%**")
    cw,cl = st.columns(2)
    if cw.button("✅ WIN",  use_container_width=True): reg(am,dm,"WIN", val_entrada,payout_manual); st.balloons(); st.rerun()
    if cl.button("❌ LOSS", use_container_width=True): reg(am,dm,"LOSS",val_entrada,payout_manual); st.rerun()
    st.divider()
    if st.button("🔄 Resetar", use_container_width=True):
        for k in ['banca','banca_max','wins','losses','seq','best_seq','worst_seq','logs','resultados','analisado']:
            del st.session_state[k]
        st.rerun()

# ── ABAS ───────────────────────────────────
t1,t2,t3,t4 = st.tabs(["🎯 Sniper Board","📊 Gráfico","📈 Performance","🛡️ Risco"])

# ══════════════════════════════════════════
with t1:
    s_ativas, s_qual, s_qcor, s_desc, s_prox, h_brt = sessoes()
    hora_fmt = f"{int(h_brt):02d}:{int((h_brt%1)*60):02d}"

    st.markdown(f"""
    <div class="sess-box" style="border-left:4px solid {s_qcor}">
      <div style="display:flex;gap:24px;flex-wrap:wrap;align-items:center">
        <div>
          <div style="color:#607090;font-size:0.68rem;letter-spacing:1px">🕐 HORA BRT</div>
          <div style="font-family:'Orbitron',monospace;font-size:1.3rem;color:#fff;font-weight:700">{hora_fmt}</div>
        </div>
        <div>
          <div style="color:#607090;font-size:0.68rem;letter-spacing:1px">📡 SESSÕES ATIVAS</div>
          <div style="font-family:'Orbitron',monospace;font-size:0.85rem;color:#00ffcc">{s_ativas}</div>
        </div>
        <div>
          <div style="color:#607090;font-size:0.68rem;letter-spacing:1px">⚡ QUALIDADE</div>
          <div style="font-family:'Orbitron',monospace;font-size:0.95rem;font-weight:700;color:{s_qcor}">{s_qual}</div>
          <div style="color:#607090;font-size:0.72rem">{s_desc}</div>
        </div>
        <div>
          <div style="color:#607090;font-size:0.68rem;letter-spacing:1px">⏭ PRÓXIMA JANELA</div>
          <div style="color:#e0e0e0;font-size:0.8rem">{s_prox}</div>
        </div>
      </div>
      <div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap">
        <span style="background:#aa77ff22;color:#aa77ff;border:1px solid #aa77ff44;padding:1px 8px;border-radius:20px;font-size:0.68rem">🌏 ÁSIA 20h–05h</span>
        <span style="background:#00ffcc22;color:#00ffcc;border:1px solid #00ffcc44;padding:1px 8px;border-radius:20px;font-size:0.68rem">🇬🇧 LONDRES 05h–14h</span>
        <span style="background:#ffaa0022;color:#ffaa00;border:1px solid #ffaa0044;padding:1px 8px;border-radius:20px;font-size:0.68rem">🇺🇸 NY 10h–19h</span>
        <span style="background:#00ff8822;color:#00ff88;border:1px solid #00ff8844;padding:1px 8px;border-radius:20px;font-size:0.68rem">🔥 MELHOR: 10h–14h</span>
      </div>
    </div>""", unsafe_allow_html=True)

    if not ativos_sel:
        st.info("Selecione ativos na sidebar.")
    else:
        cb,ci2 = st.columns([1,3])
        with cb: analisar = st.button("🔍 ANALISAR AGORA", use_container_width=True)
        with ci2: st.caption(f"Timeframe: **{tf_sel}** | Expiração: **{expiracao}** | {datetime.now().strftime('%H:%M:%S')}")

        if analisar:
            st.session_state.analisado = True
            st.session_state.resultados = {}
            with st.spinner("🔄 Buscando dados e calculando sinais..."):
                for nome in ativos_sel:
                    st.session_state.resultados[nome] = buscar(nome, period, interval)

        if not st.session_state.analisado:
            st.markdown("""
            <div style="text-align:center;padding:48px 24px;background:#0d1520;border-radius:12px;
                        border:1px dashed #1a2030;margin-top:16px">
              <div style="font-family:'Orbitron',monospace;color:#607090;font-size:1rem;letter-spacing:2px">
                🎯 AGUARDANDO ANÁLISE
              </div>
              <div style="color:#607090;font-size:0.85rem;margin-top:8px">
                Configure os ativos e clique em <b style="color:#00ffcc">ANALISAR AGORA</b>
              </div>
            </div>""", unsafe_allow_html=True)
        else:
            cols = st.columns(min(len(ativos_sel),3))
            for i,nome in enumerate(ativos_sel):
                df  = st.session_state.resultados.get(nome)
                ticker, payout_ativo, categoria, is_synthetic = ATIVOS[nome]
                with cols[i%len(cols)]:
                    st.markdown(f"""<div style="font-size:0.7rem;color:#607090;margin-bottom:2px">
                        {categoria} &nbsp;|&nbsp; Payout: <b style="color:#00ffcc">{payout_ativo}%</b>
                        {"&nbsp;|&nbsp;<span style='color:#ffaa00'>⚠️ Sintético</span>" if is_synthetic else ""}
                    </div>""", unsafe_allow_html=True)

                    if df is None:
                        st.warning(f"Sem dados: {nome}"); continue
                    sc_c, sc_p = score(df)
                    last = df.iloc[-1]; prev = df.iloc[-2]
                    close = float(last['Close'])
                    pct   = (close/float(prev['Close'])-1)*100
                    dc4   = "#00ff88" if pct>=0 else "#ff4444"
                    st.markdown(card(nome, f"{close:.4f}",
                        f"{'▲' if pct>=0 else '▼'} {abs(pct):.3f}%", dc4), unsafe_allow_html=True)

                    rs_v = float(last['RSI']); mh_v = float(last['MHIST'])
                    at_v = float(last['ATR']);  sk_v = float(last['SK'])
                    c1,c2 = st.columns(2)
                    with c1:
                        rsc = "#00ff88" if rs_v<35 else "#ff4444" if rs_v>65 else "#e0e0e0"
                        st.markdown(f"<small style='color:#607090'>RSI 14</small><br><b style='color:{rsc}'>{rs_v:.1f}</b>", unsafe_allow_html=True)
                        st.markdown(f"<small style='color:#607090'>STOCH K</small><br><b>{sk_v:.1f}</b>", unsafe_allow_html=True)
                    with c2:
                        mhc = "#00ff88" if mh_v>0 else "#ff4444"
                        st.markdown(f"<small style='color:#607090'>MACD Hist</small><br><b style='color:{mhc}'>{mh_v:.5f}</b>", unsafe_allow_html=True)
                        st.markdown(f"<small style='color:#607090'>ATR</small><br><b>{at_v:.5f}</b>", unsafe_allow_html=True)

                    if sc_c>=65 or sc_p>=65:
                        dom   = "CALL" if sc_c>=sc_p else "PUT"
                        scr   = sc_c if dom=="CALL" else sc_p
                        css   = "sig-call" if dom=="CALL" else "sig-put"
                        bc    = "#00ff88" if dom=="CALL" else "#ff4444"
                        acao  = "🟢 COMPRA" if dom=="CALL" else "🔴 VENDA"
                        icon  = "💎 CALL ▲" if dom=="CALL" else "📉 PUT ▼"
                        seg   = EXPIRACAO_SEG[expiracao]
                        mins  = seg//60; segs_r = seg%60
                        tempo_str = f"{mins}min {segs_r:02d}s" if mins else f"{segs_r}s"
                        lucro_est = val_entrada * (payout_ativo/100)

                        # ── Alerta sonoro automático ao detectar sinal ──
                        import streamlit.components.v1 as components
                        freqs_call = "[880,1100,1320]"
                        freqs_put  = "[660,440,330]"
                        freqs = freqs_call if dom=="CALL" else freqs_put
                        components.html(f"""
                        <script>
                        (function(){{
                            try {{
                                var ctx = new (window.AudioContext||window.webkitAudioContext)();
                                var freqs = {freqs};
                                freqs.forEach(function(f,i){{
                                    var o=ctx.createOscillator(),g=ctx.createGain();
                                    o.connect(g);g.connect(ctx.destination);
                                    o.frequency.value=f;
                                    g.gain.setValueAtTime(0.3,ctx.currentTime+i*0.2);
                                    g.gain.exponentialRampToValueAtTime(0.001,ctx.currentTime+i*0.2+0.25);
                                    o.start(ctx.currentTime+i*0.2);
                                    o.stop(ctx.currentTime+i*0.2+0.25);
                                }});
                            }} catch(e){{}}
                        }})();
                        </script>
                        """, height=0)

                        st.markdown(f"""
                        <div class="{css}">
                          <div class="sig-title">{icon}</div>
                          <div style="font-family:'Orbitron',monospace;font-size:1.5rem;font-weight:900;
                                      color:{bc};margin:8px 0;letter-spacing:2px">{acao}</div>
                          <div style="color:#607090;font-size:0.7rem">Score de Confluência</div>
                          <div style="font-family:'Orbitron',monospace;font-size:1.1rem;color:{bc}">{scr}/100</div>
                          <div class="bar-bg"><div class="bar-fill" style="width:{scr}%;background:{bc}"></div></div>
                          <div style="margin-top:10px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px">
                            <div style="background:rgba(0,0,0,0.35);border-radius:6px;padding:8px;text-align:center">
                              <div style="color:#607090;font-size:0.62rem;letter-spacing:1px">⏱ EXPIRAÇÃO</div>
                              <div style="font-family:'Orbitron',monospace;color:#fff;font-size:0.78rem;font-weight:700">{expiracao.upper()}</div>
                            </div>
                            <div style="background:rgba(0,0,0,0.35);border-radius:6px;padding:8px;text-align:center">
                              <div style="color:#607090;font-size:0.62rem;letter-spacing:1px">⏳ FIQUE POR</div>
                              <div style="font-family:'Orbitron',monospace;color:{bc};font-size:0.78rem;font-weight:700">{tempo_str}</div>
                            </div>
                            <div style="background:rgba(0,0,0,0.35);border-radius:6px;padding:8px;text-align:center">
                              <div style="color:#607090;font-size:0.62rem;letter-spacing:1px">💰 LUCRO EST.</div>
                              <div style="font-family:'Orbitron',monospace;color:#00ff88;font-size:0.78rem;font-weight:700">${lucro_est:.2f}</div>
                            </div>
                          </div>
                          <div style="margin-top:8px;background:rgba(0,0,0,0.2);border-radius:6px;
                                      padding:8px 10px;font-size:0.73rem;color:#607090;line-height:1.6">
                            📋 <b>Payout:</b> <span style="color:{bc}">{payout_ativo}%</span> &nbsp;|&nbsp;
                            ✅ <b>Entrada:</b> ${val_entrada:.2f} &nbsp;|&nbsp;
                            💎 <b>Retorno Total:</b> ${val_entrada+lucro_est:.2f}<br>
                            ⏱ Entre agora e aguarde <b style="color:{bc}">{expiracao}</b> para sair.
                          </div>
                        </div>""", unsafe_allow_html=True)
                        st.toast(f"📡 {nome}: {acao} | Payout {payout_ativo}% | {expiracao} ({scr}/100)",
                                 icon="🚀" if dom=="CALL" else "⚠️")
                    else:
                        best = max(sc_c, sc_p)
                        st.markdown(f"""
                        <div class="sig-wait">
                          <div class="sig-title" style="color:#607090">⏳ AGUARDANDO SINAL...</div>
                          <div style="color:#607090;font-size:0.72rem;margin-top:4px">Confluência: {best}/100 &nbsp;|&nbsp; Payout: {payout_ativo}%</div>
                          <div class="bar-bg"><div class="bar-fill" style="width:{best}%;background:#607090"></div></div>
                        </div>""", unsafe_allow_html=True)
                    st.markdown("---")

# ══════════════════════════════════════════
with t2:
    ca,ct = st.columns([2,1])
    with ca: chart_at = st.selectbox("Ativo", list(ATIVOS.keys()), key="ca")
    with ct: chart_tf = st.selectbox("Timeframe", list(TIMEFRAMES.keys()), index=1, key="ct")
    if st.button("📊 Carregar Gráfico", use_container_width=False):
        cp, ci = TIMEFRAMES[chart_tf]
        with st.spinner("Carregando..."):
            dfc = buscar(chart_at, cp, ci)
        if dfc is not None:
            try:
                fig = make_subplots(rows=3,cols=1,shared_xaxes=True,row_heights=[0.55,0.25,0.20],
                    vertical_spacing=0.03,
                    subplot_titles=[f"{chart_at} — Candles","MACD","RSI (14)"])
                fig.add_trace(go.Candlestick(x=dfc.index,open=dfc['Open'],high=dfc['High'],
                    low=dfc['Low'],close=dfc['Close'],
                    increasing_line_color='#00ff88',decreasing_line_color='#ff4444',name="Preço"),row=1,col=1)
                for e,cor in [('E8','#00ffcc'),('E20','#ffaa00'),('E50','#aa77ff')]:
                    fig.add_trace(go.Scatter(x=dfc.index,y=dfc[e],line=dict(color=cor,width=1.5),name=e),row=1,col=1)
                fig.add_trace(go.Scatter(x=dfc.index,y=dfc['BBU'],
                    line=dict(color='rgba(255,255,255,0.15)',width=1,dash='dot'),showlegend=False),row=1,col=1)
                fig.add_trace(go.Scatter(x=dfc.index,y=dfc['BBL'],
                    line=dict(color='rgba(255,255,255,0.15)',width=1,dash='dot'),
                    fill='tonexty',fillcolor='rgba(255,255,255,0.02)',showlegend=False),row=1,col=1)
                ch = ['#00ff88' if v>=0 else '#ff4444' for v in dfc['MHIST']]
                fig.add_trace(go.Bar(x=dfc.index,y=dfc['MHIST'],marker_color=ch,opacity=0.7,name="Hist"),row=2,col=1)
                fig.add_trace(go.Scatter(x=dfc.index,y=dfc['MACD'],line=dict(color='#00ffcc',width=1.5),name="MACD"),row=2,col=1)
                fig.add_trace(go.Scatter(x=dfc.index,y=dfc['MSIG'],line=dict(color='#ffaa00',width=1.5),name="Signal"),row=2,col=1)
                fig.add_trace(go.Scatter(x=dfc.index,y=dfc['RSI'],line=dict(color='#aa77ff',width=2),name="RSI"),row=3,col=1)
                # Níveis RSI com add_shape (compatível com todas versões do plotly)
                for nivel, cor in [(70,"#ff4444"),(30,"#00ff88")]:
                    fig.add_shape(type="line",x0=dfc.index[0],x1=dfc.index[-1],
                        y0=nivel,y1=nivel,line=dict(color=cor,width=1,dash="dash"),row=3,col=1)
                fig.update_layout(template="plotly_dark",paper_bgcolor="#080b14",plot_bgcolor="#0d1520",
                    height=660,margin=dict(l=10,r=10,t=40,b=10),xaxis_rangeslider_visible=False,
                    legend=dict(orientation="h",yanchor="bottom",y=1.01,xanchor="right",x=1))
                fig.update_xaxes(gridcolor="#1a2030"); fig.update_yaxes(gridcolor="#1a2030")
                st.plotly_chart(fig,use_container_width=True)
            except Exception as e:
                st.error(f"Erro: {e}")
        else:
            st.warning("Dados insuficientes.")
    else:
        st.info("Selecione o ativo e clique em **Carregar Gráfico**.")

# ══════════════════════════════════════════
with t3:
    lucro = st.session_state.banca - BANCA_INICIAL
    m1,m2,m3,m4,m5 = st.columns(5)
    for col,lbl,val,cor in [
        (m1,"Total Ops",str(total_ops),"#e0e0e0"),
        (m2,"Wins",str(st.session_state.wins),"#00ff88"),
        (m3,"Losses",str(st.session_state.losses),"#ff4444"),
        (m4,"Lucro",f"${lucro:+.2f}","#00ff88" if lucro>=0 else "#ff4444"),
        (m5,"Sequência",str(st.session_state.seq),"#00ffcc" if st.session_state.seq>=0 else "#ff4444"),
    ]:
        with col: st.markdown(card(lbl,val,dc=cor), unsafe_allow_html=True)

    logs = st.session_state.logs
    if len(logs)>0:
        fig_p = go.Figure()
        fig_p.add_hline(y=BANCA_INICIAL,line_dash="dash",line_color="#607090",annotation_text="Início")
        fig_p.add_trace(go.Scatter(x=logs.index,y=logs['Saldo'],mode='lines+markers',
            line=dict(color='#00ffcc',width=2.5),fill='tozeroy',fillcolor='rgba(0,255,204,0.05)',
            marker=dict(size=6,color=['#00ff88' if v>=0 else '#ff4444' for v in logs['P&L']])))
        fig_p.update_layout(template="plotly_dark",paper_bgcolor="#080b14",plot_bgcolor="#0d1520",
            height=280,title="Curva de Patrimônio",margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(fig_p,use_container_width=True)
        cb2,cd2 = st.columns(2)
        with cb2:
            fig_b=go.Figure(go.Bar(x=logs['Hora'],y=logs['P&L'],
                marker_color=['#00ff88' if v>=0 else '#ff4444' for v in logs['P&L']]))
            fig_b.update_layout(template="plotly_dark",paper_bgcolor="#080b14",plot_bgcolor="#0d1520",
                height=240,title="P&L por Op",margin=dict(l=10,r=10,t=40,b=10))
            st.plotly_chart(fig_b,use_container_width=True)
        with cd2:
            ww=len(logs[logs['Resultado']=='WIN']); ll=len(logs[logs['Resultado']=='LOSS'])
            fig_pie=go.Figure(go.Pie(labels=["WIN","LOSS"],values=[max(ww,0),max(ll,0)],hole=0.6,
                marker_colors=['#00ff88','#ff4444'],textfont_size=13))
            fig_pie.update_layout(template="plotly_dark",paper_bgcolor="#080b14",
                height=240,title="W/L",margin=dict(l=10,r=10,t=40,b=10))
            st.plotly_chart(fig_pie,use_container_width=True)
        st.dataframe(logs,use_container_width=True,height=260)
    else:
        st.info("Nenhuma operação ainda.")

# ══════════════════════════════════════════
with t4:
    st.subheader("📐 Gestão de Risco")
    r1,r2,r3 = st.columns(3)
    with r1:
        st.markdown("#### Kelly Criterion")
        k_wr  = st.slider("Win Rate (%)",30,90,max(30,int(wr*100)))/100
        k_pay = st.slider("Payout (%)",70,95,payout_pct,key="kp")/100
        kf2=kelly(k_wr,k_pay); kv2=st.session_state.banca*kf2
        st.markdown(card("Entrada recomendada",f"${kv2:.2f}",f"{kf2*100:.1f}% da banca","#00ff88"), unsafe_allow_html=True)
    with r2:
        st.markdown("#### Stop Loss / Stop Win")
        sl=st.slider("Stop Loss (%)",5,40,20); sw=st.slider("Stop Win (%)",5,100,30)
        slv=st.session_state.banca*(1-sl/100); swv=st.session_state.banca*(1+sw/100)
        st.markdown(card("🔴 Parar abaixo de",f"${slv:.2f}",dc="#ff4444"), unsafe_allow_html=True)
        st.markdown(card("🟢 Parar acima de", f"${swv:.2f}",dc="#00ff88"), unsafe_allow_html=True)
        if st.session_state.banca<=slv: st.error("🚨 STOP LOSS ATINGIDO!")
        elif st.session_state.banca>=swv: st.success("🏆 STOP WIN ATINGIDO!")
    with r3:
        st.markdown("#### Simulador Martingale")
        mb=st.number_input("Entrada base ($)",1.0,50.0,val_entrada,key="mb")
        mf=st.number_input("Multiplicador",1.5,3.0,2.0,step=0.1,key="mf")
        mn=st.slider("Níveis",2,7,4,key="mn")
        ent=[mb*(mf**i) for i in range(mn)]; tot=sum(ent)
        pct_b=tot/st.session_state.banca*100 if st.session_state.banca>0 else 0
        st.dataframe(pd.DataFrame({
            'Nível':[f"G{i+1}" for i in range(mn)],
            'Entrada':[f"${e:.2f}" for e in ent],
            'Expo.Acum.':[f"${sum(ent[:i+1]):.2f}" for i in range(mn)]
        }),use_container_width=True,hide_index=True)
        rc2="#ff4444" if pct_b>50 else "#ffaa00" if pct_b>25 else "#00ff88"
        st.markdown(card("Risco total",f"${tot:.2f}",f"{pct_b:.1f}% da banca",rc2), unsafe_allow_html=True)
    st.divider()
    logs=st.session_state.logs; avg=float(logs['P&L'].mean()) if len(logs)>0 else 0
    s1,s2,s3,s4=st.columns(4)
    with s1: st.markdown(card("Melhor Seq.",f"+{st.session_state.best_seq}",dc="#00ff88"), unsafe_allow_html=True)
    with s2: st.markdown(card("Pior Seq.",str(st.session_state.worst_seq),dc="#ff4444"), unsafe_allow_html=True)
    with s3:
        c5="#00ff88" if avg>=0 else "#ff4444"
        st.markdown(card("Média P&L",f"${avg:+.2f}",dc=c5), unsafe_allow_html=True)
    with s4:
        c6="#ff4444" if dda>15 else "#ffaa00" if dda>8 else "#00ff88"
        st.markdown(card("Drawdown",f"{dda:.1f}%",dc=c6), unsafe_allow_html=True)
