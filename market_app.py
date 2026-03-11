"""
market_app.py - Stock & Crypto Market Dashboard built with Plotly Dash.

Run:
    pip install -r requirements.txt
    python market_app.py

Then open http://127.0.0.1:8050 in your browser.
"""

import dash
from dash import dcc, html, Input, Output, State, callback, no_update
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

import market_data as md

# ── App setup ────────────────────────────────────────────────────────────────

app = dash.Dash(__name__, title="Market Dashboard")
app.config.suppress_callback_exceptions = True

DARK_BG = "#0d1117"
CARD_BG = "#161b22"
BORDER = "#30363d"
TEXT_PRIMARY = "#e6edf3"
TEXT_SECONDARY = "#8b949e"
GREEN = "#3fb950"
RED = "#f85149"
BLUE = "#58a6ff"
YELLOW = "#d29922"
PURPLE = "#bc8cff"

TIMEFRAMES = ["1D", "5D", "1M", "3M", "6M", "1Y"]

# ── Helper components ────────────────────────────────────────────────────────

def metric_card(label: str, value: str, color: str = TEXT_PRIMARY) -> html.Div:
    return html.Div([
        html.P(label, style={"color": TEXT_SECONDARY, "fontSize": "11px", "margin": "0 0 4px",
                              "textTransform": "uppercase", "letterSpacing": "0.05em"}),
        html.P(value, style={"color": color, "fontSize": "20px", "fontWeight": "700",
                              "margin": "0", "fontFamily": "monospace"}),
    ], style={
        "background": CARD_BG, "border": f"1px solid {BORDER}", "borderRadius": "8px",
        "padding": "16px 20px", "flex": "1", "minWidth": "120px",
    })


def trending_coin_card(coin: dict) -> html.Div:
    return html.Div([
        html.Span(f"#{coin.get('market_cap_rank', '?')}",
                  style={"color": TEXT_SECONDARY, "fontSize": "10px"}),
        html.P(coin.get("symbol", ""), style={"color": TEXT_PRIMARY, "fontWeight": "700",
                                               "fontSize": "15px", "margin": "4px 0 2px"}),
        html.P(coin.get("name", ""), style={"color": TEXT_SECONDARY, "fontSize": "11px", "margin": "0"}),
    ], style={
        "background": CARD_BG, "border": f"1px solid {BORDER}", "borderRadius": "8px",
        "padding": "12px 16px", "cursor": "pointer", "minWidth": "100px",
        "transition": "border-color 0.2s",
    }, id={"type": "trending-coin", "index": coin.get("coin_id", "")})


def stock_watchlist_card(stock: dict) -> html.Div:
    chg = stock.get("change_pct", 0)
    chg_color = GREEN if chg >= 0 else RED
    arrow = "▲" if chg >= 0 else "▼"
    return html.Div([
        html.P(stock.get("symbol", ""), style={"color": TEXT_PRIMARY, "fontWeight": "700",
                                                "fontSize": "15px", "margin": "0 0 4px"}),
        html.P(f"${stock.get('price', 0):,.2f}",
               style={"color": TEXT_PRIMARY, "fontSize": "13px", "margin": "0 0 4px", "fontFamily": "monospace"}),
        html.P(f"{arrow} {abs(chg):.2f}%",
               style={"color": chg_color, "fontSize": "12px", "fontWeight": "600", "margin": "0"}),
    ], style={
        "background": CARD_BG, "border": f"1px solid {BORDER}", "borderRadius": "8px",
        "padding": "12px 16px", "cursor": "pointer", "minWidth": "100px",
    })


# ── Layout ───────────────────────────────────────────────────────────────────

