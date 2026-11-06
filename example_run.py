from databento_pipeline.client import BudgetGuardedClient
from databento_pipeline.stitcher import ContinuousContractStitcher, RollMethod, AdjustmentMethod

def main():
    print("=== Databento Futures Pipeline Pipeline Execution ===")
    
    # 1. Initialize budget-guarded client
    client = BudgetGuardedClient(max_cost_usd=5.00, cache_dir="./data/cache")
    
    # 2. Query data (checks local cache first)
    df = client.fetch_data(
        dataset="GLBX.MDP3",
        symbols=["CLZ4", "CLF5"],
        schema="ohlcv-1m",
        start="2024-10-01",
        end="2024-10-30"
    )
    print(f"Retrieved {len(df)} total raw contract records.")

    # 3. Stitch continuous series using Ratio adjustment
    stitcher = ContinuousContractStitcher(
        roll_method=RollMethod.VOLUME,
        adjustment=AdjustmentMethod.RATIO
    )
    continuous_df = stitcher.stitch(df)
    print("\n--- Stitched Continuous Data Preview ---")
    print(continuous_df[["ts_event", "symbol", "close", "adj_close"]].head())

if __name__ == "__main__":
    main()
