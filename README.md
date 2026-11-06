# Databento Futures Pipeline & Continuous Contract Stitcher

**Author:** Jodany Fanord  
**Language:** Python 3.10+  
**License:** MIT  

A robust, production-grade Python data pipeline that pulls historical futures market data from [Databento](https://databento.com/), caches data locally in day-partitioned Apache Parquet files, enforces pre-flight cost estimation and budget controls, and stitches expiring futures contracts into continuous, backtestable price series using standard roll detection and adjustment methodologies.

---

## Technical Overview & Architecture

Futures contracts expire periodically (e.g., monthly or quarterly). Constructing long-term historical price series requires splicing individual contract legs together. Naive concatenation introduces artificial price gaps (seams) caused by differences in forward curves (contango/backwardation). This pipeline resolves seam distortion while eliminating redundant API costs through disk caching.

```
+-------------------+      Cost Check /      +------------------------+
|  Databento API /  | ---- Budget Limit ----> |  Partitioned Parquet   |
| Remote Historical |                        |   Local Disk Cache     |
+-------------------+                        +------------------------+
                                                         |
                                                         v
                                             +------------------------+
                                             | Continuous Stitcher    |
                                             | - Roll Detection       |
                                             | - Diff / Ratio Adjust  |
                                             +------------------------+
                                                         |
                                                         v
                                             +------------------------+
                                             |  Backtestable Dataset  |
                                             +------------------------+
```

### Core Components

1. **Pre-Flight Cost Guard & Client Wrapper (`databento_pipeline/client.py`)**:
   - Calculates estimated query data size prior to dispatch.
   - Enforces configurable hard caps (`max_cost_usd` or `max_gigabytes`).
   - Prevents unbudgeted billing spikes on large historical data requests.

2. **Day-Partitioned Parquet Cache (`databento_pipeline/cache.py`)**:
   - Stores raw OHLCV / tick data partitioned by dataset, symbol, and date (`data/cache/dataset=GLBX.MDP3/symbol=CL/year=YYYY/month=MM/day=DD.parquet`).
   - Guarantees deterministic, reproducible backtest runs without network round-trips.
   - Reduces I/O overhead by scanning only requested date ranges rather than loading multi-gigabyte files.

3. **Continuous Contract Stitcher (`databento_pipeline/stitcher.py`)**:
   - Detects roll trigger points based on **Volume/Open Interest crossover** or **Fixed Days prior to expiration**.
   - Applies **Difference Adjustment** (additive shifting) to preserve absolute dollar moves.
   - Applies **Ratio Adjustment** (multiplicative scaling) to preserve percentage returns across seams.

---

## Installation

```bash
git clone https://github.com/jodanyfanord/databento-futures-pipeline.git
cd databento-futures-pipeline
pip install -r requirements.txt
```

---

## Configuration & Usage

Set your Databento API key:
```bash
export DATABENTO_API_KEY="db-your-api-key-here"
```

### 1. Fetching Data with Budget Guard
```python
from databento_pipeline.client import BudgetGuardedClient

client = BudgetGuardedClient(
    api_key="YOUR_API_KEY",
    max_cost_usd=5.00,  # Hard limit: max $5.00 spend per request
    cache_dir="./data/cache"
)

# Fetch historical data (checks cache first, queries API if missing)
df = client.get_range(
    dataset="GLBX.MDP3",
    symbols=["CLZ4", "CLF5"],
    schema="ohlcv-1m",
    start="2024-10-01",
    end="2024-11-01"
)
```

### 2. Generating Continuous Price Series
```python
from databento_pipeline.stitcher import ContinuousContractStitcher, RollMethod, AdjustmentMethod

stitcher = ContinuousContractStitcher(
    roll_method=RollMethod.VOLUME,       # Roll when volume shifts to next contract
    adjustment=AdjustmentMethod.RATIO     # Preserve percentage returns
)

continuous_df = stitcher.stitch(df)
print(continuous_df.tail())
```

---

## Difference vs. Ratio Adjustment Mechanics

| Feature | Difference Adjustment | Ratio Adjustment |
| :--- | :--- | :--- |
| **Formula** | $P_{adj} = P_{raw} + (P_{next} - P_{prev})$ | $P_{adj} = P_{raw} 	imes (P_{next} / P_{prev})$ |
| **Preserves** | Absolute dollar p&l ($ change) | Percentage return distribution (% change) |
| **Best For** | Fixed dollar position sizing, spread trading | Equity/percentage position sizing, momentum algorithms |
| **Drawback** | Can lead to negative price values in severe backwardation | Distorts historical price levels in long series |

---

## Offline Unit Test Suite

Run the comprehensive unit test suite without hitting live endpoints or consuming Databento credits:

```bash
pytest tests/
```

---
*Created by Jodany Fanord (Georgia Institute of Technology).*
