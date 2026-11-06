import os
import tempfile
import pandas as pd
from databento_pipeline.cache import ParquetCache

def test_parquet_cache_write_and_read():
    with tempfile.TemporaryDirectory() as tmp_dir:
        cache = ParquetCache(base_dir=tmp_dir)

        df = pd.DataFrame({
            "ts_event": pd.date_range("2024-10-01", "2024-10-03", freq="1D"),
            "symbol": ["CLZ4"] * 3,
            "open": [70.0, 71.0, 72.0],
            "high": [71.5, 72.5, 73.5],
            "low": [69.5, 70.5, 71.5],
            "close": [70.5, 71.8, 72.4],
            "volume": [1000, 1100, 1200],
            "open_interest": [5000, 4900, 4800]
        })

        cache.write(df, dataset="GLBX.MDP3")
        res = cache.read(dataset="GLBX.MDP3", symbols=["CLZ4"], start="2024-10-01", end="2024-10-03")

        assert not res.empty
        assert len(res) == 3
        assert res["symbol"].iloc[0] == "CLZ4"
