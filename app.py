import warnings
warnings.filterwarnings("ignore")

from dataclasses import dataclass

import feedparser
import nltk
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from nltk.sentiment import SentimentIntensityAnalyzer
from plotly.subplots import make_subplots
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.layers import Bidirectional, Dense, Dropout, LSTM
from tensorflow.keras.models import Sequential


st.set_page_config(page_title="Multi-Modal AI Trading Terminal", layout="wide")

css = """
<style>
:root {
  --bg: #080d1a;
  --card1: #0f172b;
  --card2: #121f3b;
  --txt: #e8efff;
  --muted: #9ab0d7;
  --green: #00f7a8;
  --red: #ff4d6d;
  --cyan: #6dc8ff;
}
html, body, [class*="css"] {font-family: Inter, Segoe UI, sans-serif;}
.stApp {
  color: var(--txt);
  background:
    radial-gradient(circle at 0% 0%, #1a2a50 0%, transparent 35%),
    radial-gradient(circle at 100% 100%, #11203d 0%, transparent 40%),
    var(--bg);
}
.block-container {padding-top: 1rem;}
div[data-testid="stSidebar"] {display:none;}
.panel {
  background: linear-gradient(150deg, var(--card1), var(--card2));
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 14px;
  padding: 14px;
  margin-bottom: 10px;
}
.title {font-size: 1.18rem; font-weight: 700; margin: 0 0 8px 0;}
.subtle {font-size: 0.88rem; color: var(--muted);}
.metric {font-size: 0.94rem; color: var(--muted); margin: 4px 0;}
.signal-box {
  border-radius: 18px;
  font-size: 2.1rem;
  font-weight: 900;
  text-align: center;
  letter-spacing: 0.5px;
  padding: 28px 10px;
  margin: 12px 0;
  border: 1px solid rgba(255,255,255,0.25);
}
.headline {
  border-left: 3px solid var(--cyan);
  padding-left: 8px;
  margin: 8px 0;
  font-size: 0.9rem;
  color: #dbe7ff;
}
</style>
"""
st.markdown(css, unsafe_allow_html=True)


STOCKS = {
    "Reliance": "RELIANCE.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "TCS": "TCS.NS",
    "Infosys": "INFY.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "State Bank of India": "SBIN.NS",
}
INDICES = {
    "NIFTY 50": "^NSEI",
    "BSE SENSEX": "^BSESN",
    "BANK NIFTY": "^NSEBANK",
}
INTERVAL_MAP = {"15m": "15m", "30m": "30m", "1h": "60m"}


@dataclass
class TradeOutput:
    current: float
    target: float
    move: float
    take_profit: float
    stop_loss: float
    signal_text: str


