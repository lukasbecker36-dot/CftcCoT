"""CFTC Commitment of Traders Dashboard — Streamlit App."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from src.data.cache import load_initial_data, refresh_current_year, get_last_update
from src.charts.net_positioning import create_net_positioning_chart
from src.charts.open_interest import create_open_interest_chart
from src.charts.weekly_changes import create_weekly_changes_chart
from src.charts.concentration import create_concentration_chart
from src.charts.pct_open_interest import create_pct_oi_chart
from src.utils.constants import REPORT_TYPES, CATEGORIES
from src.utils.categories import build_category_map

st.set_page_config(
    page_title="CFTC COT Dashboard",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)


@st.cache_data(ttl=timedelta(days=7), show_spinner=False)
def get_data() -> pd.DataFrame:
    """Load data with caching."""
    return load_initial_data()


def main():
    st.title("CFTC Commitment of Traders Dashboard")
    st.caption("Disaggregated & Traders in Financial Futures — Futures Only")

    # --- Sidebar ---
    with st.sidebar:
        st.header("Settings")

        # Report type selector
        report_type_key = st.selectbox(
            "Report Type",
            options=list(REPORT_TYPES.keys()),
            format_func=lambda x: REPORT_TYPES[x],
        )

        # Refresh button
        if st.button("Refresh Data (Current Year)"):
            with st.spinner("Refreshing..."):
                df = refresh_current_year()
                st.cache_data.clear()
            st.success("Data refreshed!")
            st.rerun()

        # Last updated
        last_update = get_last_update()
        if last_update:
            st.caption(f"Last updated: {last_update[:19]}")
        else:
            st.caption("No cached data yet")

    # --- Load data ---
    with st.spinner("Loading COT data (first run downloads from CFTC)..."):
        df = get_data()

    if df.empty:
        st.error(
            "Failed to load data. Check your internet connection and try refreshing."
        )
        return

    # Filter by report type
    report_df = df[df["report_type"] == report_type_key].copy()

    if report_df.empty:
        st.warning(f"No data available for {REPORT_TYPES[report_type_key]}.")
        return

    # --- Sidebar: Commodity selector (two-level) ---
    # Only include contracts that have data in the last 12 months
    cutoff_date = report_df["date"].max() - timedelta(days=365)
    active_commodities = (
        report_df[report_df["date"] >= cutoff_date]["commodity"].unique()
    )
    all_commodities = sorted(active_commodities)
    category_map = build_category_map(all_commodities)
    category_names = sorted(category_map.keys())

    with st.sidebar:
        asset_class = st.selectbox(
            "Asset Class",
            options=category_names,
            index=0,
        )

        contracts_in_class = category_map.get(asset_class, [])
        commodity = st.selectbox(
            "Futures Contract",
            options=contracts_in_class,
            index=0,
        )

        # Date range
        min_date = report_df["date"].min().date()
        max_date = report_df["date"].max().date()
        default_start = max(min_date, max_date - timedelta(days=365))

        date_range = st.date_input(
            "Date Range",
            value=(default_start, max_date),
            min_value=min_date,
            max_value=max_date,
        )

    # Apply date filter
    if len(date_range) == 2:
        start_date, end_date = date_range
        filtered = report_df[
            (report_df["date"].dt.date >= start_date)
            & (report_df["date"].dt.date <= end_date)
        ]
    else:
        filtered = report_df

    if filtered.empty:
        st.warning("No data for the selected filters.")
        return

    # --- Summary metrics ---
    commodity_data = filtered[filtered["commodity"] == commodity]
    if commodity_data.empty:
        st.warning(f"No data for {commodity} in the selected date range.")
        return
    latest = commodity_data.sort_values("date").iloc[-1]
    categories = CATEGORIES[report_type_key]

    cols = st.columns(len(categories))
    for i, (cat_name, (long_col, short_col)) in enumerate(categories.items()):
        with cols[i]:
            if long_col in latest.index and short_col in latest.index:
                net = latest[long_col] - latest[short_col]
                direction = "Long" if net >= 0 else "Short"
                st.metric(
                    label=cat_name,
                    value=f"{abs(net):,.0f} Net {direction}",
                )

    st.divider()

    # --- Chart tabs ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Net Positioning",
        "Open Interest",
        "Weekly Changes",
        "Concentration Ratios",
        "% of Open Interest",
    ])

    with tab1:
        fig = create_net_positioning_chart(filtered, report_type_key, commodity)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        show_breakdown = st.checkbox("Show category breakdown", value=True, key="oi_breakdown")
        fig = create_open_interest_chart(
            filtered, report_type_key, commodity, show_breakdown
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        fig = create_weekly_changes_chart(filtered, report_type_key, commodity)
        st.plotly_chart(fig, use_container_width=True)

    with tab4:
        fig = create_concentration_chart(filtered, commodity)
        st.plotly_chart(fig, use_container_width=True)

    with tab5:
        side = st.radio(
            "Position Side",
            ["long", "short"],
            horizontal=True,
            key="pct_side",
        )
        fig = create_pct_oi_chart(filtered, report_type_key, commodity, side)
        st.plotly_chart(fig, use_container_width=True)

    # --- Commodity comparison ---
    st.divider()
    with st.expander("Cross-Commodity Comparison"):
        compare_class = st.selectbox(
            "Asset Class",
            options=category_names,
            index=category_names.index(asset_class) if asset_class in category_names else 0,
            key="compare_asset_class",
        )
        compare_contracts = category_map.get(compare_class, [])
        compare_commodities = st.multiselect(
            "Select futures contracts to compare",
            options=compare_contracts,
            default=[compare_contracts[0]] if compare_contracts else [],
            max_selections=5,
        )

        if compare_commodities:
            compare_metric = st.selectbox(
                "Metric",
                options=list(categories.keys()),
                key="compare_metric",
            )
            long_col, short_col = categories[compare_metric]

            import plotly.graph_objects as go
            fig = go.Figure()
            for comm in compare_commodities:
                comm_data = filtered[filtered["commodity"] == comm].sort_values("date")
                if long_col in comm_data.columns and short_col in comm_data.columns:
                    net = comm_data[long_col] - comm_data[short_col]
                    fig.add_trace(
                        go.Scatter(
                            x=comm_data["date"],
                            y=net,
                            mode="lines",
                            name=comm,
                        )
                    )

            fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
            fig.update_layout(
                title=f"Net {compare_metric} — Comparison",
                xaxis_title="Date",
                yaxis_title="Net Contracts",
                hovermode="x unified",
                template="plotly_white",
                height=500,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig, use_container_width=True)

    # --- Raw data view ---
    with st.expander("Raw Data"):
        display_cols = ["date", "commodity", "open_interest"] + [
            col
            for cat_cols in categories.values()
            for col in cat_cols
            if col in filtered.columns
        ]
        st.dataframe(
            filtered[filtered["commodity"] == commodity][display_cols]
            .sort_values("date", ascending=False)
            .reset_index(drop=True),
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
