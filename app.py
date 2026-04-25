import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import numpy as np

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
st.set_page_config(page_title="Axwell Pro | Analista Sniper", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@400;600&display=swap');
html,body,[class*="css"]{font-family:'Rajdhani',sans-serif;color:#e0e0e0;}
.main{background-color:#080b14;}.block-container{padding-top:1.5rem;}
.axwell-header{text-align:center;padding:18px 0 8px;border-bottom:1px solid #00ffcc33;margin-bottom:24px;}
.axwell-header h1{font-family:'Orbitron',monospace;font-size:2.2rem;font-weight:900;color:#00ffcc;letter-spacing:4px;margin:0;text-shadow:0 0 20px #00ffcc66;}
.axwell-header p{color:#607090;font-size:0.85rem;margin-top:4px;letter-spacing:2px;}
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
.stTabs [data-baseweb="tab-list"]{background:#0a0e18;border-bottom:1px solid #1a2030;}
.stTabs [data-baseweb="tab"]{font-family:'Rajdhani',sans-serif;color:#607090;}
.stTabs [aria-selected="true"]{color:#00ffcc !important;border-bottom:2px solid #00ffcc !important;background:#0d1520;}
.stButton>button{border-radius:8px;font-family:'Orbitron',monospace;font-size:0.8rem;font-weight:700;letter-spacing:1px;height:3.2em;border:none;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────
BANCA_INICIAL = 70.0

def init_state():
    defaults = {
        'banca': BANCA_INICIAL, 'banca_max': BANCA_INICIAL,
        'total_wins': 0, 'total_losses': 0,
        'sequencia': 0, 'melhor_sequencia': 0, 'pior_sequencia': 0,
        'logs': pd.DataFrame(columns=['Hora','Ativo','Direção','Resultado','Valor','P&L','Saldo']),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ─────────────────────────────────────────────
#  INDICADORES — CÁLCULO MANUAL SEM pandas-ta
# ─────────────────────────────────────────────
def calc_rsi(s, p=14):
    d = s.diff()
    g = d.clip(lower=0).rolling(p).mean()
    l = (-d.clip(upper=0)).rolling(p).mean()
    rs = g / l.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calc_ema(s, span):
    return s.ewm(span=span, adjust=False).mean()

def calc_macd(s):
    e12 = calc_ema(s, 12); e26 = calc_ema(s, 26)
    macd = e12 - e26; sig = calc_ema(macd, 9)
    return macd, sig, macd - sig

def calc_bbands(s, p=20, std=2):
    m = s.rolling(p).mean(); sigma = s.rolling(p).std()
    return m + std*sigma, m, m - std*sigma

def calc_stoch(h, l, c, k=14, d=3):
    lo = l.rolling(k).min(); hi = h.rolling(k).max()
    sk = 100 * (c - lo) / (hi - lo).replace(0, np.nan)
    return sk, sk.rolling(d).mean()

def calc_atr(h, l, c, p=14):
    tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(p).mean()

def calcular_indicadores(df):
    c = df['Close']; h = df['High']; l = df['Low']
    df = df.copy()
    df['RSI'] = calc_rsi(c)
    df['EMA_8']  = calc_ema(c, 8)
    df['EMA_20'] = calc_ema(c, 20)
    df['EMA_50'] = calc_ema(c, 50)
    df['MACD'], df['MACD_SIGNAL'], df['MACD_HIST'] = calc_macd(c)
    df['BB_UPPER'], df['BB_MID'], df['BB_LOWER'] = calc_bbands(c)
    df['STOCH_K'], df['STOCH_D'] = calc_stoch(h, l, c)
    df['ATR'] = calc_atr(h, l, c)
    return df.dropna()

# ─────────────────────────────────────────────
#  DADOS
# ─────────────────────────────────────────────
ATIVOS = {
    "EURUSD":"EURUSD=X","GBPUSD":"GBPUSD=X","USDJPY":"JPY=X","AUDUSD":"AUDUSD=X",
    "BTC/USD":"BTC-USD","ETH/USD":"ETH-USD","SOL/USD":"SOL-USD",
    "Ouro":"GC=F","Petróleo":"CL=F","S&P 500":"^GSPC","Nasdaq":"^IXIC",
}
TIMEFRAMES = {"1 min":("1d","1m"),"5 min":("5d","5m"),"15 min":("1mo","15m"),"1 hora":("3mo","1h")}

@st.cache_data(ttl=30, show_spinner=False)
def buscar_dados(ticker, period, interval):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        if df.empty or len(df) < 50:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[['Open','High','Low','Close','Volume']].copy()
        df = df.apply(pd.to_numeric, errors='coerce').dropna()
        return df
    except Exception:
        return None

# ─────────────────────────────────────────────
#  SCORE
# ─────────────────────────────────────────────
def calcular_score(df):
    if df is None or len(df) < 2: return 0, 0
    row = df.iloc[-1]; prev = df.iloc[-2]
    sc = sp = 0

    def flt(col, default=0):
        v = row.get(col, default)
        return float(v) if not pd.isna(v) else default

    def flt2(col, default=0):
        v = prev.get(col, default)
        return float(v) if not pd.isna(v) else default

    rsi = flt('RSI', 50)
    if rsi < 30: sc += 20
    elif rsi < 40: sc += 10
    elif rsi > 70: sp += 20
    elif rsi > 60: sp += 10

    if flt('EMA_8') > flt('EMA_20'): sc += 15
    else: sp += 15
    if flt('EMA_20') > flt('EMA_50'): sc += 10
    else: sp += 10

    h_now = flt('MACD_HIST'); h_prev = flt2('MACD_HIST')
    if h_now > 0 and h_now > h_prev: sc += 20
    elif h_now < 0 and h_now < h_prev: sp += 20

    close = flt('Close'); bbl = flt('BB_LOWER'); bbu = flt('BB_UPPER')
    if bbl and close < bbl * 1.001: sc += 20
    elif bbu and close > bbu * 0.999: sp += 20

    k = flt('STOCH_K', 50); d = flt('STOCH_D', 50)
    if k < 20 and k > d: sc += 15
    elif k > 80 and k < d: sp += 15

    return min(sc, 100), min(sp, 100)

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def kelly_fraction(wr, pay):
    if wr <= 0 or pay <= 0: return 0.0
    return max(0.0, (wr * pay - (1 - wr)) / pay)

def risco_banca(banca, entrada):
    pct = (entrada / banca * 100) if banca > 0 else 0
    if pct > 5: return "ALTO","badge-alto"
    if pct > 2: return "MÉDIO","badge-medio"
    return "BAIXO","badge-baixo"

def drawdown_atual():
    bmax = st.session_state.banca_max
    return ((bmax - st.session_state.banca) / bmax * 100) if bmax > 0 else 0.0

def registrar_op(ativo, direcao, resultado, valor, payout_pct):
    pnl = valor * (payout_pct/100) if resultado == "WIN" else -valor
    st.session_state.banca += pnl
    st.session_state.banca_max = max(st.session_state.banca_max, st.session_state.banca)
    if resultado == "WIN":
        st.session_state.total_wins += 1
        st.session_state.sequencia = max(0, st.session_state.sequencia) + 1
        st.session_state.melhor_sequencia = max(st.session_state.melhor_sequencia, st.session_state.sequencia)
    else:
        st.session_state.total_losses += 1
        st.session_state.sequencia = min(0, st.session_state.sequencia) - 1
        st.session_state.pior_sequencia = min(st.session_state.pior_sequencia, st.session_state.sequencia)
    nova = {'Hora': datetime.now().strftime("%H:%M:%S"), 'Ativo': ativo, 'Direção': direcao,
            'Resultado': resultado, 'Valor': valor, 'P&L': round(pnl, 2), 'Saldo': round(st.session_state.banca, 2)}
    st.session_state.logs = pd.concat([st.session_state.logs, pd.DataFrame([nova])], ignore_index=True)

def mcard(label, value, delta="", dc="#607090"):
    d = f'<div class="delta" style="color:{dc}">{delta}</div>' if delta else ""
    return f'<div class="metric-card"><div class="label">{label}</div><div class="value">{value}</div>{d}</div>'

# ─────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div class="axwell-header">
    <h1>⬡ AXWELL PRO</h1>
    <p>ANALISTA SNIPER v4.0 &nbsp;|&nbsp; ROYAL CAPITAL &nbsp;|&nbsp; INTELIGÊNCIA QUANTITATIVA</p>
</div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🛡️ GESTÃO DE BANCA")
    total_ops = st.session_state.total_wins + st.session_state.total_losses
    win_rate  = st.session_state.total_wins / total_ops if total_ops > 0 else 0
    dd        = drawdown_atual()
    banca_delta = st.session_state.banca - BANCA_INICIAL
    dc = "#00ff88" if banca_delta >= 0 else "#ff4444"
    ds = f"{'▲' if banca_delta >= 0 else '▼'} ${abs(banca_delta):.2f} ({banca_delta/BANCA_INICIAL*100:+.1f}%)"
    st.markdown(mcard("Saldo Atual", f"${st.session_state.banca:.2f}", ds, dc), unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        ddc = "#ff4444" if dd>15 else "#ffaa00" if dd>8 else "#00ff88"
        st.markdown(mcard("Drawdown", f"{dd:.1f}%", dc=ddc), unsafe_allow_html=True)
    with c2:
        wrc = "#00ff88" if win_rate>=0.6 else "#ffaa00" if win_rate>=0.4 else "#ff4444"
        st.markdown(mcard("Win Rate", f"{win_rate*100:.0f}%", dc=wrc), unsafe_allow_html=True)

    st.divider()
    st.markdown("### ⚙️ PARÂMETROS")
    ativos_sel  = st.multiselect("Ativos Monitorados", list(ATIVOS.keys()), default=["EURUSD","BTC/USD"])
    tf_sel      = st.selectbox("Timeframe", list(TIMEFRAMES.keys()), index=1)
    val_entrada = st.number_input("Entrada ($)", 1.0, 100.0, 2.0, step=0.5)
    payout_pct  = st.slider("Payout (%)", 70, 95, 89)
    period, interval = TIMEFRAMES[tf_sel]

    kf = kelly_fraction(win_rate, payout_pct/100)
    kv = st.session_state.banca * kf
    rl, rb = risco_banca(st.session_state.banca, val_entrada)
    st.markdown(f"""
    <div style="padding:10px 14px;background:#0d1520;border-radius:8px;border:1px solid #1a2030;margin-top:8px">
        <span style="color:#607090;font-size:0.72rem;letter-spacing:1px">KELLY CRITERION</span>
        <div style="font-family:'Orbitron',monospace;color:#00ffcc;font-size:1rem;margin:4px 0">${kv:.2f}
            <span style="font-size:0.75rem;color:#607090">({kf*100:.1f}%)</span></div>
        <span class="badge {rb}">Risco: {rl}</span>
    </div>""", unsafe_allow_html=True)

    if dd >= 20: st.error("⛔ DRAWDOWN CRÍTICO — Pause!")
    elif dd >= 10: st.warning("⚠️ Drawdown elevado.")

    st.divider()
    st.markdown("### 📋 LANÇAR RESULTADO")
    ativo_manual = st.selectbox("Ativo", list(ATIVOS.keys()))
    dir_manual   = st.radio("Direção", ["CALL ▲","PUT ▼"], horizontal=True)
    cw, cl = st.columns(2)
    if cw.button("✅ WIN",  use_container_width=True):
        registrar_op(ativo_manual, dir_manual, "WIN",  val_entrada, payout_pct); st.balloons(); st.rerun()
    if cl.button("❌ LOSS", use_container_width=True):
        registrar_op(ativo_manual, dir_manual, "LOSS", val_entrada, payout_pct); st.rerun()

    st.divider()
    if st.button("🔄 Resetar Banca", use_container_width=True):
        for k in ['banca','banca_max','total_wins','total_losses','sequencia','melhor_sequencia','pior_sequencia','logs']:
            del st.session_state[k]
        st.rerun()

# ─────────────────────────────────────────────
#  ABAS
# ─────────────────────────────────────────────
tab_sniper, tab_chart, tab_perf, tab_risco = st.tabs([
    "🎯 Sniper Board","📊 Gráfico Avançado","📈 Performance","🛡️ Gestão de Risco"])

# ══ SNIPER ══════════════════════════════════
with tab_sniper:
    if not ativos_sel:
        st.info("Selecione ao menos um ativo.")
    else:
        st.caption(f"Timeframe: **{tf_sel}** | {datetime.now().strftime('%H:%M:%S')}")
        if st.button("🔁 Atualizar"): st.cache_data.clear()
        cols = st.columns(min(len(ativos_sel), 3))
        for i, nome in enumerate(ativos_sel):
            col = cols[i % len(cols)]
            with col:
                with st.spinner(f"Carregando {nome}..."):
                    df = buscar_dados(ATIVOS[nome], period, interval)
                if df is None: st.warning(f"Sem dados: {nome}"); continue
                try: df = calcular_indicadores(df)
                except Exception as e: st.warning(f"Erro: {e}"); continue

                sc, sp = calcular_score(df)
                last = df.iloc[-1]; prev = df.iloc[-2]
                close = float(last['Close']); pct = (close/float(prev['Close'])-1)*100
                dc2 = "#00ff88" if pct >= 0 else "#ff4444"
                st.markdown(mcard(ATIVOS[nome], f"{close:.5f}", f"{'▲' if pct>=0 else '▼'} {abs(pct):.3f}%", dc2), unsafe_allow_html=True)

                rsi_v = float(last['RSI']); mh = float(last['MACD_HIST'])
                atr_v = float(last['ATR']); stk = float(last['STOCH_K'])
                a, b = st.columns(2)
                with a:
                    rc = "#00ff88" if rsi_v<35 else "#ff4444" if rsi_v>65 else "#e0e0e0"
                    st.markdown(f"<small style='color:#607090'>RSI 14</small><br><b style='color:{rc}'>{rsi_v:.1f}</b>", unsafe_allow_html=True)
                    st.markdown(f"<small style='color:#607090'>STOCH K</small><br><b>{stk:.1f}</b>", unsafe_allow_html=True)
                with b:
                    mc2 = "#00ff88" if mh>0 else "#ff4444"
                    st.markdown(f"<small style='color:#607090'>MACD Hist</small><br><b style='color:{mc2}'>{mh:.5f}</b>", unsafe_allow_html=True)
                    st.markdown(f"<small style='color:#607090'>ATR</small><br><b>{atr_v:.5f}</b>", unsafe_allow_html=True)

                if sc >= 65 or sp >= 65:
                    dom = "CALL" if sc >= sp else "PUT"
                    score = sc if dom=="CALL" else sp
                    css  = "signal-call" if dom=="CALL" else "signal-put"
                    icon = "💎 CALL ▲" if dom=="CALL" else "📉 PUT ▼"
                    bc   = "#00ff88" if dom=="CALL" else "#ff4444"
                    st.markdown(f"""
                    <div class="{css}">
                        <div class="signal-title">{icon}</div>
                        <div style="color:#607090;font-size:0.75rem;margin-top:2px">Score de Confluência</div>
                        <div style="font-family:'Orbitron',monospace;font-size:1.2rem;color:{bc}">{score}/100</div>
                        <div class="score-bar-bg"><div class="score-bar-fill" style="width:{score}%;background:{bc}"></div></div>
                        <div style="color:#607090;font-size:0.75rem;margin-top:6px">⏱ Expiração: {tf_sel} × 2</div>
                    </div>""", unsafe_allow_html=True)
                    st.toast(f"📡 {nome}: {dom} ({score}/100)", icon="🚀" if dom=="CALL" else "⚠️")
                else:
                    best = max(sc, sp)
                    st.markdown(f"""
                    <div class="signal-wait">
                        <div class="signal-title" style="color:#607090">⏳ AGUARDANDO...</div>
                        <div style="color:#607090;font-size:0.75rem;margin-top:4px">Confluência: {best}/100</div>
                        <div class="score-bar-bg"><div class="score-bar-fill" style="width:{best}%;background:#607090"></div></div>
                    </div>""", unsafe_allow_html=True)
                st.markdown("---")

# ══ GRÁFICO ═════════════════════════════════
with tab_chart:
    ca, ct = st.columns([2,1])
    with ca: chart_ativo = st.selectbox("Ativo", list(ATIVOS.keys()), key="ca")
    with ct: chart_tf    = st.selectbox("Timeframe", list(TIMEFRAMES.keys()), index=1, key="ct")
    cp, ci = TIMEFRAMES[chart_tf]
    with st.spinner("Carregando gráfico..."):
        dfc = buscar_dados(ATIVOS[chart_ativo], cp, ci)
    if dfc is not None and len(dfc) > 50:
        try:
            dfc = calcular_indicadores(dfc)
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.55,0.25,0.20],
                                vertical_spacing=0.03,
                                subplot_titles=[f"{chart_ativo} — Candles + EMAs + Bollinger","MACD","RSI (14)"])
            fig.add_trace(go.Candlestick(x=dfc.index, open=dfc['Open'], high=dfc['High'],
                low=dfc['Low'], close=dfc['Close'],
                increasing_line_color='#00ff88', decreasing_line_color='#ff4444', name="Preço"), row=1, col=1)
            for ema, color in [('EMA_8','#00ffcc'),('EMA_20','#ffaa00'),('EMA_50','#aa77ff')]:
                fig.add_trace(go.Scatter(x=dfc.index, y=dfc[ema], line=dict(color=color,width=1.5),
                    name=ema.replace('_',' ')), row=1, col=1)
            fig.add_trace(go.Scatter(x=dfc.index, y=dfc['BB_UPPER'],
                line=dict(color='rgba(255,255,255,0.2)',width=1,dash='dot'), showlegend=False), row=1, col=1)
            fig.add_trace(go.Scatter(x=dfc.index, y=dfc['BB_LOWER'],
                line=dict(color='rgba(255,255,255,0.2)',width=1,dash='dot'),
                fill='tonexty', fillcolor='rgba(255,255,255,0.03)', showlegend=False), row=1, col=1)
            colors_h = ['#00ff88' if v >= 0 else '#ff4444' for v in dfc['MACD_HIST']]
            fig.add_trace(go.Bar(x=dfc.index, y=dfc['MACD_HIST'], marker_color=colors_h, opacity=0.7, name="Hist"), row=2, col=1)
            fig.add_trace(go.Scatter(x=dfc.index, y=dfc['MACD'], line=dict(color='#00ffcc',width=1.5), name="MACD"), row=2, col=1)
            fig.add_trace(go.Scatter(x=dfc.index, y=dfc['MACD_SIGNAL'], line=dict(color='#ffaa00',width=1.5), name="Signal"), row=2, col=1)
            fig.add_trace(go.Scatter(x=dfc.index, y=dfc['RSI'], line=dict(color='#aa77ff',width=2), name="RSI"), row=3, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="#ff444455", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="#00ff8855", row=3, col=1)
            fig.update_layout(template="plotly_dark", paper_bgcolor="#080b14", plot_bgcolor="#0d1520",
                height=680, margin=dict(l=10,r=10,t=40,b=10), xaxis_rangeslider_visible=False,
                legend=dict(orientation="h",yanchor="bottom",y=1.01,xanchor="right",x=1),
                font=dict(family="Rajdhani"))
            fig.update_xaxes(gridcolor="#1a2030"); fig.update_yaxes(gridcolor="#1a2030")
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao renderizar: {e}")
    else:
        st.warning("Dados insuficientes. Tente outro ativo ou timeframe.")

# ══ PERFORMANCE ══════════════════════════════
with tab_perf:
    lucro = st.session_state.banca - BANCA_INICIAL
    m1,m2,m3,m4,m5 = st.columns(5)
    for col, lbl, val, color in [
        (m1,"Total Ops",str(total_ops),"#e0e0e0"),
        (m2,"Wins",str(st.session_state.total_wins),"#00ff88"),
        (m3,"Losses",str(st.session_state.total_losses),"#ff4444"),
        (m4,"Lucro Líquido",f"${lucro:+.2f}","#00ff88" if lucro>=0 else "#ff4444"),
        (m5,"Seq. Atual",str(st.session_state.sequencia),"#00ffcc" if st.session_state.sequencia>=0 else "#ff4444"),
    ]:
        with col: st.markdown(mcard(lbl, val, dc=color), unsafe_allow_html=True)

    logs = st.session_state.logs
    if len(logs) > 0:
        fig_p = go.Figure()
        fig_p.add_hline(y=BANCA_INICIAL, line_dash="dash", line_color="#607090")
        fig_p.add_trace(go.Scatter(x=logs.index, y=logs['Saldo'], mode='lines+markers',
            line=dict(color='#00ffcc',width=2.5), fill='tozeroy', fillcolor='rgba(0,255,204,0.05)',
            marker=dict(size=5, color=['#00ff88' if v>=0 else '#ff4444' for v in logs['P&L']])))
        fig_p.update_layout(template="plotly_dark", paper_bgcolor="#080b14", plot_bgcolor="#0d1520",
            height=280, title="Curva de Patrimônio", margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(fig_p, use_container_width=True)

        cb, cd = st.columns(2)
        with cb:
            fig_b = go.Figure(go.Bar(x=logs['Hora'], y=logs['P&L'],
                marker_color=['#00ff88' if v>=0 else '#ff4444' for v in logs['P&L']]))
            fig_b.update_layout(template="plotly_dark", paper_bgcolor="#080b14", plot_bgcolor="#0d1520",
                height=250, title="P&L por Operação", margin=dict(l=10,r=10,t=40,b=10))
            st.plotly_chart(fig_b, use_container_width=True)
        with cd:
            w = len(logs[logs['Resultado']=='WIN']); l = len(logs[logs['Resultado']=='LOSS'])
            fig_pie = go.Figure(go.Pie(labels=["WIN","LOSS"], values=[w,l], hole=0.6,
                marker_colors=['#00ff88','#ff4444'], textfont_size=14))
            fig_pie.update_layout(template="plotly_dark", paper_bgcolor="#080b14",
                height=250, title="W/L", margin=dict(l=10,r=10,t=40,b=10))
            st.plotly_chart(fig_pie, use_container_width=True)

        st.subheader("Histórico")
        st.dataframe(logs, use_container_width=True, height=280)
    else:
        st.info("Nenhuma operação registrada ainda.")

# ══ RISCO ════════════════════════════════════
with tab_risco:
    st.subheader("📐 Calculadora de Gestão de Risco")
    r1, r2, r3 = st.columns(3)
    with r1:
        st.markdown("#### Kelly Criterion")
        k_wr  = st.slider("Win Rate (%)", 30, 90, max(30, int(win_rate*100))) / 100
        k_pay = st.slider("Payout (%)", 70, 95, payout_pct, key="kp") / 100
        kf2   = kelly_fraction(k_wr, k_pay); kv2 = st.session_state.banca * kf2
        st.markdown(mcard("Entrada recomendada", f"${kv2:.2f}", f"{kf2*100:.1f}% da banca", "#00ff88"), unsafe_allow_html=True)

    with r2:
        st.markdown("#### Stop Loss / Stop Win")
        sl_pct = st.slider("Stop Loss (%)", 5, 40, 20)
        sw_pct = st.slider("Stop Win (%)", 5, 100, 30)
        sl_val = st.session_state.banca * (1 - sl_pct/100)
        sw_val = st.session_state.banca * (1 + sw_pct/100)
        st.markdown(mcard("🔴 Parar abaixo de", f"${sl_val:.2f}", dc="#ff4444"), unsafe_allow_html=True)
        st.markdown(mcard("🟢 Parar acima de",  f"${sw_val:.2f}", dc="#00ff88"), unsafe_allow_html=True)
        if st.session_state.banca <= sl_val: st.error("🚨 STOP LOSS ATINGIDO!")
        elif st.session_state.banca >= sw_val: st.success("🏆 STOP WIN ATINGIDO!")

    with r3:
        st.markdown("#### Simulador Martingale")
        mb = st.number_input("Entrada base ($)", 1.0, 50.0, val_entrada, key="mb")
        mf = st.number_input("Multiplicador", 1.5, 3.0, 2.0, step=0.1, key="mf")
        mn = st.slider("Níveis", 2, 7, 4, key="mn")
        ent = [mb * (mf**i) for i in range(mn)]
        total_exp = sum(ent)
        pct_b = total_exp / st.session_state.banca * 100 if st.session_state.banca > 0 else 0
        st.dataframe(pd.DataFrame({
            'Nível':[f"G{i+1}" for i in range(mn)],
            'Entrada':[f"${e:.2f}" for e in ent],
            'Expo. Acum.':[f"${sum(ent[:i+1]):.2f}" for i in range(mn)]
        }), use_container_width=True, hide_index=True)
        rc = "#ff4444" if pct_b>50 else "#ffaa00" if pct_b>25 else "#00ff88"
        st.markdown(mcard("Risco total", f"${total_exp:.2f}", f"{pct_b:.1f}% da banca", rc), unsafe_allow_html=True)

    st.divider()
    logs = st.session_state.logs
    avg_pnl = float(logs['P&L'].mean()) if len(logs) > 0 else 0
    s1,s2,s3,s4 = st.columns(4)
    with s1: st.markdown(mcard("Melhor Sequência", f"+{st.session_state.melhor_sequencia}", dc="#00ff88"), unsafe_allow_html=True)
    with s2: st.markdown(mcard("Pior Sequência", str(st.session_state.pior_sequencia), dc="#ff4444"), unsafe_allow_html=True)
    with s3:
        c = "#00ff88" if avg_pnl>=0 else "#ff4444"
        st.markdown(mcard("Média P&L/Op", f"${avg_pnl:+.2f}", dc=c), unsafe_allow_html=True)
    with s4:
        c = "#ff4444" if dd>15 else "#ffaa00" if dd>8 else "#00ff88"
        st.markdown(mcard("Drawdown Atual", f"{dd:.1f}%", dc=c), unsafe_allow_html=True)
