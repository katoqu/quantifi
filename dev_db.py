"""Development helper: purge and seed the Supabase DB.

Usage:
  python dev_db.py --purge --yes      # purge all data
  python dev_db.py --seed             # seed sample data
  python dev_db.py --both --yes       # purge then seed

Requires that Streamlit secrets are available (same as the app).
"""
from datetime import date, timedelta
import argparse
from supabase_client import sb


def purge_all(yes: bool = False):
    if not yes:
        confirm = input("This will DELETE ALL DATA from the Supabase DB. Type 'yes' to continue: ")
        if confirm.strip().lower() != "yes":
            print("Aborted.")
            return

    tables = ["entries", "metrics", "categories", "units"]
    for t in tables:
        # PostgREST requires a WHERE clause for deletes; delete by id list instead.
        rows = sb.table(t).select("id").execute().data or []
        if not rows:
            print(f"No rows to delete in {t}")
            continue
        ids = [r["id"] for r in rows]
        res = sb.table(t).delete().in_("id", ids).execute()
        print(f"Deleted {len(ids)} rows from {t}")


def seed_sample():
    # Seed categories
    categories = [
        {"name": "body"},
        {"name": "performance"},
        {"name": "sleep"},
    ]
    res = sb.table("categories").insert(categories).execute()
    print("Inserted categories:", res.data)

    # Seed units
    units = [
        {"name": "kg", "unit_type": "float"},
        {"name": "lb", "unit_type": "float"},
        {"name": "reps", "unit_type": "int", "range_start": 0},
        {"name": "minutes", "unit_type": "int"},
    ]
    res = sb.table("units").insert(units).execute()
    print("Inserted units:", res.data)

    # Fetch IDs for relationships
    cats = {c["name"]: c["id"] for c in sb.table("categories").select("*").execute().data}
    uns = {u["name"]: u["id"] for u in sb.table("units").select("*").execute().data}

    # Seed metrics
    metrics = [
        {"name": "weight", "category_id": cats.get("body"), "unit_id": uns.get("kg")},
        {"name": "bench_press", "category_id": cats.get("performance"), "unit_id": uns.get("reps")},
        {"name": "sleep", "category_id": cats.get("sleep"), "unit_id": uns.get("minutes")},
    ]
    res = sb.table("metrics").insert(metrics).execute()
    print("Inserted metrics:", res.data)

    # Seed entries (some sample history for each metric)
    metrics_map = {m["name"]: m["id"] for m in sb.table("metrics").select("*").execute().data}

    today = date.today()
    entries = []
    # weight: last 7 days
    for i in range(7):
        entries.append({
            "metric_id": metrics_map.get("weight"),
            "value": 80 - i * 0.2,
            "recorded_at": (today - timedelta(days=i)).isoformat(),
        })

    # bench_press: 5 days
    for i in range(5):
        entries.append({
            "metric_id": metrics_map.get("bench_press"),
            "value": 5 + i,
            "recorded_at": (today - timedelta(days=i)).isoformat(),
        })

    # sleep: last 7 days
    for i in range(7):
        entries.append({
            "metric_id": metrics_map.get("sleep"),
            "value": 420 - i * 10,
            "recorded_at": (today - timedelta(days=i)).isoformat(),
        })

    res = sb.table("entries").insert(entries).execute()
    print("Inserted entries (sample):", len(res.data) if res.data else res)


def main():
    p = argparse.ArgumentParser(description="Dev helpers to purge/seed Supabase DB")
    p.add_argument("--purge", action="store_true", help="Delete all rows from tables")
    p.add_argument("--seed", action="store_true", help="Insert sample seed data")
    p.add_argument("--both", action="store_true", help="Purge then seed")
    p.add_argument("--yes", action="store_true", help="Skip interactive confirmation for destructive actions")
    args = p.parse_args()

    if args.both:
        purge_all(yes=args.yes)
        seed_sample()
        return

    if args.purge:
        purge_all(yes=args.yes)
    if args.seed:
        seed_sample()


if __name__ == "__main__":
    main()
