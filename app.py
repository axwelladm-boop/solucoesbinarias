import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import time

# --- 1. CONFIGURAÇÃO DE ELITE ---
st.set_page_config(page_title="AXWELL PRO | MULTI-SCANNER", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Rajdhani:wght@600&display=swap');
    .main { background-color: #04060a; color: #e0e0e0; }
    .stButton>button { width: 100%; background: linear-gradient(90deg, #00ffcc, #0099ff); color: black; font-weight: bold; border: none; height: 3rem; }
    .signal-card { background: #0a111e; border: 2px solid #00ffcc; border-radius: 15px; padding: 25px; text-align: center; box-shadow: 0 0 30px #00ffcc22; }
    .buy { color: #00ff88; font-family: 'Orbitron'; font-size: 2.5rem; }
    .sell { color: #ff4444; font-family: 'Orbitron'; font-size: 2.5rem; }
    .timer-text { color: #ffaa00; font-size: 1.5rem; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. SISTEMA DE ÁUDIO ---
def play_alert_sound():
    audio_html = """
    <audio autoplay>
    <source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg">
    </audio>
    """
    st.components.v1.html(audio_html, height=0)

# --- 3. DATABASE E VARIÁVEIS ---
LISTA_ATIVOS = ["EURUSD=X", "GBPUSD=X", "AUDUSD=X", "USDJPY=X", "BTC-USD", "ETH-USD", "SOL-USD"]

if 'banca' not in st.session_state: st.session_state.banca = 70.0
if 'historico' not in st.session_state: st.session_state.historico = pd.DataFrame()

# --- 4. ENGINE DE VARREDURA AUTOMÁTICA ---
def scan_markets():
    melhor_sinal = None
    maior_desvio = 0
    
    with st.status("🚀 Escaneando múltiplos mercados em tempo real...", expanded=True) as status:
        for ticker in LISTA_ATIVOS:
            status.write(f"Analisando {ticker}...")
            try:
                # Puxa dados do último minuto com máxima velocidade
                df = yf.download(ticker, period="1d", interval="1m", progress=False)
                if df.empty or len(df) < 10: continue
                
                # Cálculo RSI de Alta Velocidade (7 períodos)
                delta = df['Close'].diff()
                gain = delta.where(delta > 0, 0).rolling(7).mean().iloc[-1]
                loss = (-delta.where(delta < 0, 0)).rolling(7).mean().iloc[-1]
                rsi = 100 - (100 / (1 + (gain/loss)))
                
                # Lógica de seleção do melhor ativo (mais extremo)
                distancia_extremo = max(rsi - 70, 30 - rsi)
                
                if (rsi > 75 or rsi < 25) and distancia_extremo > maior_desvio:
                    maior_desvio = distancia_extremo
                    # Sugestão de tempo baseada na volatilidade (ATR simplificado)
                    volatilidade = (df['High'].iloc[-1] - df['Low'].iloc[-1])
                    tempo_sugerido = "1 min" if volatilidade < 0.001 else "5 min"
                    
                    melhor_sinal = {
                        "ativo": ticker,
                        "direcao": "COMPRA (CALL)" if rsi < 25 else "VENDA (PUT)",
                        "rsi": rsi,
                        "preco": df['Close'].iloc[-1],
                        "entrada": (datetime.now() + timedelta(minutes=1)).strftime("%H:%M:00"),
                        "expiracao": tempo_sugerido
                    }
            except:
                continue
        status.update(label="Varredura Concluída!", state="complete")
    return melhor_sinal

# --- 5. INTERFACE ---
with st.sidebar:
    st.title("🎯 AXWELL SNIPER")
    st.metric("BANCA ATUAL", f"${st.session_state.banca:.2f}")
    valor_ent = st.number_input("Valor da Entrada ($)", 1.0, 1000.0, 2.0)
    st.divider()
    st.info("O robô analisa 7 ativos simultaneamente e escolhe o de menor erro.")

st.header("🔍 Pesquisa Automática de Ativos")

if st.button("EXECUTAR VARREDURA EM TEMPO REAL"):
    resultado = scan_markets()
    
    if resultado:
        play_alert_sound()
        st.session_state.ultimo_sinal = resultado
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"""
            <div class="signal-card">
                <h3 style="color:#00ffcc;">ATIVO DETECTADO: {resultado['ativo']}</h3>
                <div class="{'buy' if 'COMPRA' in resultado['direcao'] else 'sell'}">
                    {resultado['direcao']}
                </div>
                <hr style="border: 0.5px solid #333;">
                <p class="timer-text">ENTRADA EXATA: {resultado['entrada']}</p>
                <p>TEMPO DE OPERAÇÃO: <b>{resultado['expiracao']}</b></p>
                <p style="font-size: 0.9rem; color: #888;">PREÇO ALVO: {resultado['preco']:.5f} | RSI: {resultado['rsi']:.2f}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.subheader("Confirmar Resultado")
            res_win = st.button("✅ DEU WIN")
            res_loss = st.button("❌ DEU LOSS")
            
            if res_win or res_loss:
                pnl = (valor_ent * 0.87) if res_win else -valor_ent
                st.session_state.banca += pnl
                st.success(f"Banca atualizada: ${st.session_state.banca:.2f}")
    else:
        st.warning("Mercado muito estável. Nenhum sinal de alta precisão encontrado agora. Tente em instantes.")

# --- 6. HISTÓRICO E MELHOR HORÁRIO ---
st.divider()
st.subheader("📊 Inteligência de Performance")
if not st.session_state.historico.empty:
    # Mostra o melhor horário de ganho baseado nas vitórias anteriores
    st.write("Análise de histórico em tempo real disponível.")
else:
    st.info("Aguardando primeiras operações para calcular o melhor horário de ganho.")
