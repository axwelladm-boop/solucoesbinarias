import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np

# --- 1. CONFIGURAÇÃO DE ALTA PERFORMANCE ---
st.set_page_config(page_title="AXWELL PRO | QUANT SNIPER", layout="wide", initial_sidebar_state="expanded")

# --- 2. ESTILIZAÇÃO UI/UX PREMIUM (SISTEMA INTEGRADO) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Rajdhani:wght@400;600&display=swap');
    html,body,[class*="css"]{font-family:'Rajdhani',sans-serif;color:#e0e0e0;background-color: #05080d;}
    .main{background:#080b14;}.block-container{padding-top:1rem;}
    .axwell-header{text-align:center;padding:14px 0 6px;border-bottom:1px solid #00ffcc33;margin-bottom:20px;}
    .axwell-header h1{font-family:'Orbitron',monospace;font-size:2rem;font-weight:900;color:#00ffcc;letter-spacing:4px;margin:0;}
    .axwell-header p{color:#607090;font-size:0.8rem;margin-top:4px;letter-spacing:2px;}
    .card{background:#0d1520;border:1px solid #00ffcc22;border-radius:10px;padding:14px 18px;margin-bottom:8px;}
    .card .lbl{color:#607090;font-size:0.7rem;letter-spacing:1px;text-transform:uppercase;}
    .card .val{font-family:'Orbitron',monospace;font-size:1.4rem;color:#00ffcc;font-weight:700;}
    .card .dlt{font-size:0.8rem;margin-top:2px;}
    .signal-card { background: #0a111e; border: 2px solid #00ffcc; border-radius: 15px; padding: 25px; text-align: center; box-shadow: 0 0 30px #00ffcc44; margin-bottom: 20px; }
    .sig-call{background:#06180e;border:1px solid #00ff8844;border-left:4px solid #00ff88;border-radius:10px;padding:16px;margin:8px 0;}
    .sig-put{background:#180606;border:1px solid #ff444444;border-left:4px solid #ff4444;border-radius:10px;padding:16px;margin:8px 0;}
    .sig-wait{background:#0d1520;border:1px solid #607090;border-left:4px solid #607090;border-radius:10px;padding:16px;margin:8px 0;}
    .buy-text { color: #00ff88; font-family: 'Orbitron'; font-size: 2.3rem; text-shadow: 0 0 15px #00ff88; }
    .sell-text { color: #ff4444; font-family: 'Orbitron'; font-size: 2.3rem; text-shadow: 0 0 15px #ff4444; }
    .bar-bg{background:#1a1f2e;border-radius:4px;height:7px;margin-top:5px;overflow:hidden;}
    .bar-fill{height:7px;border-radius:4px;}
    .sess-box{background:#0d1520;border:1px solid #1a2030;border-radius:10px;padding:14px 18px;margin-bottom:16px;}
    .timer-highlight { color: #ffaa00; font-size: 1.6rem; font-weight: bold; border: 1px solid #ffaa00; padding: 5px 15px; border-radius: 5px; }
    .stButton>button{border-radius:8px;font-family:'Orbitron',monospace;font-size:0.75rem;font-weight:700;letter-spacing:1px;height:3.5em; width:100%;}
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ──────────────────────────────
BANCA_INICIAL = 70.0
ATIVOS = {
    "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "JPY=X",
    "AUDUSD": "AUDUSD=X", "BTC/USD": "BTC-USD",  "ETH/USD": "ETH-USD",
    "SOL/USD": "SOL-USD",  "Ouro":     "GC=F",      "Petróleo": "CL=F",
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

# ── SESSION STATE ──────────────────────────
if 'banca' not in st.session_state:
    st.session_state.banca = BANCA_INICIAL
    st.session_state.banca_max = BANCA_INICIAL
    st.session_state.wins = 0
    st.session_state.losses = 0
    st.session_state.seq = 0
    st.session_state.best_seq = 0
    st.session_state.worst_seq = 0
    st.session_state.logs = pd.DataFrame(columns=['Hora','Ativo','Direção','Resultado','Valor','P&L','Saldo'])
    st.session_state.resultados = {}
    st.session_state.analisado = False

# ── SISTEMA DE ÁUDIO ──
def play_alert():
    audio_html = '<audio autoplay><source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg"></audio>'
    st.components.v1.html(audio_html, height=0)

# ── INDICADORES TÉCNICOS ──────────────────
def ema(s, n):   return s.ewm(span=n, adjust=False).mean()
def rsi(s, n=14):
    d = s.diff(); g = d.clip(lower=0).rolling(n).mean(); l = (-d.clip(upper=0)).rolling(n).mean()
    return 100 - 100/(1 + g/l.replace(0,np.nan))
def macd(s):
    m = ema(s,12)-ema(s,26); sg = ema(m,9); return m, sg, m-sg
def bbands(s, n=20):
    m = s.rolling(n).mean(); sd = s.rolling(n).std(); return m+2*sd, m, m-2*sd
def stoch(h, l, c, k=14, d=3):
    lo = l.rolling(k).min(); hi = h.rolling(k).max()
    sk = 100*(c-lo)/(hi-lo).replace(0,np.nan); return sk, sk.rolling(d).mean()
def atr(h, l, c, n=14):
    tr = pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1); return tr.rolling(n).mean()

def calcular_indicadores(df):
    df = df.copy(); c, h, l = df['Close'], df['High'], df['Low']
    df['RSI'] = rsi(c); df['E8'] = ema(c,8); df['E20'] = ema(c,20); df['E50'] = ema(c,50)
    df['MACD'], df['MSIG'], df['MHIST'] = macd(c)
    df['BBU'], df['BBM'], df['BBL'] = bbands(c)
    df['SK'], df['SD'] = stoch(h,l,c); df['ATR'] = atr(h,l,c)
    return df.dropna()

def calcular_score_confluencia(df):
    if df is None or len(df)<2: return 0, 0
    r = df.iloc[-1]; p = df.iloc[-2]; sc = sp = 0
    rs = float(r['RSI'])
    if rs < 30: sc += 20
    elif rs < 40: sc += 10
    elif rs > 70: sp += 20
    elif rs > 60: sp += 10
    if float(r['E8']) > float(r['E20']): sc += 15
    else: sp += 15
    if float(r['MHIST']) > float(p['MHIST']): sc += 20
    else: sp += 20
    cl, bl, bu = float(r['Close']), float(r['BBL']), float(r['BBU'])
    if cl < bl * 1.001: sc += 20
    elif cl > bu * 0.999: sp += 20
    return min(sc, 100), min(sp, 100)

def buscar_dados(ticker, period, interval):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        if df.empty or len(df)<20: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df[['Open','High','Low','Close','Volume']].copy().ffill().dropna()
        return calcular_indicadores(df)
    except: return None

# ── HELPERS GESTÃO ──────────────────────────
def kelly_criterion(wr, pay):
    if wr <= 0 or pay <= 0: return 0.0
    return max(0.0, (wr * pay - (1 - wr)) / pay)

def registrar_op(ativo, direcao, resultado, valor, payout):
    pnl = valor * (payout/100) if resultado == "WIN" else -valor
    st.session_state.banca += pnl
    st.session_state.banca_max = max(st.session_state.banca_max, st.session_state.banca)
    if resultado == "WIN":
        st.session_state.wins += 1
        st.session_state.seq = max(0, st.session_state.seq) + 1
    else:
        st.session_state.losses += 1
        st.session_state.seq = min(0, st.session_state.seq) - 1
    st.session_state.best_seq = max(st.session_state.best_seq, st.session_state.seq)
    st.session_state.worst_seq = min(st.session_state.worst_seq, st.session_state.seq)
    row = {'Hora': datetime.now().strftime("%H:%M:%S"), 'Ativo': ativo, 'Direção': direcao,
           'Resultado': resultado, 'Valor': valor, 'P&L': round(pnl, 2), 'Saldo': round(st.session_state.banca, 2)}
    st.session_state.logs = pd.concat([st.session_state.logs, pd.DataFrame([row])], ignore_index=True)

def sessoes_mercado():
    h_utc = datetime.utcnow().hour + datetime.utcnow().minute/60
    ativas = []
    if 0 <= h_utc < 9: ativas.append("🌏 Ásia")
    if 8 <= h_utc < 17: ativas.append("🇬🇧 Londres")
    if 13 <= h_utc < 22: ativas.append("🇺🇸 Nova York")
    q, qc = ("🟢 ALTA", "#00ff88") if 13 <= h_utc < 17 else ("🟡 MÉDIA", "#ffaa00") if ativas else ("🔴 BAIXA", "#ff4444")
    return " · ".join(ativas) or "Nenhuma", q, qc

# ── HEADER ─────────────────────────────────
st.markdown('<div class="axwell-header"><h1>⬡ AXWELL PRO</h1><p>QUANT SNIPER v4.5 | ROYAL CAPITAL | ERRO ZERO</p></div>', unsafe_allow_html=True)

# ── SIDEBAR ────────────────────────────────
with st.sidebar:
    st.markdown(f"### 🛡️ BANCA: ${st.session_state.banca:.2f}")
    total_ops = st.session_state.wins + st.session_state.losses
    wr = (st.session_state.wins / total_ops) if total_ops > 0 else 0.0
    st.markdown(f"**Win Rate:** {wr*100:.1f}% | **DD:** {((st.session_state.banca_max-st.session_state.banca)/st.session_state.banca_max*100):.1f}%")
    
    st.divider()
    ativos_sel = st.multiselect("Scan Ativos", list(ATIVOS.keys()), default=["EURUSD", "BTC/USD"])
    tf_sel = st.selectbox("Timeframe", list(TIMEFRAMES.keys()), index=0)
    val_entrada = st.number_input("Entrada ($)", 1.0, 1000.0, 2.0)
    payout_pct = st.slider("Payout %", 70, 95, 87)
    expiracao = st.selectbox("Expiração", list(EXPIRACAO_SEG.keys()), index=1)
    
    st.divider()
    st.subheader("📝 Registrar")
    am = st.selectbox("Ativo Op", list(ATIVOS.keys()))
    dm = st.radio("Lado", ["CALL ▲", "PUT ▼"], horizontal=True)
    c_w, c_l = st.columns(2)
    if c_w.button("✅ WIN"): registrar_op(am, dm, "WIN", val_entrada, payout_pct); st.balloons(); st.rerun()
    if c_l.button("❌ LOSS"): registrar_op(am, dm, "LOSS", val_entrada, payout_pct); st.rerun()
    
    if st.button("🔄 RESET GERAL"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

# ── ABAS PRINCIPAIS ────────────────────────
t1, t2, t3, t4 = st.tabs(["🎯 Sniper Board", "📊 Gráfico", "📈 Performance", "🛡️ Risco"])

with t1:
    s_at, s_q, s_qc = sessoes_mercado()
    st.markdown(f'<div class="sess-box" style="border-left:4px solid {s_qc}"><b>Sessões:</b> {s_at} | <b>Qualidade:</b> <span style="color:{s_qc}">{s_q}</span></div>', unsafe_allow_html=True)
    
    if st.button("🔍 EXECUTAR VARREDURA SNIPER", use_container_width=True):
        st.session_state.resultados = {}
        st.session_state.analisado = True
        with st.spinner("Analisando confluências..."):
            for nome in ativos_sel:
                p, i = TIMEFRAMES[tf_sel]
                df = buscar_dados(ATIVOS[nome], p, i)
                if df is not None:
                    sc_c, sc_p = calcular_score_confluencia(df)
                    st.session_state.resultados[nome] = {"df": df, "sc_c": sc_c, "sc_p": sc_p}

    if st.session_state.analisado:
        cols = st.columns(min(len(ativos_sel), 3))
        for idx, nome in enumerate(st.session_state.resultados):
            res = st.session_state.resultados[nome]
            df, sc_c, sc_p = res["df"], res["sc_c"], res["sc_p"]
            with cols[idx % 3]:
                st.markdown(f'<div class="card"><div class="lbl">{nome}</div><div class="val">{df.iloc[-1]["Close"]:.5f}</div></div>', unsafe_allow_html=True)
                
                if sc_c >= 70 or sc_p >= 70:
                    play_alert()
                    tipo = "CALL ▲" if sc_c >= sc_p else "PUT ▼"
                    cor = "#00ff88" if "CALL" in tipo else "#ff4444"
                    scr = max(sc_c, sc_p)
                    st.markdown(f"""
                    <div class="{"sig-call" if "CALL" in tipo else "sig-put"}">
                        <div class="sig-title" style="color:{cor}">{tipo} DETECTADO</div>
                        <div style="font-size:1.8rem; font-weight:900; color:{cor}">{scr}% SCORE</div>
                        <div class="timer-highlight">ENTRADA PRÓX. VELA</div>
                        <div style="font-size:0.8rem; margin-top:10px;">Expiração: {expiracao}</div>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="sig-wait">Aguardando Confluência ({max(sc_c, sc_p)}%)</div>', unsafe_allow_html=True)

with t2:
    at_g = st.selectbox("Ativo para Gráfico", list(ATIVOS.keys()), key="at_g")
    if st.button("📊 GERAR ESTUDO TÉCNICO"):
        p, i = TIMEFRAMES[tf_sel]
        dfg = buscar_dados(ATIVOS[at_g], p, i)
        if dfg is not None:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
            fig.add_trace(go.Candlestick(x=dfg.index, open=dfg['Open'], high=dfg['High'], low=dfg['Low'], close=dfg['Close'], name="Preço"), row=1, col=1)
            fig.add_trace(go.Scatter(x=dfg.index, y=dfg['BBU'], line=dict(color='gray', width=1), name="B-Upper"), row=1, col=1)
            fig.add_trace(go.Scatter(x=dfg.index, y=dfg['BBL'], line=dict(color='gray', width=1), name="B-Lower"), row=1, col=1)
            fig.add_trace(go.Scatter(x=dfg.index, y=dfg['RSI'], line=dict(color='#aa77ff', width=2), name="RSI"), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
            fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

with t3:
    if not st.session_state.logs.empty:
        st.dataframe(st.session_state.logs, use_container_width=True)
        st.line_chart(st.session_state.logs['Saldo'])
    else:
        st.info("Nenhuma operação registrada no histórico.")

with t4:
    st.subheader("📐 Simulador de Risco")
    col_k1, col_k2 = st.columns(2)
    with col_k1:
        kf = kelly_criterion(wr if wr > 0 else 0.5, payout_pct/100)
        st.markdown(f'<div class="card"><div class="lbl">Sugestão Kelly</div><div class="val">${st.session_state.banca * kf:.2f}</div><div class="dlt">{kf*100:.1f}% da banca</div></div>', unsafe_allow_html=True)
    with col_k2:
        st.markdown("#### Martingale (Nível 3)")
        st.write(f"G1: ${val_entrada*2.2:.2f} | G2: ${val_entrada*4.8:.2f}")
