"""Constants and configuration for CFTC COT data."""

from datetime import datetime

# Years to download
START_YEAR = 2022
CURRENT_YEAR = datetime.now().year
YEARS = list(range(START_YEAR, CURRENT_YEAR + 1))

# CFTC download URL templates (futures only)
URLS = {
    "disaggregated": "https://www.cftc.gov/files/dea/history/fut_disagg_txt_{year}.zip",
    "tff": "https://www.cftc.gov/files/dea/history/fut_fin_txt_{year}.zip",
}

REPORT_TYPES = {
    "disaggregated": "Disaggregated",
    "tff": "Traders in Financial Futures",
}

# Column mappings per report type — standardized names
DISAGG_COLUMNS = {
    "Market_and_Exchange_Names": "commodity",
    "CFTC_Contract_Market_Code": "cftc_code",
    "As_of_Date_In_Form_YYMMDD": "date",
    "Report_Date_as_YYYY-MM-DD": "report_date",
    "Open_Interest_All": "open_interest",
    "Prod_Merc_Positions_Long_All": "prod_merc_long",
    "Prod_Merc_Positions_Short_All": "prod_merc_short",
    "Swap_Positions_Long_All": "swap_long",
    "Swap__Positions_Short_All": "swap_short",
    "Swap_Positions_Spread_All": "swap_spread",
    "M_Money_Positions_Long_All": "managed_money_long",
    "M_Money_Positions_Short_All": "managed_money_short",
    "M_Money_Positions_Spread_All": "managed_money_spread",
    "Other_Rept_Positions_Long_All": "other_long",
    "Other_Rept_Positions_Short_All": "other_short",
    "Other_Rept_Positions_Spread_All": "other_spread",
    "NonRept_Positions_Long_All": "nonreportable_long",
    "NonRept_Positions_Short_All": "nonreportable_short",
    "Change_in_Open_Interest_All": "change_oi",
    "Change_in_Prod_Merc_Long_All": "change_prod_merc_long",
    "Change_in_Prod_Merc_Short_All": "change_prod_merc_short",
    "Change_in_Swap_Long_All": "change_swap_long",
    "Change_in_Swap_Short_All": "change_swap_short",
    "Change_in_M_Money_Long_All": "change_managed_money_long",
    "Change_in_M_Money_Short_All": "change_managed_money_short",
    "Change_in_Other_Rept_Long_All": "change_other_long",
    "Change_in_Other_Rept_Short_All": "change_other_short",
    "Pct_of_OI_Prod_Merc_Long_All": "pct_prod_merc_long",
    "Pct_of_OI_Prod_Merc_Short_All": "pct_prod_merc_short",
    "Pct_of_OI_Swap_Long_All": "pct_swap_long",
    "Pct_of_OI_Swap_Short_All": "pct_swap_short",
    "Pct_of_OI_Swap_Spread_All": "pct_swap_spread",
    "Pct_of_OI_M_Money_Long_All": "pct_managed_money_long",
    "Pct_of_OI_M_Money_Short_All": "pct_managed_money_short",
    "Pct_of_OI_M_Money_Spread_All": "pct_managed_money_spread",
    "Pct_of_OI_Other_Rept_Long_All": "pct_other_long",
    "Pct_of_OI_Other_Rept_Short_All": "pct_other_short",
    "Pct_of_OI_Other_Rept_Spread_All": "pct_other_spread",
    "Pct_of_OI_NonRept_Long_All": "pct_nonreportable_long",
    "Pct_of_OI_NonRept_Short_All": "pct_nonreportable_short",
    "Conc_Gross_LE_4_TDR_Long_All": "conc4_long",
    "Conc_Gross_LE_4_TDR_Short_All": "conc4_short",
    "Conc_Gross_LE_8_TDR_Long_All": "conc8_long",
    "Conc_Gross_LE_8_TDR_Short_All": "conc8_short",
    "Conc_Net_LE_4_TDR_Long_All": "conc4_net_long",
    "Conc_Net_LE_4_TDR_Short_All": "conc4_net_short",
    "Conc_Net_LE_8_TDR_Long_All": "conc8_net_long",
    "Conc_Net_LE_8_TDR_Short_All": "conc8_net_short",
}

