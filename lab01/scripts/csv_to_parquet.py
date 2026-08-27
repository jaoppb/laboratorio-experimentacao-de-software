"""Converts dados/unified_sample.csv to Parquet for the dashboard.

Parquet (snappy) was chosen over Arrow/Feather after comparing both formats
on this dataset: `primary_language` is low-cardinality (312 distinct values
repeated across ~100k rows) and benefits heavily from Parquet's dictionary
encoding, while `repo`/`id` are near-unique strings that only benefit from
generic compression. Measured on this file: CSV 13.06 MB -> Parquet/snappy
6.34 MB vs. Feather/uncompressed 10.96 MB. zstd compresses smaller in both
formats (~5 MB) but the in-browser reader (hyparquet) only implements
snappy decompression in pure JS, so snappy was kept to avoid adding a WASM
codec dependency to the dashboard.

Usage: uv run scripts/csv_to_parquet.py
"""

from pathlib import Path

import pandas as pd

script_dir = Path(__file__).resolve().parent

possible_paths = [
    script_dir / "../dados/unified_sample.csv",
    Path.cwd() / "dados/unified_sample.csv",
    Path.cwd() / "lab01/dados/unified_sample.csv",
]

csv_path = next((p.resolve() for p in possible_paths if p.exists()), None)

if not csv_path:
    raise FileNotFoundError(
        "Could not locate 'dados/unified_sample.csv'. Ensure the file exists."
    )

parquet_path = csv_path.with_suffix(".parquet")

df = pd.read_csv(csv_path)

potential_int_cols = [
    "age_days",
    "merged_pull_requests",
    "open_pull_requests",
    "total_pull_requests",
    "total_releases",
    "time_since_update_days",
    "closed_issues",
    "open_issues",
    "total_issues",
    "stargazer_count",
    "fork_count",
    "watchers_count",
    "disk_usage_kb",
]
for col in potential_int_cols:
    if col in df.columns:
        df[col] = df[col].fillna(0).astype("int32")


df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
df["updated_at"] = pd.to_datetime(df["updated_at"], utc=True)
df["primary_language"] = df["primary_language"].astype("category")
# Kept at float64 (not downcast to float32): closed_issues_ratio is compared
# against exact bucket thresholds (e.g. 0.9) in the dashboard, and float32
# rounding flips ~242 rows across that boundary (values like 9/10 round to
# 0.899999976f32). The precision loss isn't worth the negligible size gain.

df.to_parquet(parquet_path, engine="pyarrow", compression="snappy", index=False)

csv_size = csv_path.stat().st_size / 1024 / 1024
parquet_size = parquet_path.stat().st_size / 1024 / 1024
print(f"{csv_path.name}: {csv_size:.2f} MB -> {parquet_path.name}: {parquet_size:.2f} MB")
print(f"{len(df)} rows written to {parquet_path}")
