import os
import pandas as pd
from typing import List, Optional
from databento_pipeline.cache import ParquetCache

# Databento unit pricing estimates per schema/dataset (approx per GB)
ESTIMATED_COST_PER_GB = {
    "ohlcv-1m": 0.05,
    "ohlcv-1s": 0.20,
    "trades": 0.75,
    "mbp-1": 1.50,
    "mbp-10": 3.00,
}

class BudgetExceededError(Exception):
    """Raised when a requested Databento query exceeds cost or data spending caps."""
    pass


class BudgetGuardedClient:
    """
    Wrapper around Databento Historical API client featuring pre-flight cost estimation,
    spending guards, and seamless local Parquet caching.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_cost_usd: float = 10.00,
        max_gigabytes: float = 2.0,
        cache_dir: str = "./data/cache"
    ):
        self.api_key = api_key or os.getenv("DATABENTO_API_KEY")
        self.max_cost_usd = max_cost_usd
        self.max_gigabytes = max_gigabytes
        self.cache = ParquetCache(base_dir=cache_dir)

    def estimate_cost(self, dataset: str, schema: str, start: str, end: str, num_symbols: int) -> dict:
        """
        Performs a pre-flight estimate of data size and projected cost.
        """
        start_dt = pd.to_datetime(start)
        end_dt = pd.to_datetime(end)
        days = max((end_dt - start_dt).days, 1)

        # Baseline size heuristic: ~1.5MB per symbol per day for minute OHLCV
        est_gb_per_symbol_day = 0.0015
        if "trade" in schema:
            est_gb_per_symbol_day = 0.02
        elif "mbp" in schema:
            est_gb_per_symbol_day = 0.10

        est_gb = days * num_symbols * est_gb_per_symbol_day
        rate_per_gb = ESTIMATED_COST_PER_GB.get(schema, 0.50)
        est_cost_usd = est_gb * rate_per_gb

        return {
            "estimated_gb": round(est_gb, 4),
            "estimated_cost_usd": round(est_cost_usd, 4),
            "days": days,
            "symbols": num_symbols
        }

    def fetch_data(
        self,
        dataset: str,
        symbols: List[str],
        schema: str,
        start: str,
        end: str
    ) -> pd.DataFrame:
        """
        Fetches data, checking local cache first. If missing, runs pre-flight budget checks,
        pulls from Databento (or mock API), and caches the output.
        """
        # Check cache
        cached_df = self.cache.read(dataset=dataset, symbols=symbols, start=start, end=end)
        if not cached_df.empty:
            return cached_df

        # Pre-flight check
        estimation = self.estimate_cost(dataset, schema, start, end, len(symbols))
        if estimation["estimated_cost_usd"] > self.max_cost_usd:
            raise BudgetExceededError(
                f"Request estimated cost (${estimation['estimated_cost_usd']}) "
                f"exceeds maximum allowed limit (${self.max_cost_usd})."
            )

        if estimation["estimated_gb"] > self.max_gigabytes:
            raise BudgetExceededError(
                f"Request estimated size ({estimation['estimated_gb']} GB) "
                f"exceeds maximum allowed limit ({self.max_gigabytes} GB)."
            )

        # Retrieve remote data (or mock if no key available)
        df = self._query_databento_api(dataset, symbols, schema, start, end)
        self.cache.write(df=df, dataset=dataset)
        return df

    def _query_databento_api(self, dataset: str, symbols: List[str], schema: str, start: str, end: str) -> pd.DataFrame:
        """Executes query against Databento API if client key is configured, else falls back to local execution logic."""
        if self.api_key and self.api_key != "mock_key":
            import databento as db
            client = db.Historical(self.api_key)
            data = client.timeseries.get_range(
                dataset=dataset,
                symbols=symbols,
                schema=schema,
                start=start,
                end=end
            )
            return data.to_df()
        else:
            # Stand-in generation for dry runs/offline testing
            from databento_pipeline.mock_data import generate_mock_futures_data
            return generate_mock_futures_data(symbols=symbols, start_date=start, end_date=end)
