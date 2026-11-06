import pytest
from databento_pipeline.client import BudgetGuardedClient, BudgetExceededError

def test_budget_estimation_pass():
    client = BudgetGuardedClient(max_cost_usd=10.0, max_gigabytes=5.0)
    est = client.estimate_cost("GLBX.MDP3", "ohlcv-1m", "2024-10-01", "2024-10-10", 2)
    assert est["estimated_cost_usd"] < 10.0

def test_budget_exceeded_guard():
    client = BudgetGuardedClient(max_cost_usd=0.0001, max_gigabytes=0.0001)
    with pytest.raises(BudgetExceededError):
        client.fetch_data("GLBX.MDP3", ["CLZ4"], "ohlcv-1m", "2024-01-01", "2024-10-01")
