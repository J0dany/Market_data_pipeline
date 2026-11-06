import pandas as pd
import numpy as np
from typing import List

def generate_mock_futures_data(symbols: List[str], start_date: str, end_date: str) -> pd.DataFrame:
    """Generates realistic synthetic futures contract data with volume crossover for offline tests."""
    dates = pd.date_range(start=start_date, end=end_date, freq="1D")
    dfs = []

    base_price = 70.0
    for idx, symbol in enumerate(symbols):
        n = len(dates)
        price_trend = base_price + (idx * 2.5) + np.sin(np.linspace(0, 3, n)) * 2.0
        
        # Volume curve: earlier contracts decline, later contracts rise
        if idx == 0:
            vol = np.linspace(10000, 1000, n)
            oi = np.linspace(50000, 5000, n)
        else:
            vol = np.linspace(1000, 12000, n)
            oi = np.linspace(5000, 60000, n)

        df = pd.DataFrame({
            "ts_event": dates,
            "symbol": symbol,
            "open": price_trend - 0.5,
            "high": price_trend + 1.2,
            "low": price_trend - 0.8,
            "close": price_trend,
            "volume": vol.astype(int),
            "open_interest": oi.astype(int)
        })
        dfs.append(df)

    return pd.concat(dfs, ignore_index=True)
