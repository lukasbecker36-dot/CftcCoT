"""Anomaly detection for CFTC COT Traders in Financial Futures data.

Flags when metrics deviate significantly from their rolling averages,
using configurable z-score thresholds and lookback windows.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# Metrics to monitor per trader type
TFF_METRICS = {
    "Open Interest": {
        "columns": ["open_interest"],
        "label": "Open Interest",
    },
    "Dealer/Intermediary": {
        "columns": ["dealer_long", "dealer_short"],
        "net": ("dealer_long", "dealer_short"),
        "label": "Dealer Net",
    },
    "Asset Manager": {
        "columns": ["asset_mgr_long", "asset_mgr_short"],
        "net": ("asset_mgr_long", "asset_mgr_short"),
        "label": "Asset Mgr Net",
    },
    "Leveraged Funds": {
        "columns": ["lev_money_long", "lev_money_short"],
        "net": ("lev_money_long", "lev_money_short"),
        "label": "Lev Funds Net",
    },
    "Other Reportable": {
        "columns": ["other_long", "other_short"],
        "net": ("other_long", "other_short"),
        "label": "Other Net",
    },
}

LOOKBACK_OPTIONS = {
    "1 Month (~4 weeks)": 4,
    "3 Months (~13 weeks)": 13,
    "6 Months (~26 weeks)": 26,
    "1 Year (~52 weeks)": 52,
}


def compute_zscore_series(series: pd.Series, window: int) -> pd.Series:
    """Compute rolling z-score for a series."""
    rolling_mean = series.rolling(window=window, min_periods=max(4, window // 2)).mean()
    rolling_std = series.rolling(window=window, min_periods=max(4, window // 2)).std()
    # Avoid division by zero
    rolling_std = rolling_std.replace(0, float("nan"))
    return (series - rolling_mean) / rolling_std


def detect_anomalies(
    df: pd.DataFrame,
    commodity: str,
    metric_key: str,
    lookback_weeks: int,
    z_threshold: float,
) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """Detect anomalies for a given commodity and metric.

    Returns:
        (commodity_data, anomalies_df, value_col_name)
    """
    metric = TFF_METRICS[metric_key]
    data = df[df["commodity"] == commodity].sort_values("date").copy()

    if data.empty:
        return data, pd.DataFrame(), ""

    # Compute the value series
    if "net" in metric:
        long_col, short_col = metric["net"]
        if long_col not in data.columns or short_col not in data.columns:
            return data, pd.DataFrame(), ""
        data["_value"] = data[long_col] - data[short_col]
        value_col = "_value"
    else:
        col = metric["columns"][0]
        if col not in data.columns:
            return data, pd.DataFrame(), ""
        value_col = col

    # Compute z-scores
    data["_zscore"] = compute_zscore_series(data[value_col], lookback_weeks)
    data["_rolling_mean"] = data[value_col].rolling(
        window=lookback_weeks, min_periods=max(4, lookback_weeks // 2)
    ).mean()
    data["_rolling_std"] = data[value_col].rolling(
        window=lookback_weeks, min_periods=max(4, lookback_weeks // 2)
    ).std()

    # Flag anomalies
    anomalies = data[data["_zscore"].abs() >= z_threshold].copy()

    return data, anomalies, value_col


def create_anomaly_chart(
    data: pd.DataFrame,
    anomalies: pd.DataFrame,
    value_col: str,
    metric_label: str,
    commodity: str,
    z_threshold: float,
) -> go.Figure:
    """Create a chart showing the metric with anomalies highlighted."""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.7, 0.3],
        subplot_titles=[f"{metric_label} — {commodity}", "Z-Score"],
    )

    # Main value line
    fig.add_trace(
        go.Scatter(
            x=data["date"],
            y=data[value_col],
            mode="lines",
            name=metric_label,
            line=dict(color="#2980b9"),
        ),
        row=1, col=1,
    )

    # Rolling mean
    fig.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["_rolling_mean"],
            mode="lines",
            name="Rolling Mean",
            line=dict(color="#95a5a6", dash="dash"),
        ),
        row=1, col=1,
    )

    # Rolling mean +/- threshold * std bands
    upper = data["_rolling_mean"] + z_threshold * data["_rolling_std"]
    lower = data["_rolling_mean"] - z_threshold * data["_rolling_std"]

    fig.add_trace(
        go.Scatter(
            x=data["date"],
            y=upper,
            mode="lines",
            name=f"+{z_threshold}σ",
            line=dict(color="#e74c3c", dash="dot", width=1),
            showlegend=True,
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=data["date"],
            y=lower,
            mode="lines",
            name=f"-{z_threshold}σ",
            line=dict(color="#e74c3c", dash="dot", width=1),
            showlegend=True,
        ),
        row=1, col=1,
    )

    # Anomaly markers
    if not anomalies.empty:
        fig.add_trace(
            go.Scatter(
                x=anomalies["date"],
                y=anomalies[value_col],
                mode="markers",
                name="Anomaly",
                marker=dict(color="#e74c3c", size=10, symbol="diamond"),
                hovertemplate=(
                    "%{x|%Y-%m-%d}<br>"
                    "Value: %{y:,.0f}<br>"
                    "Z-Score: %{customdata:.2f}"
                    "<extra>Anomaly</extra>"
                ),
                customdata=anomalies["_zscore"],
            ),
            row=1, col=1,
        )

    # Z-score subplot
    fig.add_trace(
        go.Bar(
            x=data["date"],
            y=data["_zscore"],
            name="Z-Score",
            marker_color=[
                "#e74c3c" if abs(z) >= z_threshold else "#bdc3c7"
                for z in data["_zscore"].fillna(0)
            ],
            showlegend=False,
            hovertemplate="%{x|%Y-%m-%d}<br>Z-Score: %{y:.2f}<extra></extra>",
        ),
        row=2, col=1,
    )

    # Threshold lines on z-score chart
    fig.add_hline(y=z_threshold, line_dash="dash", line_color="#e74c3c",
                  opacity=0.7, row=2, col=1)
    fig.add_hline(y=-z_threshold, line_dash="dash", line_color="#e74c3c",
                  opacity=0.7, row=2, col=1)
    fig.add_hline(y=0, line_dash="solid", line_color="#95a5a6",
                  opacity=0.3, row=2, col=1)

    fig.update_layout(
        height=650,
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="right", x=1),
    )
    fig.update_yaxes(title_text="Contracts", row=1, col=1)
    fig.update_yaxes(title_text="Z-Score", row=2, col=1)

    return fig


def build_anomaly_summary(
    df: pd.DataFrame,
    commodities: list[str],
    lookback_weeks: int,
    z_threshold: float,
) -> pd.DataFrame:
    """Scan multiple commodities and metrics, returning a summary of all anomalies."""
    rows = []
    for commodity in commodities:
        for metric_key, metric in TFF_METRICS.items():
            data, anomalies, value_col = detect_anomalies(
                df, commodity, metric_key, lookback_weeks, z_threshold
            )
            if anomalies.empty:
                continue

            # Only report the most recent anomaly per commodity/metric
            latest = anomalies.iloc[-1]
            rows.append({
                "Commodity": commodity,
                "Metric": metric["label"],
                "Date": latest["date"],
                "Value": latest[value_col],
                "Z-Score": latest["_zscore"],
                "Rolling Mean": latest["_rolling_mean"],
                "Direction": "Above" if latest["_zscore"] > 0 else "Below",
            })

    if not rows:
        return pd.DataFrame()

    summary = pd.DataFrame(rows)
    summary = summary.sort_values("Z-Score", key=abs, ascending=False)
    return summary
