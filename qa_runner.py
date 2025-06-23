import pandas as pd

def run_tests_on_schedule(df):
    errors = []

    try:
        if df["Right-of-use Asset Closing Balance"].iloc[-1] != "0":
            errors.append("❌ Right-of-use asset does not reduce to 0 at lease end.")
        if df["Closing Liability"].iloc[-1] != "0":
            errors.append("❌ Lease liability does not reduce to 0 at lease end.")
    except Exception as e:
        errors.append(f"❌ Error parsing schedule: {e}")

    if not errors:
        print("✅ All QA checks passed.")
    else:
        for error in errors:
            print(error)
        raise Exception("🚨 QA validation failed.")

if __name__ == "__main__":
    # For testing purposes, read a mock schedule
    try:
        df = pd.read_csv("schedule.csv")  # Replace with your actual schedule export if needed
        run_tests_on_schedule(df)
    except FileNotFoundError:
        print("⚠️ schedule.csv not found. Skipping test.")