TFF_COLUMNS = {
    "Market_and_Exchange_Names": "commodity",
    "CFTC_Contract_Market_Code": "cftc_code",
    "As_of_Date_In_Form_YYMMDD": "date",
    "Report_Date_as_YYYY-MM-DD": "report_date",
    "Open_Interest_All": "open_interest",
    "Dealer_Positions_Long_All": "dealer_long",
    "Dealer_Positions_Short_All": "dealer_short",
    "Dealer_Positions_Spread_All": "dealer_spread",
    "Asset_Mgr_Positions_Long_All": "asset_mgr_long",
    "Asset_Mgr_Positions_Short_All": "asset_mgr_short",
    "Asset_Mgr_Positions_Spread_All": "asset_mgr_spread",
    "Lev_Money_Positions_Long_All": "lev_money_long",
    "Lev_Money_Positions_Short_All": "lev_money_short",
    "Lev_Money_Positions_Spread_All": "lev_money_spread",
    "Other_Rept_Positions_Long_All": "other_long",
    "Other_Rept_Positions_Short_All": "other_short",
    "Other_Rept_Positions_Spread_All": "other_spread",
    "NonRept_Positions_Long_All": "nonreportable_long",
    "NonRept_Positions_Short_All": "nonreportable_short",
    "Change_in_Open_Interest_All": "change_oi",
    "Change_in_Dealer_Long_All": "change_dealer_long",
    "Change_in_Dealer_Short_All": "change_dealer_short",
    "Change_in_Asset_Mgr_Long_All": "change_asset_mgr_long",
    "Change_in_Asset_Mgr_Short_All": "change_asset_mgr_short",
    "Change_in_Lev_Money_Long_All": "change_lev_money_long",
    "Change_in_Lev_Money_Short_All": "change_lev_money_short",
    "Change_in_Other_Rept_Long_All": "change_other_long",
    "Change_in_Other_Rept_Short_All": "change_other_short",
    "Pct_of_OI_Dealer_Long_All": "pct_dealer_long",
    "Pct_of_OI_Dealer_Short_All": "pct_dealer_short",
    "Pct_of_OI_Dealer_Spread_All": "pct_dealer_spread",
    "Pct_of_OI_Asset_Mgr_Long_All": "pct_asset_mgr_long",
    "Pct_of_OI_Asset_Mgr_Short_All": "pct_asset_mgr_short",
    "Pct_of_OI_Asset_Mgr_Spread_All": "pct_asset_mgr_spread",
    "Pct_of_OI_Lev_Money_Long_All": "pct_lev_money_long",
    "Pct_of_OI_Lev_Money_Short_All": "pct_lev_money_short",
    "Pct_of_OI_Lev_Money_Spread_All": "pct_lev_money_spread",
    "Pct_of_OI_Other_Rept_Long_All": "pct_other_long",
    "Pct_of_OI_Other_Rept_Short_All": "pct_other_short",
    "Pct_of_OI_Other_Rept_Spread_All": "pct_other_spread",
    "Pct_of_OI_NonRept_Long_All": "pct_nonreportable_long",
    "Pct_of_OI_NonRept_Short_All": "pct_nonreportable_short",
    "Conc_Gross_LE_4_TDR_Long_All": "conc4_long",
    "Conc_Gross_LE_4_TDR_Short_All": "conc4_short",
    "Conc_Gross_LE_8_TDR_Long_All": "conc8_long",
    "Conc_Gross_LE_8_TDR_Short_All": "conc8_short",
    "Conc_Net_LE_4_TDR_Long_All": "conc4_net_long",
    "Conc_Net_LE_4_TDR_Short_All": "conc4_net_short",
    "Conc_Net_LE_8_TDR_Long_All": "conc8_net_long",
    "Conc_Net_LE_8_TDR_Short_All": "conc8_net_short",
}

COLUMN_MAPS = {
    "disaggregated": DISAGG_COLUMNS,
    "tff": TFF_COLUMNS,
}

# Trader categories for each report type
DISAGG_CATEGORIES = {
    "Producer/Merchant": ("prod_merc_long", "prod_merc_short"),
    "Swap Dealers": ("swap_long", "swap_short"),
    "Managed Money": ("managed_money_long", "managed_money_short"),
    "Other Reportable": ("other_long", "other_short"),
    "Non-Reportable": ("nonreportable_long", "nonreportable_short"),
}

TFF_CATEGORIES = {
    "Dealer/Intermediary": ("dealer_long", "dealer_short"),
    "Asset Manager": ("asset_mgr_long", "asset_mgr_short"),
    "Leveraged Funds": ("lev_money_long", "lev_money_short"),
    "Other Reportable": ("other_long", "other_short"),
    "Non-Reportable": ("nonreportable_long", "nonreportable_short"),
}

CATEGORIES = {
    "disaggregated": DISAGG_CATEGORIES,
    "tff": TFF_CATEGORIES,
}

# Weekly change columns per category
DISAGG_CHANGES = {
    "Producer/Merchant": ("change_prod_merc_long", "change_prod_merc_short"),
    "Swap Dealers": ("change_swap_long", "change_swap_short"),
    "Managed Money": ("change_managed_money_long", "change_managed_money_short"),
    "Other Reportable": ("change_other_long", "change_other_short"),
}

TFF_CHANGES = {
    "Dealer/Intermediary": ("change_dealer_long", "change_dealer_short"),
    "Asset Manager": ("change_asset_mgr_long", "change_asset_mgr_short"),
    "Leveraged Funds": ("change_lev_money_long", "change_lev_money_short"),
    "Other Reportable": ("change_other_long", "change_other_short"),
}

CHANGES = {
    "disaggregated": DISAGG_CHANGES,
    "tff": TFF_CHANGES,
}

# Pct of OI columns per category (including spreads where available)
DISAGG_PCT = {
    "Producer/Merchant Long": "pct_prod_merc_long",
    "Producer/Merchant Short": "pct_prod_merc_short",
    "Swap Dealers Long": "pct_swap_long",
    "Swap Dealers Short": "pct_swap_short",
    "Managed Money Long": "pct_managed_money_long",
    "Managed Money Short": "pct_managed_money_short",
    "Other Reportable Long": "pct_other_long",
    "Other Reportable Short": "pct_other_short",
    "Non-Reportable Long": "pct_nonreportable_long",
    "Non-Reportable Short": "pct_nonreportable_short",
}

TFF_PCT = {
    "Dealer Long": "pct_dealer_long",
    "Dealer Short": "pct_dealer_short",
    "Asset Manager Long": "pct_asset_mgr_long",
    "Asset Manager Short": "pct_asset_mgr_short",
    "Leveraged Funds Long": "pct_lev_money_long",
    "Leveraged Funds Short": "pct_lev_money_short",
    "Other Reportable Long": "pct_other_long",
    "Other Reportable Short": "pct_other_short",
    "Non-Reportable Long": "pct_nonreportable_long",
    "Non-Reportable Short": "pct_nonreportable_short",
}

PCT_COLUMNS = {
    "disaggregated": DISAGG_PCT,
    "tff": TFF_PCT,
}

# SQLite database path
import os
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "cot.db")

# Refresh interval in days
REFRESH_INTERVAL_DAYS = 7
