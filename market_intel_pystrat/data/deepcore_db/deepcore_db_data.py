from __future__ import annotations

FUTURES_ASSET_NAMES = {
    "SB11": "sb11",
    "ARBC": "arabica",
    "ARABICA": "arabica",
    "RBST": "robusta",
    "ROBUSTA": "robusta",
    "CORN": "corn",  # not yet populated in DB, same table/format expected
}
FUTURES_PRICE_DIVISOR = 100.0 # data in db are in cents (13.92 => 1395 ; 3000.00 => 300000)

FUTURES_QUERY = """
    SELECT date, open, high, low, close, volume
    FROM public.data_market_intelligence_futures
    WHERE name = %s
    ORDER BY date ASC
"""

# Mono-series spots: one (commodity, 'Spot Index' period) pair -> bid/offer.
SPOT_ASSET_IDS = {
    "VHP": {
        "data_commodity_id": "96bb478f-7baf-4027-a9dc-2c646644f90f",   # VHP FOB Brazil
        "shipment_period_id": "d95ff7a9-644e-4b9a-b57c-fbd0ffeecae1",  # Spot Index
    },
    "THP": {
        "data_commodity_id": "48b9390f-6333-42bd-bb91-8f6d585960d6",   # Thai High Pol FOB
        "shipment_period_id": "3baa818d-9972-4b9a-9eea-3f6e9e92f58d",  # Spot Index
    },
    "CORN_ARG": {
        "data_commodity_id": "70c7919a-eca1-4abc-a744-e7dcdf60b0b4",   # FOB Corn Arg
        "shipment_period_id": "50d26a29-c851-43b0-9657-6e5eabe5bcca",  # Spot Index
    },
    "CORN_BRZ": {
        "data_commodity_id": "6202aa06-8052-423b-bab3-9c06044e1dbe",   # Corn santos
        "shipment_period_id": "7f1fccef-e7f3-4b64-887e-0aeec8d0b511",  # Spot Index
    },
}

SPOT_QUERY = """
    SELECT q.date, q.bid, q.offer
    FROM public.quotations q
    WHERE q.data_commodity_id = %s
    AND q.shipment_period_id = %s
    ORDER BY q.date ASC
"""

# Multi-origin coffee spots: the shipment_period encodes the origin, and the
# period names match the Excel market headers ('Brazil GC', 'Vietnam', ...).
COFFEE_SPOT_ASSET_IDS = {
    "COFFEE_ARBC": "0d39d62c-96d8-471e-acd9-956ed0a39842",  # Coffee Arabica
    "COFFEE_RBST": "0ccd8b25-0e9a-4d0a-91fb-c573cffd9f21",  # Coffee Robusta
}

COFFEE_SPOT_QUERY = """
    SELECT q.date, p.name AS origin, q.bid, q.offer
    FROM public.quotations q
    JOIN public.data_shipment_periods p ON p.id = q.shipment_period_id
    WHERE q.data_commodity_id = %s
    ORDER BY q.date ASC
"""