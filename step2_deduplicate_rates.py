import csv
import statistics
import time
from collections import defaultdict

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent if BASE_DIR.name == "submission" else BASE_DIR

IN_NET_CSV = PROJECT_ROOT / "healthnet_csv" / "in_network.csv"
PROV_REF_CSV = PROJECT_ROOT / "healthnet_csv" / "provider_references.csv"
OUTPUT_CSV = PROJECT_ROOT / "healthnet_csv" / "step2_curated_rates.csv"
CHUNK_SIZE = 100000

def run_step_2_extraction():
    print("Step 2: Starting Rate Deduplication and Provider Linking (Challenge C4)...")
    t0 = time.time()

    # 1. Load provider reference mapping: provider_group_id -> list of (npi, tin, business_name)
    pg_to_providers = defaultdict(list)
    with open(PROV_REF_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pg_id = row["provider_group_id"].strip()
            npi = row["npi"].strip()
            tin = row["tin_value"].strip()
            biz = row["business_name"].strip()
            if npi:
                pg_to_providers[pg_id].append((npi, tin, biz))

    print(f"Loaded provider reference mapping for {len(pg_to_providers)} provider groups.")

    # 2. Stream & Chunk in_network.csv to aggregate rates and metadata per (npi, tin, billing_code)
    # Using dictionary of aggregated values
    # key: (npi, tin, billing_code) -> dict with meta and list of rates
    records = {}

    processed_rows = 0
    with open(IN_NET_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        chunk = []
        for row in reader:
            chunk.append(row)
            if len(chunk) >= CHUNK_SIZE:
                processed_rows += len(chunk)
                _process_chunk(chunk, pg_to_providers, records)
                print(f"Processed {processed_rows:,} / 1,500,288 rows (found {len(records):,} unique provider-code pairs so far)...")
                chunk = []

        if chunk:
            processed_rows += len(chunk)
            _process_chunk(chunk, pg_to_providers, records)
            print(f"Processed {processed_rows:,} / 1,500,288 total rows.")

    t_agg = time.time()
    print(f"Rate aggregation completed in {t_agg - t0:.2f}s. Curating and writing to CSV...")

    # 3. Write curated CSV file
    # Columns: npi, tin, business_name, billing_code, billing_code_type, name, description, billing_class, curated_rate, min_rate, max_rate, rate_observations
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(f_out)
        writer.writerow([
            "npi",
            "tin",
            "business_name",
            "billing_code",
            "billing_code_type",
            "name",
            "description",
            "billing_class",
            "curated_rate",
            "min_rate",
            "max_rate",
            "rate_observations"
        ])

        for (npi, tin, b_code), data in sorted(records.items()):
            rates = data["rates"]
            # Curated rate: median rate across contract observations
            curated_rate = round(statistics.median(rates), 2)
            min_rate = round(min(rates), 2)
            max_rate = round(max(rates), 2)
            rate_count = len(rates)

            writer.writerow([
                npi,
                tin,
                data["business_name"],
                b_code,
                data["billing_code_type"],
                data["name"],
                data["description"],
                data["billing_class"],
                f"{curated_rate:.2f}",
                f"{min_rate:.2f}",
                f"{max_rate:.2f}",
                rate_count
            ])

    t_end = time.time()
    print(f"Step 2 execution successfully completed in {t_end - t0:.2f}s.")
    print(f"Saved {len(records):,} curated records to: {OUTPUT_CSV}")

def _process_chunk(chunk, pg_to_providers, records):
    for row in chunk:
        rate_str = row["negotiated_rate"]
        if not rate_str:
            continue
        try:
            rate = float(rate_str)
        except ValueError:
            continue
        if rate <= 0:
            continue

        pg_id = row["provider_group_id"]
        b_code = row["billing_code"]
        b_type = row["billing_code_type"]
        name = row["name"]
        desc = row["description"]
        b_class = row["billing_class"]

        provs = pg_to_providers.get(pg_id, [])
        for npi, tin, biz in provs:
            key = (npi, tin, b_code)
            if key not in records:
                records[key] = {
                    "business_name": biz,
                    "billing_code_type": b_type,
                    "name": name,
                    "description": desc,
                    "billing_class": b_class,
                    "rates": [rate]
                }
            else:
                records[key]["rates"].append(rate)

if __name__ == "__main__":
    run_step_2_extraction()
