from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    import yfinance as yf
    YF_AVAILABLE = True
except Exception:
    YF_AVAILABLE = False

st.set_page_config(
    page_title="Assay — Metals & Macro Intelligence Desk",
    page_icon="🪙",
    layout="wide",
    initial_sidebar_state="collapsed",
)

METALS = {
    "Gold": {"ticker": "GC=F", "unit": "oz", "color": "#e8b64c"},
    "Silver": {"ticker": "SI=F", "unit": "oz", "color": "#c9c9d1"},
    "Platinum": {"ticker": "PL=F", "unit": "oz", "color": "#8fd0e0"},
    "Palladium": {"ticker": "PA=F", "unit": "oz", "color": "#e08fd0"},
    "Copper": {"ticker": "HG=F", "unit": "lb", "color": "#d97a4d"},
}

# Central bank gold reserves, approx tonnes (public World Gold Council / IMF IFS data).
# Figures are periodic (updated monthly/quarterly by reporting institutions), not real-time.
RESERVES = [
    {"country": "United States", "iso3": "USA", "tonnes": 8133.5},
    {"country": "Germany", "iso3": "DEU", "tonnes": 3351.6},
    {"country": "Italy", "iso3": "ITA", "tonnes": 2451.8},
    {"country": "France", "iso3": "FRA", "tonnes": 2437.0},
    {"country": "Russia", "iso3": "RUS", "tonnes": 2335.9},
    {"country": "China", "iso3": "CHN", "tonnes": 2264.3},
    {"country": "Switzerland", "iso3": "CHE", "tonnes": 1040.0},
    {"country": "Japan", "iso3": "JPN", "tonnes": 845.9},
    {"country": "India", "iso3": "IND", "tonnes": 840.8},
    {"country": "Netherlands", "iso3": "NLD", "tonnes": 612.5},
    {"country": "Turkey", "iso3": "TUR", "tonnes": 585.0},
    {"country": "Poland", "iso3": "POL", "tonnes": 448.2},
    {"country": "Portugal", "iso3": "PRT", "tonnes": 382.6},
    {"country": "Uzbekistan", "iso3": "UZB", "tonnes": 361.6},
    {"country": "United Kingdom", "iso3": "GBR", "tonnes": 310.3},
    {"country": "Kazakhstan", "iso3": "KAZ", "tonnes": 299.4},
    {"country": "Spain", "iso3": "ESP", "tonnes": 281.6},
    {"country": "Austria", "iso3": "AUT", "tonnes": 280.0},
    {"country": "Belgium", "iso3": "BEL", "tonnes": 227.4},
    {"country": "Brazil", "iso3": "BRA", "tonnes": 129.6},
]

MINE_SITES = [
    {"name": "Muruntau (Uzbekistan)", "lat": 41.5, "lon": 64.6, "type": "Gold mine"},
    {"name": "Grasberg (Indonesia)", "lat": -4.05, "lon": 137.11, "type": "Gold/Copper mine"},
    {"name": "Escondida (Chile)", "lat": -24.27, "lon": -69.07, "type": "Copper mine"},
    {"name": "Kalgoorlie Super Pit (Australia)", "lat": -30.75, "lon": 121.47, "type": "Gold mine"},
    {"name": "Norilsk (Russia)", "lat": 69.35, "lon": 88.2, "type": "Palladium/Nickel mine"},
    {"name": "Rustenburg (South Africa)", "lat": -25.67, "lon": 27.24, "type": "Platinum mine"},
    {"name": "Cerro Rico (Bolivia)", "lat": -19.6, "lon": -65.75, "type": "Silver mine"},
]

CHOKEPOINTS = [
    {"name": "Strait of Hormuz", "lat": 26.57, "lon": 56.25},
    {"name": "Strait of Malacca", "lat": 2.5, "lon": 101.4},
    {"name": "Suez Canal", "lat": 30.4, "lon": 32.35},
    {"name": "Panama Canal", "lat": 9.08, "lon": -79.68},
    {"name": "Bab-el-Mandeb", "lat": 12.6, "lon": 43.3},
]

DEFAULT_PASSCODE = "assay2026"


