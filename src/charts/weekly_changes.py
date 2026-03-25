"""Weekly changes bar chart."""

import plotly.graph_objects as go
import pandas as pd

from src.utils.constants import CHANGES


def create_weekly_changes_chart(
    df: pd.DataFrame, report_type: str, commodity: str
) -> go.Figure:
    """Create a grouped bar chart of weekly position changes by category."""
    changes = CHANGES[report_type]
    data = df[df["commodity"] == commodity].sort_values("date")

    fig = go.Figure()

    for cat_name, (long_col, short_col) in changes.items():
        if long_col in data.columns and short_col in data.columns:
            net_change = data[long_col] - data[short_col]
            colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in net_change]

            fig.add_trace(
                go.Bar(
                    x=data["date"],
                    y=net_change,
                    name=cat_name,
                    hovertemplate="%{x|%Y-%m-%d}<br>Net Change: %{y:,.0f}<extra>"
                    + cat_name
                    + "</extra>",
                )
            )

    fig.update_layout(
        title=f"Weekly Net Changes — {commodity}",
        xaxis_title="Date",
        yaxis_title="Net Change in Contracts",
        barmode="group",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        height=500,
    )

    return fig