app.layout = html.Div([
    # Header
    html.Div([
        html.H1("Market Dashboard",
                style={"color": TEXT_PRIMARY, "fontSize": "28px", "fontWeight": "800",
                       "margin": "0", "letterSpacing": "-0.5px"}),
        html.P("Stocks & Crypto — powered by Yahoo Finance & CoinGecko",
               style={"color": TEXT_SECONDARY, "fontSize": "13px", "margin": "4px 0 0"}),
    ], style={"padding": "24px 32px 16px", "borderBottom": f"1px solid {BORDER}"}),

    # Search bar + timeframe
    html.Div([
        html.Div([
            dcc.Input(
                id="search-input",
                type="text",
                placeholder="Search ticker or coin (e.g. AAPL, bitcoin, ETH)...",
                debounce=False,
                n_submit=0,
                style={
                    "width": "100%", "padding": "10px 16px", "fontSize": "15px",
                    "background": CARD_BG, "border": f"1px solid {BORDER}", "borderRadius": "8px",
                    "color": TEXT_PRIMARY, "outline": "none", "boxSizing": "border-box",
                },
            ),
        ], style={"flex": "1", "marginRight": "12px"}),
        html.Button("Search", id="search-btn", n_clicks=0, style={
            "padding": "10px 24px", "background": BLUE, "color": "#0d1117",
            "border": "none", "borderRadius": "8px", "fontSize": "14px",
            "fontWeight": "700", "cursor": "pointer",
        }),
    ], style={"display": "flex", "alignItems": "center", "padding": "16px 32px 8px"}),

    # Timeframe selector
    html.Div([
        html.Div([
            html.Button(
                tf, id={"type": "tf-btn", "index": tf}, n_clicks=0,
                style={
                    "padding": "6px 14px", "marginRight": "8px",
                    "background": CARD_BG if tf != "1M" else BLUE,
                    "color": "#0d1117" if tf == "1M" else TEXT_SECONDARY,
                    "border": f"1px solid {BORDER}", "borderRadius": "6px",
                    "fontSize": "13px", "fontWeight": "600", "cursor": "pointer",
                }
            ) for tf in TIMEFRAMES
        ], style={"display": "flex", "alignItems": "center"}),
        dcc.Store(id="selected-timeframe", data="1M"),
    ], style={"padding": "0 32px 16px"}),

    # Loading wrapper for main content
    dcc.Loading(type="circle", color=BLUE, children=[
        # Asset header + metrics
        html.Div(id="asset-header", style={"padding": "0 32px 8px"}),

        html.Div(id="metrics-panel", style={
            "display": "flex", "gap": "12px", "flexWrap": "wrap",
            "padding": "0 32px 20px",
        }),

        # Main chart
        html.Div([
            dcc.Graph(
                id="price-chart",
                config={"displayModeBar": True, "scrollZoom": True,
                        "modeBarButtonsToRemove": ["lasso2d", "select2d"]},
                style={"height": "520px"},
            )
        ], style={"padding": "0 32px 24px"}),
    ]),

    # Trending section
    html.Div([
        html.Hr(style={"borderColor": BORDER, "margin": "0 32px 24px"}),
        html.H3("Trending & Watchlist", style={"color": TEXT_PRIMARY, "fontSize": "18px",
                                                "fontWeight": "700", "margin": "0 32px 16px"}),
        dcc.Loading(type="dot", color=BLUE, children=[
            html.Div(id="trending-section", style={"padding": "0 32px 32px"}),
        ]),
    ]),

    # Hidden interval to trigger trending load on page load
    dcc.Interval(id="init-interval", interval=500, n_intervals=0, max_intervals=1),

], style={
    "background": DARK_BG, "minHeight": "100vh",
    "fontFamily": "'Inter', 'Segoe UI', system-ui, sans-serif",
    "color": TEXT_PRIMARY,
})


# ── Callbacks ────────────────────────────────────────────────────────────────

@callback(
    Output("selected-timeframe", "data"),
    [Input({"type": "tf-btn", "index": tf}, "n_clicks") for tf in TIMEFRAMES],
    prevent_initial_call=True,
)
def update_timeframe(*args):
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update
    button_id = ctx.triggered[0]["prop_id"]
    for tf in TIMEFRAMES:
        if f'"index":"{tf}"' in button_id:
            return tf
    return no_update


@callback(
    Output("price-chart", "figure"),
    Output("metrics-panel", "children"),
    Output("asset-header", "children"),
    Input("search-btn", "n_clicks"),
    Input("search-input", "n_submit"),
    Input("selected-timeframe", "data"),
    State("search-input", "value"),
    prevent_initial_call=True,
)
def update_dashboard(n_clicks, n_submit, timeframe, query):
    if not query or not query.strip():
        return empty_chart("Enter a ticker or coin name to get started"), [], []

    asset_type, identifier = md.resolve_symbol(query.strip())

    if asset_type == "crypto":
        df = md.fetch_crypto_history(identifier, timeframe)
        info = md.fetch_crypto_info(identifier)
    else:
        df = md.fetch_stock_history(identifier, timeframe)
        info = md.fetch_stock_info(identifier)

    if df.empty or not info:
        return empty_chart(f"No data found for '{query.strip()}'"), [], []

    figure = build_chart(df, info, timeframe)
    metrics = build_metrics(info)
    header = build_header(info)
    return figure, metrics, header