def inject_theme(dark: bool) -> None:
    if dark:
        bg, panel, text, sub, accent, border = "#05070a", "#0d1117", "#e8ecf1", "#8b95a5", "#e8b64c", "#1c2430"
    else:
        bg, panel, text, sub, accent, border = "#f4f5f7", "#ffffff", "#101418", "#5b6472", "#a9720f", "#dde1e6"

    st.markdown(
        f"""
        <style>
        .stApp {{ background-color: {bg}; color: {text}; }}
        .block-container {{ padding-top: 1.5rem; max-width: 1300px; }}
        [data-testid="stMetricValue"] {{ color: {accent}; }}
        .assay-sub {{ color: {sub}; font-size: 0.85rem; }}
        .assay-title {{
            font-family: Georgia, 'Times New Roman', serif;
            letter-spacing: 4px;
            font-size: 2rem;
            color: {accent};
        }}
        a {{ color: {accent} !important; }}
        @media (max-width: 640px) {{
            .assay-title {{ font-size: 1.3rem; letter-spacing: 2px; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def require_passcode() -> bool:
    try:
        configured = st.secrets.get("APP_PASSCODE", DEFAULT_PASSCODE)
    except Exception:
        configured = DEFAULT_PASSCODE

    if not configured:
        return True
    if st.session_state.get("authed"):
        return True

    st.markdown("<div class='assay-title'>ASSAY</div>", unsafe_allow_html=True)
    st.caption("Metals & Macro Intelligence Desk — enter passcode to continue")
    code_input = st.text_input("Passcode", type="password")
    if st.button("Enter"):
        if code_input == configured:
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("Incorrect passcode.")
    st.info(f"Demo passcode is `{configured}` unless the app owner sets an APP_PASSCODE secret in Streamlit Cloud.")
    return False


@st.cache_data(ttl=60, show_spinner=False)
def fetch_live_prices():
    rows = []
    if YF_AVAILABLE:
        try:
            for name, meta in METALS.items():
                hist = yf.Ticker(meta["ticker"]).history(period="5d", interval="1d")
                if hist.empty:
                    raise ValueError("no data for " + name)
                last_close = float(hist["Close"].iloc[-1])
                prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else last_close
                change_pct = ((last_close - prev_close) / prev_close * 100) if prev_close else 0.0
                rows.append({
                    "metal": name, "price": last_close,
                    "change_pct": change_pct, "unit": meta["unit"],
                    "source": "Yahoo Finance (live)",
                })
        except Exception:
            rows = []
    if not rows:
        import random
        base = {"Gold": 2400, "Silver": 28.5, "Platinum": 950, "Palladium": 1000, "Copper": 4.2}
        for name, meta in METALS.items():
            rows.append({
                "metal": name, "price": base[name] * (1 + random.uniform(-0.01, 0.01)),
                "change_pct": random.uniform(-1.5, 1.5), "unit": meta["unit"],
                "source": "Simulated (live feed unavailable)",
            })
    return rows


@st.cache_data(ttl=900, show_spinner=False)
def fetch_history(ticker: str, period: str = "6mo"):
    if YF_AVAILABLE:
        try:
            hist = yf.Ticker(ticker).history(period=period)
            if not hist.empty:
                return hist.reset_index()
        except Exception:
            pass
    return pd.DataFrame()


@st.cache_data(ttl=600, show_spinner=False)
def fetch_news():
    headlines = []
    if YF_AVAILABLE:
        try:
            for meta in list(METALS.values())[:2]:
                t = yf.Ticker(meta["ticker"])
                for item in (t.news or [])[:5]:
                    content = item.get("content", {}) if isinstance(item, dict) else {}
                    title = item.get("title") or content.get("title") or "Untitled"
                    publisher = (
                        item.get("publisher")
                        or (content.get("provider") or {}).get("displayName")
                        or ""
                    )
                    link = item.get("link") or (content.get("canonicalUrl") or {}).get("url") or "#"
                    headlines.append({"title": title, "publisher": publisher, "link": link})
        except Exception:
            pass
    if not headlines:
        headlines = [
            {"title": "Live news feed unavailable — showing placeholder", "publisher": "Assay", "link": "#"},
        ]
    seen = set()
    unique = []
    for h in headlines:
        if h["title"] not in seen:
            seen.add(h["title"])
            unique.append(h)
    return unique[:10]


def render_header(dark: bool):
    left, right = st.columns([4, 1])
    with left:
        st.markdown("<div class='assay-title'>ASSAY</div>", unsafe_allow_html=True)
        st.markdown("<div class='assay-sub'>Metals &amp; Macro Intelligence Desk — live pro edition</div>", unsafe_allow_html=True)
    with right:
        st.toggle("Dark mode", value=dark, key="dark_mode")
    c1, c2 = st.columns([5, 1])
    with c1:
        st.caption(f"Last refreshed {datetime.utcnow().strftime('%H:%M:%S UTC')} · prices auto-refresh every 60s")
    with c2:
        if st.button("Refresh now"):
            st.cache_data.clear()
            st.rerun()


def render_ticker(prices):
    cols = st.columns(len(prices))
    for col, row in zip(cols, prices):
        with col:
            st.metric(
                label=f"{row['metal']} · {row['unit']}",
                value=f"${row['price']:,.2f}",
                delta=f"{row['change_pct']:+.2f}%",
            )
    sources = {row["source"] for row in prices}
    st.caption(" · ".join(sources))


def render_history_chart():
    st.subheader("Historical prices")
    metal_name = st.selectbox("Metal", list(METALS.keys()), key="hist_metal")
    period = st.select_slider("Range", options=["1mo", "3mo", "6mo", "1y", "2y"], value="6mo")
    hist = fetch_history(METALS[metal_name]["ticker"], period)
    if hist.empty:
        st.warning("Historical data is unavailable right now — try again shortly.")
        return
    fig = go.Figure(data=[go.Scatter(x=hist["Date"], y=hist["Close"], mode="lines", line=dict(color=METALS[metal_name]["color"], width=2))])
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)


def render_reserves_map(dark: bool):
    st.subheader("Global reserves & trade network")
    st.caption("Neon-lit view of central bank gold reserves, mine sites, and shipping chokepoints.")

    layers = st.multiselect(
        "Map layers",
        ["Mines", "Chokepoints", "Trade routes"],
        default=["Mines", "Chokepoints", "Trade routes"],
    )

    df = pd.DataFrame(RESERVES)
    neon_scale = [
        [0.0, "#050b18"],
        [0.25, "#0b3d5c"],
        [0.5, "#00b4d8"],
        [0.75, "#5ee6a8"],
        [1.0, "#e8b64c"],
    ]

    fig = px.choropleth(df, locations="iso3", color="tonnes", hover_name="country", color_continuous_scale=neon_scale, labels={"tonnes": "Tonnes"})
    fig.update_layout(
        height=460, margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        geo=dict(
            bgcolor="rgba(0,0,0,0)",
            landcolor="#0a1a2f",
            showocean=True, oceancolor="#020611",
            showcountries=True, countrycolor="#123049",
            showcoastlines=True, coastlinecolor="#00eaff",
            showframe=False,
        ),
        legend=dict(font=dict(color="#c9c9d1"), bgcolor="rgba(0,0,0,0)"),
    )

    mines_df = pd.DataFrame(MINE_SITES)
    choke_df = pd.DataFrame(CHOKEPOINTS)

    if "Trade routes" in layers:
        for _, mine in mines_df.iterrows():
            dists = (choke_df["lat"] - mine["lat"]) ** 2 + (choke_df["lon"] - mine["lon"]) ** 2
            nearest = choke_df.iloc[dists.idxmin()]
            fig.add_scattergeo(
                lat=[mine["lat"], nearest["lat"]], lon=[mine["lon"], nearest["lon"]],
                mode="lines", line=dict(width=1, color="rgba(0,234,255,0.35)", dash="dot"),
                showlegend=False, hoverinfo="skip",
            )

    if "Mines" in layers:
        fig.add_scattergeo(
            lat=mines_df["lat"], lon=mines_df["lon"], mode="markers",
            marker=dict(size=16, color="rgba(94,230,168,0.25)"),
            showlegend=False, hoverinfo="skip",
        )
        fig.add_scattergeo(
            lat=mines_df["lat"], lon=mines_df["lon"],
            text=mines_df["name"] + " — " + mines_df["type"], mode="markers",
            marker=dict(size=7, color="#5ee6a8", symbol="diamond"),
            name="Mines",
        )

    if "Chokepoints" in layers:
        fig.add_scattergeo(
            lat=choke_df["lat"], lon=choke_df["lon"], mode="markers",
            marker=dict(size=18, color="rgba(255,107,107,0.25)"),
            showlegend=False, hoverinfo="skip",
        )
        fig.add_scattergeo(
            lat=choke_df["lat"], lon=choke_df["lon"],
            text=choke_df["name"], mode="markers",
            marker=dict(size=9, color="#ff6b6b", symbol="x"),
            name="Shipping chokepoints",
        )

    st.plotly_chart(fig, use_container_width=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("Reserve nations", len(df))
    m2.metric("Mine sites", len(MINE_SITES))
    m3.metric("Chokepoints", len(CHOKEPOINTS))

    with st.expander("Reserves ledger"):
        st.dataframe(df[["country", "tonnes"]].sort_values("tonnes", ascending=False), use_container_width=True, hide_index=True)
    st.caption("Reserve tonnages reflect the latest publicly reported IMF/World Gold Council figures and update periodically, not in real time. Trade route lines are illustrative nearest-chokepoint links, not actual shipping data.")
def render_news():
    st.subheader("Intel feed")
    for item in fetch_news():
        st.markdown(f"- [{item['title']}]({item['link']}) — *{item['publisher']}*")


def render_portfolio(prices):
    st.subheader("Portfolio / watchlist")
    price_lookup = {row["metal"]: row["price"] for row in prices}

    if "holdings" not in st.session_state:
        st.session_state["holdings"] = pd.DataFrame({"metal": ["Gold"], "quantity": [1.0]})

    edited = st.data_editor(
        st.session_state["holdings"],
        num_rows="dynamic",
        column_config={
            "metal": st.column_config.SelectboxColumn("Metal", options=list(METALS.keys())),
            "quantity": st.column_config.NumberColumn("Quantity (oz/lb)", min_value=0.0, step=0.1),
        },
        use_container_width=True,
        key="holdings_editor",
    )
    st.session_state["holdings"] = edited

    if not edited.empty:
        valued = edited.copy()
        valued["quantity"] = pd.to_numeric(valued["quantity"], errors="coerce").fillna(0.0)
        valued["price"] = valued["metal"].map(price_lookup).fillna(0.0)
        valued["value"] = valued["quantity"] * valued["price"]
        total = valued["value"].sum()

        col1, col2 = st.columns([2, 1])
        with col1:
            non_zero = valued[valued["value"] > 0]
            if not non_zero.empty:
                fig = px.pie(non_zero, names="metal", values="value", hole=0.5)
                fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), showlegend=True)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.caption("Add quantities to see the allocation chart.")
        with col2:
            st.metric("Total portfolio value", f"${total:,.2f}")

        csv = valued.to_csv(index=False).encode("utf-8")
        st.download_button("Download holdings as CSV", data=csv, file_name="assay_portfolio.csv", mime="text/csv")


def render_alerts(prices):
    st.subheader("Price alerts")
    if "alerts" not in st.session_state:
        st.session_state["alerts"] = {}

    with st.form("alert_form", clear_on_submit=False):
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            metal_name = st.selectbox("Metal", list(METALS.keys()), key="alert_metal")
        with c2:
            threshold = st.number_input("Alert when price crosses", min_value=0.0, step=0.5)
        with c3:
            st.write("")
            submitted = st.form_submit_button("Set alert")
        if submitted and threshold > 0:
            st.session_state["alerts"][metal_name] = threshold

    if st.session_state["alerts"]:
        price_lookup = {row["metal"]: row["price"] for row in prices}
        for metal_name, threshold in list(st.session_state["alerts"].items()):
            current = price_lookup.get(metal_name)
            if current is None:
                continue
            if current >= threshold:
                st.success(f"{metal_name} is at ${current:,.2f}, at or above your ${threshold:,.2f} alert.")
            else:
                st.caption(f"{metal_name}: ${current:,.2f} (alert at ${threshold:,.2f})")
    else:
        st.caption("No alerts set yet.")


def main():
    dark = st.session_state.get("dark_mode", True)
    inject_theme(dark)

    if not require_passcode():
        return

    render_header(dark)
    prices = fetch_live_prices()
    render_ticker(prices)

    st.divider()
    tab_overview, tab_history, tab_portfolio, tab_alerts = st.tabs(
        ["Map & Intel", "Historical charts", "Portfolio", "Alerts"]
    )
    with tab_overview:
        render_reserves_map(dark)
        render_news()
    with tab_history:
        render_history_chart()
    with tab_portfolio:
        render_portfolio(prices)
    with tab_alerts:
        render_alerts(prices)

    st.divider()
    st.caption(
        "All commodity prices are sourced live from Yahoo Finance futures data when available; "
        "reserve figures and mine/chokepoint locations are curated reference data. "
        "This dashboard is for informational/demo purposes only and is not investment advice."
    )


if __name__ == "__main__":
    main()
    