@st.cache_data(show_spinner=False, ttl=300)
def fetch_ohlcv(ticker: str, interval: str) -> pd.DataFrame:
    data = yf.download(ticker, period="60d", interval=interval, auto_adjust=True, progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [c[0] for c in data.columns]
    return data.dropna().copy()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["EMA_9"] = out["Close"].ewm(span=9, adjust=False).mean()
    out["EMA_21"] = out["Close"].ewm(span=21, adjust=False).mean()

    delta = out["Close"].diff()
    gains = pd.Series(np.where(delta > 0, delta, 0.0), index=out.index)
    losses = pd.Series(np.where(delta < 0, -delta, 0.0), index=out.index)
    avg_gain = gains.rolling(14).mean()
    avg_loss = losses.rolling(14).mean().replace(0, np.nan)
    rs = avg_gain / avg_loss
    out["RSI_14"] = 100 - (100 / (1 + rs))

    ema12 = out["Close"].ewm(span=12, adjust=False).mean()
    ema26 = out["Close"].ewm(span=26, adjust=False).mean()
    out["MACD"] = ema12 - ema26
    out["MACD_SIGNAL"] = out["MACD"].ewm(span=9, adjust=False).mean()

    m = out["Close"].rolling(20).mean()
    s = out["Close"].rolling(20).std()
    out["BB_UPPER"] = m + 2 * s
    out["BB_LOWER"] = m - 2 * s
    return out


def create_sequences(values: np.ndarray, time_step: int = 60):
    x, y = [], []
    for i in range(time_step, len(values)):
        x.append(values[i - time_step:i])
        y.append(values[i])
    return np.array(x), np.array(y)


def train_bilstm_predict(df: pd.DataFrame, epochs: int = 8, time_step: int = 60):
    close = df[["Close"]].values
    scaler = MinMaxScaler((0, 1))
    scaled = scaler.fit_transform(close)

    x_all, y_all = create_sequences(scaled, time_step=time_step)
    if len(x_all) < 30:
        return None, None

    split = max(int(len(x_all) * 0.8), 1)
    x_train, y_train = x_all[:split], y_all[:split]

    model = Sequential([
        Bidirectional(LSTM(64, return_sequences=True), input_shape=(x_all.shape[1], x_all.shape[2])),
        Dropout(0.2),
        Bidirectional(LSTM(32)),
        Dense(16, activation="relu"),
        Dense(1),
    ])
    model.compile(optimizer="adam", loss="huber")
    model.fit(x_train, y_train, epochs=epochs, batch_size=16, verbose=0)

    pred_scaled = model.predict(x_all, verbose=0)
    pred = scaler.inverse_transform(pred_scaled).flatten()
    pred_series = pd.Series(index=df.index, dtype=float)
    pred_series.iloc[time_step:] = pred

    next_seq = scaled[-time_step:].reshape(1, time_step, 1)
    next_scaled = model.predict(next_seq, verbose=0)
    next_price = float(scaler.inverse_transform(next_scaled)[0, 0])
    return next_price, pred_series


def ml_signals(df: pd.DataFrame, pred_series: pd.Series):
    temp = df.copy()
    temp["Pred"] = pred_series
    temp["prev_pred"] = temp["Pred"].shift(1)
    temp["prev_close"] = temp["Close"].shift(1)

    buys = temp[(temp["Pred"] > temp["Close"]) & (temp["prev_pred"] <= temp["prev_close"])]
    sells = temp[(temp["Pred"] < temp["Close"]) & (temp["prev_pred"] >= temp["prev_close"])]
    return buys, sells


def news_sentiment(asset_name: str):
    try:
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        nltk.download("vader_lexicon", quiet=True)

    url = f"https://news.google.com/rss/search?q={asset_name}+India+stock+market&hl=en-IN&gl=IN&ceid=IN:en"
    parsed = feedparser.parse(url)
    headlines = [e.get("title", "").strip() for e in parsed.entries[:10] if e.get("title")]
    if not headlines:
        return 0.0, "Neutral", []

    analyzer = SentimentIntensityAnalyzer()
    compounds = [analyzer.polarity_scores(h)["compound"] for h in headlines]
    score = float(np.mean(compounds))

    if score > 0.12:
        state = "Bullish Greed"
    elif score < -0.12:
        state = "Bearish Fear"
    else:
        state = "Neutral"
    return score, state, headlines[:3]


def support_resistance(df: pd.DataFrame, window: int = 10):
    lows, highs = df["Low"].values, df["High"].values
    idx = df.index
    supports, resistances = [], []

    for i in range(window, len(df) - window):
        local_low = lows[i - window:i + window + 1]
        local_high = highs[i - window:i + window + 1]
        if lows[i] == np.min(local_low):
            supports.append((idx[i], lows[i]))
        if highs[i] == np.max(local_high):
            resistances.append((idx[i], highs[i]))

    return supports[-3:], resistances[-3:]


def build_trade_output(current: float, target: float, atr_proxy: float, is_index: bool) -> TradeOutput:
    move = target - current
    bullish = move >= 0

    if bullish:
        tp = current + max(abs(move) * 1.8, atr_proxy)
        sl = current - max(abs(move) * 1.1, atr_proxy * 0.8)
    else:
        tp = current - max(abs(move) * 1.8, atr_proxy)
        sl = current + max(abs(move) * 1.1, atr_proxy * 0.8)

    if is_index:
        signal_text = "BUY CALL (CE)" if bullish else "BUY PUT (PE)"
    else:
        signal_text = "STRONG BUY" if bullish else "STRONG SELL"

    return TradeOutput(
        current=float(current),
        target=float(target),
        move=float(move),
        take_profit=float(tp),
        stop_loss=float(sl),
        signal_text=signal_text,
    )


def build_plot(df: pd.DataFrame, pred_series: pd.Series, buys: pd.DataFrame, sells: pd.DataFrame, supports, resistances, show_volume: bool):
    if show_volume:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.78, 0.22], vertical_spacing=0.03)
    else:
        fig = make_subplots(rows=1, cols=1)

    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA_9"], name="EMA 9", mode="lines", line=dict(color="#00f7a8", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA_21"], name="EMA 21", mode="lines", line=dict(color="#6dc8ff", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["BB_UPPER"], name="BB Upper", mode="lines", line=dict(color="#9aa4bf", width=1, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["BB_LOWER"], name="BB Lower", mode="lines", line=dict(color="#9aa4bf", width=1, dash="dot")), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", mode="lines", line=dict(color="#ffd166", width=1), visible="legendonly"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI_14"], name="RSI 14", mode="lines", line=dict(color="#b794f4", width=1), visible="legendonly"), row=1, col=1)

    if pred_series is not None:
        fig.add_trace(go.Scatter(x=df.index, y=pred_series, mode="lines", name="LSTM Backtest", line=dict(color="#f4d35e", width=1.5)), row=1, col=1)

    fig.add_trace(go.Scatter(x=buys.index, y=buys["Close"], mode="markers", name="ML Buy", marker=dict(symbol="triangle-up", size=11, color="#00f7a8")), row=1, col=1)
    fig.add_trace(go.Scatter(x=sells.index, y=sells["Close"], mode="markers", name="ML Sell", marker=dict(symbol="triangle-down", size=11, color="#ff4d6d")), row=1, col=1)

    for _, lvl in supports:
        fig.add_hline(y=float(lvl), line=dict(color="#00f7a8", dash="dot", width=1.4), row=1, col=1)
    for _, lvl in resistances:
        fig.add_hline(y=float(lvl), line=dict(color="#ff4d6d", dash="dot", width=1.4), row=1, col=1)

    if show_volume and "Volume" in df.columns:
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume", marker=dict(color="rgba(109,200,255,0.45)")), row=2, col=1)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_rangeslider_visible=False,
        height=760,
        margin=dict(l=10, r=10, t=20, b=10),
        legend=dict(orientation="h", y=1.01, x=0),
    )
    return fig


