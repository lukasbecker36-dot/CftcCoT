"""Categorize CFTC commodities into asset classes based on name keywords."""

# Keyword-based classification: if any keyword matches the commodity name
# (case-insensitive), it gets assigned to that category.
# Order matters — first match wins.

CATEGORY_RULES = {
    "Interest Rates": [
        "treasury", "t-note", "t-bond", "bond", "note",
        "eurodollar", "fed fund", "sofr", "libor", "swap rate",
        "eris", "ultra", "2-year", "5-year", "10-year", "30-year",
        "2-yr", "5-yr", "10-yr", "30-yr",
        "municipal", "interest rate",
    ],
    "FX": [
        "euro fx", "japanese yen", "british pound", "swiss franc",
        "canadian dollar", "australian dollar", "new zealand",
        "mexican peso", "brazilian real", "russian ruble",
        "south african rand", "dollar index", "dxy",
        "currency", "forex", "yen", "pound", "franc",
        "peso", "real", "rand", "ruble", "rupee",
        "bitcoin", "ether", "micro bitcoin", "micro ether",
    ],
    "Equity": [
        "s&p", "e-mini s&p", "nasdaq", "dow jones", "djia",
        "russell", "nikkei", "vix", "volatility",
        "equity", "stock", "micro e-mini",
    ],
    "Energy": [
        "crude oil", "natural gas", "heating oil", "gasoline",
        "rbob", "brent", "wti", "petroleum", "ethanol",
        "diesel", "fuel oil",
    ],
    "Metals": [
        "gold", "silver", "platinum", "palladium", "copper",
        "aluminum", "zinc", "nickel", "lead", "tin",
        "precious", "metal",
    ],
    "Ags": [
        "corn", "wheat", "soybean", "soy ", "oat", "rice",
        "cotton", "sugar", "coffee", "cocoa", "orange juice",
        "lumber", "milk", "cattle", "hog", "lean hog",
        "feeder", "live cattle", "pork", "butter", "cheese",
        "canola", "palm", "rubber",
    ],
}


def categorize_commodity(name: str) -> str:
    """Return the category for a given commodity name."""
    lower = name.lower()
    for category, keywords in CATEGORY_RULES.items():
        for kw in keywords:
            if kw in lower:
                return category
    return "Other"


def build_category_map(commodities: list[str]) -> dict[str, list[str]]:
    """Build a dict of {category: [sorted commodity names]}.

    Args:
        commodities: List of unique commodity name strings.

    Returns:
        Dict mapping category names to sorted lists of commodities.
    """
    cat_map: dict[str, list[str]] = {}
    for comm in commodities:
        cat = categorize_commodity(comm)
        cat_map.setdefault(cat, []).append(comm)

    # Sort commodities within each category
    for cat in cat_map:
        cat_map[cat] = sorted(cat_map[cat])

    return cat_map
