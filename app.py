import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# --- 1. CONFIGURAÇÃO OBRIGATÓRIA (PRIMEIRA LINHA) ---
st.set_page_config(page_title="AXWELL PRO | Sniper Quant", layout="wide")

# --- 2. ESTILIZAÇÃO E COMPONENTE DE ÁUDIO ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Rajdhani:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Rajdhani', sans-serif; background-color: #05080d; color: #e0e0e0; }
    .main { background-color: #05080d; }
    .stMetric { background: #0d1520; border: 1px solid #00ffcc33; padding: 15px; border-radius: 10px; }
    .signal-box { padding: 25px; border-radius: 15px; text-align: center; margin: 20px 0; border: 2px solid #00ffcc; background: #0a111e; box-shadow: 0 0 20px #00ffcc22; }
    .buy-text { color: #00ff88; font-family: 'Orbitron'; font-size: 2.2rem; text-shadow: 0 0 10px #00ff88; }
    .sell-text { color: #ff4444; font-family: 'Orbitron'; font-size: 2.2rem; text-shadow: 0 0 10px #ff4444; }
</style>
""", unsafe_allow_html=True)

def play_alert():
    # Som de alerta "Bip" futurista
    audio_html = """
    <audio autoplay>
    <source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg">
    </audio>
    """
    st.components.v1.html(audio_html, height=0)

# --- 3. INICIALIZAÇÃO DE DADOS ---
if 'historico' not in st.session_state:
    st.session_state.historico = pd.DataFrame(columns=['Hora', 'Ativo', 'Direção', 'Resultado', 'Valor', 'Minuto'])
if 'banca' not in st.session_state:
    st.session_state.banca = 70.0

# --- 4. ENGINE DE ANÁLISE SNIPER (OTIMIZADA) ---
def get_sniper_signal(ticker):
    try:
        # Download apenas do necessário para velocidade máxima
        df = yf.download(ticker, period="1d", interval="1m", progress=False)
        if df.empty or len(df) < 20: return None
        
        # Garantir que os preços são floats puros (Corrige o erro TypeError)
        close_prices = df['Close'].values.flatten().astype(float)
        last_price = float(close_prices[-1])
        
        # RSI de 7 períodos para agressividade
        delta = pd.Series(close_prices).diff()
        gain = delta.where(delta > 0, 0).rolling(7).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(7).mean()
        rsi = 100 - (100 / (1 + (gain/loss).iloc[-1]))
        
        # Tempo de entrada: Próximo minuto cheio
        entrada_hora = (datetime.now() + timedelta(minutes=1)).replace(second=0, microsecond=0)
        
        return {"price": last_price, "rsi": rsi, "time": entrada_hora}
    except:
        return None

# --- 5. INTERFACE LATERAL ---
with st.sidebar:
    st.markdown("<h2 style='color:#00ffcc;'>⚙️ CONFIGURAÇÃO</h2>", unsafe_allow_html=True)
    ativo_bruto = st.selectbox("Ativo", ["EURUSD=X", "GBPUSD=X", "BTC-USD", "ETH-USD"])
    expiracao = st.selectbox("Tempo de Expiração", ["30 segundos", "1 minuto", "2 minutos", "5 minutos", "30 minutos"])
    valor_entrada = st.number_input("Valor da Entrada ($)", 1.0, 5000.0, 2.0)
    
    st.divider()
    st.metric("BANCA ATUAL", f"${st.session_state.banca:.2f}")

# --- 6. PAINEL PRINCIPAL ---
tab1, tab2, tab3 = st.tabs(["🎯 SNIPER LIVE", "📊 PERFORMANCE", "🛡️ GESTÃO"])

with tab1:
    col_btn, col_info = st.columns([1, 2])
    with col_btn:
        if st.button("🔍 ANALISAR AGORA", use_container_width=True):
            res = get_sniper_signal(ativo_bruto)
            if res:
                st.session_state.last_res = res
            else:
                st.error("Erro na leitura do mercado. Tente novamente.")

    if 'last_res' in st.session_state:
        res = st.session_state.last_res
        c1, c2 = st.columns(2)
        c1.metric("Preço Atual", f"{res['price']:.5f}")
        c2.metric("Força RSI", f"{res['rsi']:.2f}")

        # LÓGICA DE SINAL (SOBRECOMPRA/SOBREVENDA)
        if res['rsi'] < 30 or res['rsi'] > 70:
            play_alert() # Notificação Sonora
            tipo = "COMPRA (CALL)" if res['rsi'] < 30 else "VENDA (PUT)"
            cor_classe = "buy-text" if res['rsi'] < 30 else "sell-text"
            
            st.markdown(f"""
            <div class="signal-box">
                <div class="{cor_classe}">{tipo}</div>
                <p style='font-size:1.2rem;'>ENTRADA EXATA ÀS: <b style='color:#fff;'>{res['time'].strftime('%H:%M:%S')}</b></p>
                <p>EXPIRAÇÃO: <b>{expiracao}</b></p>
                <p style='color:#ffaa00;'>⚠️ ALERTA: OPERAÇÃO EM 1 MINUTO! PREPARE-SE.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Aguardando zona de exaustão (RSI fora de 30-70).")

    st.divider()
    st.subheader("📝 REGISTRAR RESULTADO")
    cr1, cr2, cr3 = st.columns(3)
    resultado = cr1.selectbox("Resultado", ["WIN ✅", "LOSS ❌"])
    if cr2.button("SALVAR OPERAÇÃO", use_container_width=True):
        lucro = (valor_entrada * 0.87) if "WIN" in resultado else -valor_entrada
        st.session_state.banca += lucro
        
        novo_dado = {
            'Hora': datetime.now().strftime("%H:%M"),
            'Ativo': ativo_bruto,
            'Direção': "SINAL",
            'Resultado': resultado,
            'Valor': lucro,
            'Minuto': datetime.now().minute
        }
        st.session_state.historico = pd.concat([st.session_state.historico, pd.DataFrame([novo_dado])], ignore_index=True)
        st.toast("Histórico atualizado!", icon="📊")

with tab2:
    if not st.session_state.historico.empty:
        st.subheader("🔥 Melhor Horário de Lucro")
        df_win = st.session_state.historico[st.session_state.historico['Resultado'].str.contains("WIN")]
        
        if not df_win.empty:
            stats = df_win['Hora'].value_counts()
            st.bar_chart(stats)
            st.success(f"Seu melhor horário de entrada detectado: **{stats.idxmax()}**")
        
        st.dataframe(st.session_state.historico, use_container_width=True)
    else:
        st.info("Realize operações para ver sua performance.")

with tab3:
    st.subheader("Gestão Sniper")
    st.write(f"Sua banca inicial era $70.00. Seu saldo atual é **${st.session_state.banca:.2f}**")
    progresso = (st.session_state.banca / 70.0) - 1
    st.metric("Crescimento Total", f"{progresso*100:.2f}%")
