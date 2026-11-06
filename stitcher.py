import enum
import pandas as pd
import numpy as np
from typing import List, Tuple

class RollMethod(enum.Enum):
    VOLUME = "volume"
    OPEN_INTEREST = "open_interest"
    FIXED_DAYS = "fixed_days"


class AdjustmentMethod(enum.Enum):
    DIFFERENCE = "difference"  # Shift historical prices additively
    RATIO = "ratio"            # Scale historical prices multiplicatively
    NONE = "none"              # Raw price series with seam jumps


class ContinuousContractStitcher:
    """
    Stitches expiring individual futures contract legs into continuous price series
    with automated roll triggers and backward adjustment mechanics.
    """

    def __init__(
        self,
        roll_method: RollMethod = RollMethod.VOLUME,
        adjustment: AdjustmentMethod = AdjustmentMethod.RATIO,
        roll_days_prior: int = 5
    ):
        self.roll_method = roll_method
        self.adjustment = adjustment
        self.roll_days_prior = roll_days_prior

    def detect_roll_points(self, df: pd.DataFrame) -> List[Tuple[pd.Timestamp, str, str]]:
        """
        Identifies exact roll timestamps where active contract transitions to next contract.
        Returns list of tuples: (roll_timestamp, outgoing_symbol, incoming_symbol).
        """
        df = df.sort_values(by=["ts_event", "symbol"]).reset_index(drop=True)
        symbols = sorted(df["symbol"].unique())
        if len(symbols) < 2:
            return []

        rolls = []
        for i in range(len(symbols) - 1):
            curr_sym = symbols[i]
            next_sym = symbols[i + 1]

            curr_data = df[df["symbol"] == curr_sym].set_index("ts_event")
            next_data = df[df["symbol"] == next_sym].set_index("ts_event")

            common_idx = curr_data.index.intersection(next_data.index)
            if len(common_idx) == 0:
                continue

            roll_ts = None
            if self.roll_method == RollMethod.VOLUME:
                # Roll when next contract volume exceeds active contract volume
                crossover = next_data.loc[common_idx, "volume"] > curr_data.loc[common_idx, "volume"]
                if crossover.any():
                    roll_ts = crossover.idxmax()
            elif self.roll_method == RollMethod.OPEN_INTEREST:
                crossover = next_data.loc[common_idx, "open_interest"] > curr_data.loc[common_idx, "open_interest"]
                if crossover.any():
                    roll_ts = crossover.idxmax()
            elif self.roll_method == RollMethod.FIXED_DAYS:
                roll_ts = common_idx[-min(self.roll_days_prior, len(common_idx))]

            if roll_ts is None:
                roll_ts = common_idx[len(common_idx) // 2]

            rolls.append((roll_ts, curr_sym, next_sym))

        return rolls

    def stitch(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Stitches contract data into a continuous series, applying selected adjustment methodology.
        """
        if df.empty:
            return df

        rolls = self.detect_roll_points(df)
        if not rolls:
            # Single contract or no crossover detected
            res = df.copy()
            res["adj_close"] = res["close"]
            return res.sort_values("ts_event").reset_index(drop=True)

        # Build raw unadjusted continuous chain
        segments = []
        symbols = sorted(df["symbol"].unique())
        
        # Segment slices based on rolls
        start_ts = df["ts_event"].min()
        for i, (roll_ts, outgoing, incoming) in enumerate(rolls):
            seg = df[(df["symbol"] == outgoing) & (df["ts_event"] >= start_ts) & (df["ts_event"] < roll_ts)].copy()
            segments.append(seg)
            start_ts = roll_ts

        # Add final active segment
        final_sym = rolls[-1][2]
        final_seg = df[(df["symbol"] == final_sym) & (df["ts_event"] >= start_ts)].copy()
        segments.append(final_seg)

        continuous_df = pd.concat(segments, ignore_index=True).sort_values("ts_event").reset_index(drop=True)
        continuous_df["adj_close"] = continuous_df["close"].astype(float)
        continuous_df["adj_open"] = continuous_df["open"].astype(float)
        continuous_df["adj_high"] = continuous_df["high"].astype(float)
        continuous_df["adj_low"] = continuous_df["low"].astype(float)

        if self.adjustment == AdjustmentMethod.NONE:
            return continuous_df

        # Apply backward adjustments at roll seams
        for roll_ts, outgoing, incoming in reversed(rolls):
            out_row = df[(df["symbol"] == outgoing) & (df["ts_event"] == roll_ts)]
            in_row = df[(df["symbol"] == incoming) & (df["ts_event"] == roll_ts)]

            if out_row.empty or in_row.empty:
                continue

            p_out = out_row["close"].values[0]
            p_in = in_row["close"].values[0]

            mask = continuous_df["ts_event"] < roll_ts

            if self.adjustment == AdjustmentMethod.DIFFERENCE:
                diff = p_in - p_out
                continuous_df.loc[mask, "adj_close"] += diff
                continuous_df.loc[mask, "adj_open"] += diff
                continuous_df.loc[mask, "adj_high"] += diff
                continuous_df.loc[mask, "adj_low"] += diff

            elif self.adjustment == AdjustmentMethod.RATIO:
                ratio = p_in / p_out if p_out != 0 else 1.0
                continuous_df.loc[mask, "adj_close"] *= ratio
                continuous_df.loc[mask, "adj_open"] *= ratio
                continuous_df.loc[mask, "adj_high"] *= ratio
                continuous_df.loc[mask, "adj_low"] *= ratio

        return continuous_df
