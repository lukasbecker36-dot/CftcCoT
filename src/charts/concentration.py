"""Concentration ratios chart — Top 4 and Top 8 traders."""

import plotly.graph_objects as go
import pandas as pd


def create_concentration_chart(df: pd.DataFrame, commodity: str) -> go.Figure:
    """Create a line chart of gross concentration ratios (Top 4 and Top 8)."""
    data = df[df["commodity"] == commodity].sort_values("date")

    fig = go.Figure()

    traces = [
        ("conc4_long", "Top 4 Long (Gross)", "solid", "#2980b9"),
        ("conc4_short", "Top 4 Short (Gross)", "dash", "#2980b9"),
        ("conc8_long", "Top 8 Long (Gross)", "solid", "#e67e22"),
        ("conc8_short", "Top 8 Short (Gross)", "dash", "#e67e22"),
    ]

    for col, name, dash, color in traces:
        if col in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data["date"],
                    y=data[col],
                    mode="lines",
                    name=name,
                    line=dict(dash=dash, color=color),
                    hovertemplate="%{x|%Y-%m-%d}<br>%{y:.1f}%<extra>" + name + "</extra>",
                )
            )

    fig.update_layout(
        title=f"Concentration Ratios — {commodity}",
        xaxis_title="Date",
        yaxis_title="% of Open Interest",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        height=500,
    )

    return fig
