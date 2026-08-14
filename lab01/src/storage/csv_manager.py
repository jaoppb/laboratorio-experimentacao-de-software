import csv
import os
from typing import Dict, List

import structlog

logger = structlog.get_logger(__name__)


class CSVManager:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def save(self, rows: List[Dict], filename: str):
        if not rows:
            logger.warning(f"No rows to save for {filename}")
            return

        filepath = os.path.join(self.output_dir, filename)

        # Gather all unique keys for fieldnames to handle merged or varying rows
        fieldnames = []
        for row in rows:
            for k in row.keys():
                if k not in fieldnames:
                    fieldnames.append(k)

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        logger.info(f"Saved {len(rows)} records to {filepath}")

    def merge_and_save(
        self, datasets: List[List[Dict]], filename: str, merge_key: str = "repo"
    ):
        if not datasets:
            logger.warning(f"No datasets to merge for {filename}")
            return

        merged_data = {}
        for dataset in datasets:
            for row in dataset:
                key = row.get(merge_key)
                if key:
                    if key not in merged_data:
                        merged_data[key] = {}
                    merged_data[key].update(row)

        final_rows = list(merged_data.values())
        self.save(final_rows, filename)
