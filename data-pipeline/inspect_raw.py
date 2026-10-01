from pathlib import Path
import pandas as pd

RAW = Path(__file__).parent / "raw"

for f in sorted(RAW.glob("*.csv")):
    df = pd.read_csv(f, na_values=["\\N"], keep_default_na=False)
    print(f"\n=== {f.name}: {len(df)} righe, {len(df.columns)} colonne")
    summary = pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "null": df.isna().sum(),
        "distinct": df.nunique(),
        "esempio": df.iloc[0] if len(df) else None,
    })
    print(summary.to_string())
    print("righe duplicate:", df.duplicated().sum())