left, center, right = st.columns([1.5, 3.5, 1.5])

with left:
    st.markdown("<div class='panel'><div class='title'>Controls</div>", unsafe_allow_html=True)
    mode = st.radio("Asset Mode", ["Individual Stocks", "Market Indices"])
    universe = STOCKS if mode == "Individual Stocks" else INDICES
    asset_name = st.selectbox("Select Asset", list(universe.keys()))
    ticker = universe[asset_name]
    interval_label = st.selectbox("Timeframe", ["15m", "30m", "1h"], index=0)
    interval = INTERVAL_MAP[interval_label]
    epochs = st.slider("LSTM Epochs", min_value=4, max_value=20, value=8, step=2)
    run = st.button("Run AI Terminal", type="primary", use_container_width=True)
    st.markdown("<div class='subtle'>Data window: last 60 days</div></div>", unsafe_allow_html=True)

if not run:
    with center:
        st.info("Configure settings and click **Run AI Terminal** to generate AI projections, sentiment fusion, and support/resistance zones.")
    st.stop()

raw = fetch_ohlcv(ticker, interval)
if raw.empty:
    st.error("No data returned from yfinance. Please switch interval or asset.")
    st.stop()

data = add_indicators(raw)
is_index = mode == "Market Indices"
if is_index and "Volume" in data.columns:
    data = data.drop(columns=["Volume"])

data = data.dropna().copy()
if len(data) < 120:
    st.error("Not enough candles after indicator warmup. Choose a different timeframe.")
    st.stop()

next_price, pred_series = train_bilstm_predict(data, epochs=epochs, time_step=60)
if next_price is None:
    st.error("Insufficient data for 60-candle lookback training.")
    st.stop()

sent_score, sent_state, headlines = news_sentiment(asset_name)
sentiment_multiplier = 1.0 + (sent_score * 0.03)
fused_target = float(next_price * sentiment_multiplier)

buys, sells = ml_signals(data, pred_series)
supports, resistances = support_resistance(data, window=10)

current = float(data["Close"].iloc[-1])
atr_proxy = float((data["High"] - data["Low"]).rolling(14).mean().dropna().iloc[-1])
trade = build_trade_output(current, fused_target, atr_proxy, is_index=is_index)

with center:
    fig = build_plot(
        data,
        pred_series,
        buys,
        sells,
        supports,
        resistances,
        show_volume=(not is_index),
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.markdown("<div class='panel'><div class='title'>AI Insights</div>", unsafe_allow_html=True)
    is_buy = "BUY" in trade.signal_text
    color = "#00f7a8" if is_buy else "#ff4d6d"
    glow = "rgba(0,247,168,0.55)" if is_buy else "rgba(255,77,109,0.55)"
    signal_html = "<div class='signal-box' style='color:" + color + "; box-shadow: 0 0 38px " + glow + ";'>" + trade.signal_text + "</div>"
    st.markdown(signal_html, unsafe_allow_html=True)

    st.markdown(f"<div class='metric'><b>Current:</b> {trade.current:,.2f}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric'><b>AI Target:</b> {trade.target:,.2f}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric'><b>Projected Move:</b> {trade.move:,.2f}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric'><b>Take Profit:</b> {trade.take_profit:,.2f}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric'><b>Stop Loss:</b> {trade.stop_loss:,.2f}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric'><b>Sentiment State:</b> {sent_state} ({sent_score:+.2f})</div>", unsafe_allow_html=True)

    st.markdown("<div class='title' style='margin-top:12px;'>Top 3 Headlines</div>", unsafe_allow_html=True)
    if headlines:
        for h in headlines[:3]:
            st.markdown(f"<div class='headline'>{h}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='headline'>No recent headlines found.</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
