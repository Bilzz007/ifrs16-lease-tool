import pandas as pd

def run_ifrs16_tests(df):
    errors = []

    # 1. Test ROU asset reduces to zero
    try:
        rou_final = float(str(df["Right-of-use Asset Closing Balance"].iloc[-1]).replace(",", ""))
        if round(rou_final, 2) != 0.0:
            errors.append("❌ Right-of-use asset does not reduce to zero at lease end.")
    except Exception as e:
        errors.append(f"❌ ROU asset check failed: {e}")

    # 2. Test Lease Liability reduces to zero
    try:
        liability_final = float(str(df["Closing Liability"].iloc[-1]).replace(",", ""))
        if round(liability_final, 2) != 0.0:
            errors.append("❌ Lease liability does not reduce to zero at lease end.")
    except Exception as e:
        errors.append(f"❌ Liability check failed: {e}")

    # 3. Test Depreciation adds up to ROU
    try:
        depreciation_total = df["Depreciation"].str.replace(",", "").astype(float).sum()
        rou_opening = float(str(df["Right-of-use Asset Closing Balance"].iloc[0]).replace(",", ""))
        if abs(depreciation_total - rou_opening) > 1:
            errors.append(f"❌ Total depreciation ({depreciation_total:,.0f}) ≠ ROU asset opening ({rou_opening:,.0f})")
    except Exception as e:
        errors.append(f"❌ Depreciation sum check failed: {e}")

    # 4. Test for constant monthly payment unless CPI/Modification
    try:
        payments = df["Payment"].str.replace(",", "").astype(float)
        unique_payments = payments.nunique()
        if unique_payments > 1:
            errors.append("⚠️ Payments vary month-to-month — CPI or modification logic should be confirmed.")
    except Exception as e:
        errors.append(f"❌ Payment consistency check failed: {e}")

    # 5. Optional: Detect CPI flag but no visible escalation
    try:
        cpi_detected = df["Payment"].duplicated().sum() == 0 and len(df) > 1
        if cpi_detected:
            errors.append("⚠️ All payments are different — did you intend CPI-linked escalation?")
    except:
        pass

    if not errors:
        print("✅ All IFRS 16 QA checks passed.")
    else:
        for e in errors:
            print(e)
        raise Exception("🚨 IFRS 16 QA validation failed.")

if __name__ == "__main__":
    try:
        df = pd.read_csv("schedule.csv")
        run_ifrs16_tests(df)
    except FileNotFoundError:
        print("⚠️ schedule.csv not found. QA skipped.")
