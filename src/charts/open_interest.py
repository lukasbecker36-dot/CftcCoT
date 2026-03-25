"""Open interest trends chart."""

import plotly.graph_objects as go
import pandas as pd

from src.utils.constants import CATEGORIES


def create_open_interest_chart(
    df: pd.DataFrame, report_type: str, commodity: str, show_breakdown: bool = True
) -> go.Figure:
    """Create an open interest chart with optional category breakdown."""
    categories = CATEGORIES[report_type]
    data = df[df["commodity"] == commodity].sort_values("date")

    fig = go.Figure()

    # Total open interest
    fig.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["open_interest"],
            mode="lines",
            name="Total Open Interest",
            line=dict(width=3, color="black"),
            hovertemplate="%{x|%Y-%m-%d}<br>OI: %{y:,.0f}<extra>Total OI</extra>",
        )
    )

    if show_breakdown:
        for cat_name, (long_col, _) in categories.items():
            if long_col in data.columns:
                fig.add_trace(
                    go.Scatter(
                        x=data["date"],
                        y=data[long_col],
                        mode="lines",
                        name=f"{cat_name} (Long)",
                        line=dict(dash="dot"),
                        hovertemplate="%{x|%Y-%m-%d}<br>Long: %{y:,.0f}<extra>"
                        + cat_name
                        + "</extra>",
                    )
                )

    fig.update_layout(
        title=f"Open Interest — {commodity}",
        xaxis_title="Date",
        yaxis_title="Contracts",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        height=500,
    )

    return fig
