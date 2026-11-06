import os
import glob
import pandas as pd
from typing import List

class ParquetCache:
    """
    Day-partitioned local Apache Parquet cache layer.
    Partition format: base_dir/dataset={dataset}/symbol={symbol}/year={YYYY}/month={MM}/day={DD}.parquet
    """

    def __init__(self, base_dir: str = "./data/cache"):
        self.base_dir = base_dir

    def read(self, dataset: str, symbols: List[str], start: str, end: str) -> pd.DataFrame:
        """Reads cached partitioned parquet files covering the given range."""
        start_dt = pd.to_datetime(start)
        end_dt = pd.to_datetime(end)

        records = []
        for symbol in symbols:
            symbol_dir = os.path.join(self.base_dir, f"dataset={dataset}", f"symbol={symbol}")
            if not os.path.exists(symbol_dir):
                continue

            for filepath in glob.glob(os.path.join(symbol_dir, "**", "*.parquet"), recursive=True):
                # Extract date from parquet filename path
                df_part = pd.read_parquet(filepath)
                if not df_part.empty:
                    df_part["ts_event"] = pd.to_datetime(df_part["ts_event"])
                    mask = (df_part["ts_event"] >= start_dt) & (df_part["ts_event"] <= end_dt)
                    filtered = df_part.loc[mask]
                    if not filtered.empty:
                        records.append(filtered)

        if not records:
            return pd.DataFrame()

        combined = pd.concat(records, ignore_index=True)
        return combined.sort_values(by="ts_event").reset_index(drop=True)

    def write(self, df: pd.DataFrame, dataset: str) -> None:
        """Writes DataFrame to local day-partitioned Parquet files."""
        if df.empty:
            return

        df = df.copy()
        df["ts_event"] = pd.to_datetime(df["ts_event"])

        for (symbol, dt), group in df.groupby(["symbol", df["ts_event"].dt.date]):
            year_str = f"year={dt.year:04d}"
            month_str = f"month={dt.month:02d}"
            day_filename = f"day={dt.day:02d}.parquet"

            out_dir = os.path.join(self.base_dir, f"dataset={dataset}", f"symbol={symbol}", year_str, month_str)
            os.makedirs(out_dir, exist_ok=True)
            out_file = os.path.join(out_dir, day_filename)

            group.to_parquet(out_file, index=False)
