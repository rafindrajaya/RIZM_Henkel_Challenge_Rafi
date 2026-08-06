import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from src.optimization_model import compute_pv_normalized_yield

solar_path = PROJECT_ROOT / "data" / "solar_data_duesseldorf_2025.csv"
df_solar = pd.read_csv(solar_path, index_col=0, parse_dates=True)
df_solar["pv_normalized_yield"] = compute_pv_normalized_yield(df_solar)
df_solar.to_csv(solar_path)
print("Successfully added pv_normalized_yield column to data/solar_data_duesseldorf_2025.csv")
print(df_solar[["ghi", "pv_normalized_yield"]].head())
