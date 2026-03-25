"""Net positioning chart — Long minus Short by trader category."""

import plotly.graph_objects as go
import pandas as pd

from src.utils.constants import CATEGORIES


def create_net_positioning_chart(
    df: pd.DataFrame, report_type: str, commodity: str
) -> go.Figure:
    """Create a net positioning line chart for a given commodity.

    Shows Long - Short for each trader category over time.
    """
    categories = CATEGORIES[report_type]
    data = df[df["commodity"] == commodity].sort_values("date")

    fig = go.Figure()

    for cat_name, (long_col, short_col) in categories.items():
        if long_col in data.columns and short_col in data.columns:
            net = data[long_col] - data[short_col]
            fig.add_trace(
                go.Scatter(
                    x=data["date"],
                    y=net,
                    mode="lines",
                    name=cat_name,
                    hovertemplate="%{x|%Y-%m-%d}<br>Net: %{y:,.0f}<extra>" + cat_name + "</extra>",
                )
            )

    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    fig.update_layout(
        title=f"Net Positioning — {commodity}",
        xaxis_title="Date",
        yaxis_title="Net Contracts (Long - Short)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        height=500,
    )

    return fig
