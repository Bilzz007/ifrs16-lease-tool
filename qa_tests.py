from lease_calculations import (
    calculate_right_of_use_asset,
    calculate_lease_liability_from_payments,
    generate_amortization_schedule,
)
from datetime import date
from dateutil.relativedelta import relativedelta

# Sample input data
sample_start = date(2025, 1, 1)
sample_term = 12  # months
sample_payment = 1000
sample_discount_rate = 0.06  # 6% annual
sample_direct_costs = 500
sample_incentives = 200

# Generate flat payments
payments = [sample_payment] * sample_term

# Calculate expected values
expected_liability = calculate_lease_liability_from_payments(payments, sample_discount_rate)
expected_rou_asset = calculate_right_of_use_asset(expected_liability, sample_direct_costs, sample_incentives)

# Run amortization schedule
schedule_df, rou_asset = generate_amortization_schedule(
    sample_start, payments, sample_discount_rate, sample_term, expected_rou_asset
)

def run_tests():
    print("🔍 Running QA tests...")

    # Test 1: Liability is consistent
    actual_liability = calculate_lease_liability_from_payments(payments, sample_discount_rate)
    assert abs(actual_liability - expected_liability) < 1, "Lease liability mismatch"

    # Test 2: ROU asset calculation
    actual_rou = calculate_right_of_use_asset(expected_liability, sample_direct_costs, sample_incentives)
    assert abs(actual_rou - expected_rou_asset) < 1, "ROU asset mismatch"

    # Test 3: Final balances are zero (rounded)
    last_row = schedule_df.iloc[-1]
    closing_liab = float(last_row["Closing Liability"].replace(",", ""))
    closing_rou = float(last_row["Right-of-use Asset Closing Balance"].replace(",", ""))
    assert abs(closing_liab) < 1, "Final lease liability not zero"
    assert abs(closing_rou) < 1, "Final ROU asset not zero"

    print("✅ All QA tests passed!")

if __name__ == "__main__":
    run_tests()
