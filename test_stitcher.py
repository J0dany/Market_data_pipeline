import pandas as pd
from databento_pipeline.stitcher import ContinuousContractStitcher, RollMethod, AdjustmentMethod
from databento_pipeline.mock_data import generate_mock_futures_data

def test_stitching_difference_and_ratio():
    mock_df = generate_mock_futures_data(["CLZ4", "CLF5"], "2024-10-01", "2024-10-20")

    diff_stitcher = ContinuousContractStitcher(roll_method=RollMethod.VOLUME, adjustment=AdjustmentMethod.DIFFERENCE)
    diff_df = diff_stitcher.stitch(mock_df)

    ratio_stitcher = ContinuousContractStitcher(roll_method=RollMethod.VOLUME, adjustment=AdjustmentMethod.RATIO)
    ratio_df = ratio_stitcher.stitch(mock_df)

    assert "adj_close" in diff_df.columns
    assert "adj_close" in ratio_df.columns
    assert len(diff_df) > 0
    assert len(ratio_df) > 0