def build_chart(df: pd.DataFrame, info: dict, timeframe: str) -> go.Figure:
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.03,
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        name="Price",
        increasing_line_color=GREEN,
        decreasing_line_color=RED,
        increasing_fillcolor=GREEN,
        decreasing_fillcolor=RED,
    ), row=1, col=1)

    # Moving averages
    if "MA20" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MA20"], name="MA 20",
            line={"color": YELLOW, "width": 1.5, "dash": "dot"},
            hovertemplate="MA20: $%{y:,.2f}<extra></extra>",
        ), row=1, col=1)

    if "MA50" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MA50"], name="MA 50",
            line={"color": PURPLE, "width": 1.5, "dash": "dot"},
            hovertemplate="MA50: $%{y:,.2f}<extra></extra>",
        ), row=1, col=1)

    # Volume bars
    if "Volume" in df.columns:
        vol_colors = [
            GREEN if (df["Close"].iloc[i] >= df["Open"].iloc[i]) else RED
            for i in range(len(df))
        ]
        fig.add_trace(go.Bar(
            x=df.index, y=df["Volume"], name="Volume",
            marker_color=vol_colors, opacity=0.7,
            hovertemplate="Volume: %{y:,.0f}<extra></extra>",
        ), row=2, col=1)

    name = info.get("name", "")
    symbol = info.get("symbol", "")
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=DARK_BG,
        plot_bgcolor=CARD_BG,
        title={
            "text": f"{name} ({symbol}) — {timeframe}",
            "font": {"size": 16, "color": TEXT_PRIMARY},
            "x": 0.01,
        },
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02,
                 "xanchor": "right", "x": 1, "bgcolor": "rgba(0,0,0,0)"},
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
        xaxis2={"showgrid": True, "gridcolor": BORDER},
        yaxis={"showgrid": True, "gridcolor": BORDER, "tickprefix": "$"},
        yaxis2={"showgrid": True, "gridcolor": BORDER, "title": "Vol"},
    )
    fig.update_xaxes(showgrid=True, gridcolor=BORDER)
    return fig


def build_metrics(info: dict) -> list:
    price = info.get("price", 0)
    chg = info.get("change_pct", 0)
    chg_color = GREEN if chg >= 0 else RED
    arrow = "▲" if chg >= 0 else "▼"
    return [
        metric_card("Price", f"${price:,.4f}" if price < 1 else f"${price:,.2f}"),
        metric_card("24h / Daily Change", f"{arrow} {abs(chg):.2f}%", chg_color),
        metric_card("Volume", md.format_number(info.get("volume", 0), prefix="")),
        metric_card("Market Cap", md.format_number(info.get("market_cap", 0))),
        metric_card("52w High", f"${info.get('high_52w', 0):,.2f}" if info.get('high_52w') else "N/A"),
        metric_card("52w Low", f"${info.get('low_52w', 0):,.2f}" if info.get('low_52w') else "N/A"),
    ]


def build_header(info: dict) -> list:
    asset_type = info.get("type", "")
    badge_color = BLUE if asset_type == "Stock" else YELLOW
    return [
        html.Div([
            html.H2(info.get("name", ""), style={
                "color": TEXT_PRIMARY, "fontSize": "24px", "fontWeight": "800",
                "margin": "0", "display": "inline",
            }),
            html.Span(f" {info.get('symbol', '')}",
                      style={"color": TEXT_SECONDARY, "fontSize": "18px", "marginLeft": "8px"}),
            html.Span(asset_type, style={
                "background": badge_color, "color": "#0d1117", "fontSize": "11px",
                "fontWeight": "700", "padding": "2px 10px", "borderRadius": "20px",
                "marginLeft": "12px", "verticalAlign": "middle",
                "textTransform": "uppercase", "letterSpacing": "0.05em",
            }),
            html.Span(info.get("sector", ""), style={
                "color": TEXT_SECONDARY, "fontSize": "12px", "marginLeft": "10px",
                "verticalAlign": "middle",
            }),
        ], style={"marginBottom": "12px"}),
    ]


def empty_chart(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message, xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font={"color": TEXT_SECONDARY, "size": 16},
    )
    fig.update_layout(
        template="plotly_dark", paper_bgcolor=DARK_BG, plot_bgcolor=CARD_BG,
        xaxis={"visible": False}, yaxis={"visible": False},
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
    )
    return fig


@callback(
    Output("trending-section", "children"),
    Input("init-interval", "n_intervals"),
)
def load_trending(_):
    trending_coins = md.fetch_trending_crypto()
    watchlist = md.get_watchlist_stocks()

    sections = []

    if trending_coins:
        sections.append(html.Div([
            html.H4("Trending Crypto", style={"color": TEXT_SECONDARY, "fontSize": "13px",
                                               "textTransform": "uppercase", "letterSpacing": "0.08em",
                                               "margin": "0 0 12px", "fontWeight": "600"}),
            html.Div([trending_coin_card(c) for c in trending_coins],
                     style={"display": "flex", "gap": "10px", "flexWrap": "wrap"}),
        ], style={"marginBottom": "24px"}))

    if watchlist:
        sections.append(html.Div([
            html.H4("Stock Watchlist", style={"color": TEXT_SECONDARY, "fontSize": "13px",
                                               "textTransform": "uppercase", "letterSpacing": "0.08em",
                                               "margin": "0 0 12px", "fontWeight": "600"}),
            html.Div([stock_watchlist_card(s) for s in watchlist],
                     style={"display": "flex", "gap": "10px", "flexWrap": "wrap"}),
        ]))

    return sections if sections else html.P("Could not load trending data.",
                                             style={"color": TEXT_SECONDARY})


# ── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n  Market Dashboard starting...")
    print("  Open http://127.0.0.1:8050 in your browser\n")
    app.run(debug=False, host="0.0.0.0", port=8050)
