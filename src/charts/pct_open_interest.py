"""Percentage of open interest stacked area chart."""

import plotly.graph_objects as go
import pandas as pd

from src.utils.constants import CATEGORIES


def create_pct_oi_chart(
    df: pd.DataFrame, report_type: str, commodity: str, side: str = "long"
) -> go.Figure:
    """Create a stacked area chart of each category's % of open interest.

    Args:
        side: 'long' or 'short'
    """
    categories = CATEGORIES[report_type]
    data = df[df["commodity"] == commodity].sort_values("date")

    fig = go.Figure()

    col_idx = 0 if side == "long" else 1

    for cat_name, cols in categories.items():
        col = cols[col_idx]
        pct_col = f"pct_{col.replace('_long', '').replace('_short', '')}_{side}"

        if pct_col in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data["date"],
                    y=data[pct_col],
                    mode="lines",
                    name=cat_name,
                    stackgroup="one",
                    hovertemplate="%{x|%Y-%m-%d}<br>%{y:.1f}%<extra>"
                    + cat_name
                    + "</extra>",
                )
            )

    fig.update_layout(
        title=f"% of Open Interest ({side.title()}) — {commodity}",
        xaxis_title="Date",
        yaxis_title="% of Open Interest",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        height=500,
    )

    return fig
