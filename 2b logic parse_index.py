import json
import re
import csv
from pathlib import Path

# -- Config --------------------------------------------------------------------
DATA_DIR   = Path(__file__).parent
OUTPUT_CSV = DATA_DIR / "centene_ca_commercial_group.csv"

# -- Valid US state abbreviations (used to validate URL suffixes) ---------------
US_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
    "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
    "VA","WA","WV","WI","WY","DC","PR","GU","VI","AS","MP",
}

# ==============================================================================
#  Signal 1 (block-level): extract state from in_network_files URL suffix
# ==============================================================================
#  URL patterns observed:
#    ambetter-ok_in-network.json    -> state OK   (brand-STATE)
#    healthnet-ca_in-network.json   -> state CA   (brand-STATE)
#    fidelis-ex_in-network.json     -> suffix EX  (product type, NOT a state)
#    qualchoice_in-network.json     -> no suffix  (brand only)
#
#  We extract the 2-letter suffix after the last hyphen in the brand segment,
#  then validate it against US_STATES to distinguish real states from product
#  type codes like 'ex'/'es'.

def extract_block_state(in_network_files):
    """Return the US state code from URL suffix, or None if not a valid state."""
    for f in in_network_files:
        url = f.get("location", "")
        # Match: brand-{XX}_in-network  or  brand-{XX}_allowed-amounts
        m = re.search(r'-([a-zA-Z]{2})_(?:in-network|allowed-amounts)', url)
        if m:
            code = m.group(1).upper()
            if code in US_STATES:
                return code
    return None


# ==============================================================================
#  Signal 2 (plan-level): extract state from HIOS plan_id
# ==============================================================================
#  HIOS IDs embed the 2-letter state code: 67138CA073 -> CA
#  EIN-type IDs (pure numeric like 474726731) have no state info.

def extract_hios_state(plan_id):
    """Return state from HIOS plan ID, or None for EIN/short IDs."""
    m = re.search(r'\d{5}([A-Z]{2})\d', plan_id)
    if m:
        code = m.group(1)
        if code in US_STATES:
            return code
    return None


# ==============================================================================
#  Signal 3 (plan-level): extract state from plan_name prefix
# ==============================================================================
#  HealthNet CA large-group plans use: "CA L SC HMO ...", "CA T CUS ..."
#  This is California-specific; Oregon plans use company names instead.
#  We validate the prefix against US_STATES to avoid false positives
#  from names like "ERICKSON..." (ER) or "NW PIPE..." (NW).

def extract_name_state(plan_name):
    """Return state from plan_name prefix like 'CA L ...', or None."""
    m = re.match(r'^([A-Z]{2})\s', plan_name)
    if m:
        code = m.group(1)
        if code in US_STATES:
            return code
    return None


# ==============================================================================
#  State resolution: prioritised multi-signal merge
# ==============================================================================

def resolve_state(block_state, plan_id, plan_name):
    """Resolve state using priority: URL suffix > HIOS plan_id > name prefix.

    Returns (state_code, signals_list) where signals_list records which
    signals matched for transparency.
    """
    signals = []
    resolved = None

    # Priority 1: block-level URL suffix (covers all plans in block)
    if block_state:
        resolved = block_state
        signals.append("url")

    # Priority 2: plan-level HIOS ID
    hios = extract_hios_state(plan_id)
    if hios:
        if resolved is None:
            resolved = hios
        signals.append("plan_id")

    # Priority 3: plan-level name prefix (CA-specific convention)
    name_st = extract_name_state(plan_name)
    if name_st:
        if resolved is None:
            resolved = name_st
        signals.append("plan_name")

    return resolved, signals


# ==============================================================================
#  Brand normaliser
# ==============================================================================

def get_brand(issuer_name):
    n = issuer_name.lower()
    if "fidelis"    in n: return "Fidelis Care"
    if "ambetter"   in n: return "Ambetter"
    if "healthnet"  in n or "health net" in n: return "Health Net"
    if "qualchoice" in n: return "QualChoice"
    return issuer_name


# ==============================================================================
#  Core parser -- walks every reporting_structure block
# ==============================================================================

def parse_index(path):
    """Parse one index JSON and return California commercial group plan rows."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    ca_group_rows = []

    for block in data.get("reporting_structure", []):
        in_net_files = block.get("in_network_files", [])
        allowed_amt  = block.get("allowed_amount_file", {})

        # Signal 1: block-level state from URL
        block_state = extract_block_state(in_net_files)

        # Collect file URLs for this block
        in_net_urls = [f["location"] for f in in_net_files if f.get("location")]
        allowed_url = allowed_amt.get("location", "")

        for plan in block.get("reporting_plans", []):
            plan_name   = plan.get("plan_name", "")
            plan_id     = plan.get("plan_id", "")
            market_type = plan.get("plan_market_type", "")
            id_type     = plan.get("plan_id_type", "")
            issuer      = plan.get("issuer_name", "")
            sponsor     = plan.get("plan_sponsor_name", "")

            # Filter: only commercial group plans
            if market_type != "group":
                continue

            # Resolve state via multi-signal priority
            state, signals = resolve_state(block_state, plan_id, plan_name)

            # Keep only California plans
            if state != "CA":
                continue

            ca_group_rows.append({
                "source_file":        path.name,
                "brand":              get_brand(issuer),
                "plan_name":          plan_name,
                "plan_id":            plan_id,
                "plan_id_type":       id_type,
                "plan_market_type":   market_type,
                "issuer_name":        issuer,
                "plan_sponsor":       sponsor,
                "resolved_state":     state,
                "ca_signals":         "+".join(signals),
                "in_network_url":     "; ".join(in_net_urls),
                "allowed_amount_url": allowed_url,
            })

    return ca_group_rows


# ==============================================================================
#  Deduplication
# ==============================================================================

def deduplicate(rows):
    """Remove exact duplicates on (plan_name, plan_id, in_network_url)."""
    seen, out = set(), []
    for r in rows:
        key = (r["plan_name"], r["plan_id"], r["in_network_url"])
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


# ==============================================================================
#  Main
# ==============================================================================

FIELDS = [
    "source_file", "brand", "plan_name", "plan_id", "plan_id_type",
    "plan_market_type", "issuer_name", "plan_sponsor",
    "resolved_state", "ca_signals", "in_network_url", "allowed_amount_url",
]

def main():
    index_files = sorted(DATA_DIR.glob("*.json"))
    print(f"{'-'*60}")
    print(f"  Centene CA Commercial Group Plan Parser (v2)")
    print(f"  Found {len(index_files)} index file(s)")
    print(f"{'-'*60}\n")

    all_rows = []
    for f in index_files:
        rows = parse_index(f)
        print(f"  {f.name}")
        print(f"    -> {len(rows)} CA commercial group plan rows")
        all_rows.extend(rows)

    print(f"\n  Total before dedup : {len(all_rows)}")
    deduped = deduplicate(all_rows)
    print(f"  Total after dedup  : {len(deduped)}")

    # -- Signal breakdown ------------------------------------------------------
    sig_counts = {}
    for r in deduped:
        for s in r["ca_signals"].split("+"):
            sig_counts[s] = sig_counts.get(s, 0) + 1
    print(f"\n  Detection signal breakdown:")
    for sig, count in sorted(sig_counts.items()):
        print(f"    {sig:12s} : {count} plans")

    # -- Distinct rate file URLs -----------------------------------------------
    urls = sorted({r["in_network_url"] for r in deduped if r["in_network_url"]})
    print(f"\n  Distinct in-network URLs ({len(urls)}):")
    for u in urls:
        print(f"    {u}")

    # -- Write CSV -------------------------------------------------------------
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(deduped)

    print(f"\n  CSV written -> {OUTPUT_CSV}")
    print(f"{'-'*60}")


if __name__ == "__main__":
    main()
