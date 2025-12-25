"""Development helper: purge and seed the Supabase DB for specific users.

Usage:
  python dev_db.py --purge --user test@example.com
  python dev_db.py --seed --user test1@example.com test2@example.com
"""
from datetime import date, timedelta
import argparse
import sys
from supabase_config import sb_admin

def get_user_id(email: str):
    """Fetch the UUID for a given email from Supabase Auth."""
    # Note: Requires service_role key if fetching other users, 
    # or admin privileges depending on your client setup.
    try:
        res = sb_admin.auth.admin.list_users()
        user = next((u for u in res if u.email == email), None)
        if not user:
            print(f"Error: User with email {email} not found.")
            return None
        return user.id
    except Exception as e:
        print(f"Auth Error: Ensure you are using the Service Role Key to list users. {e}")
        return None

def purge_user_data(user_id: str, email: str, yes: bool = False):
    if not yes:
        confirm = input(f"DELETE ALL DATA for user {email}? Type 'yes': ")
        if confirm.strip().lower() != "yes":
            return

    tables = ["entries", "metrics", "categories", "units"]
    for t in tables:
        # Delete only rows belonging to this user
        res = sb_admin.table(t).delete().eq("user_id", user_id).execute()
        print(f"Deleted {len(res.data) if res.data else 0} rows from {t} for {email}")

def seed_sample(user_id: str, email: str):
    print(f"Seeding data for {email}...")

    # 1. Seed categories
    categories = [
        {"name": "body", "user_id": user_id},
        {"name": "fitness", "user_id": user_id},
        {"name": "health", "user_id": user_id},
    ]
    sb_admin.table("categories").insert(categories).execute()

    # 2. Seed units
    units = [
        {"name": "kg", "unit_type": "float", "user_id": user_id},
        {"name": "quality", "unit_type": "int", "range_start": 0, "range_end": 10, "user_id": user_id},
        {"name": "reps", "unit_type": "int", "range_start": 0, "user_id": user_id},
        {"name": "minutes", "unit_type": "int", "user_id": user_id},
    ]
    sb_admin.table("units").insert(units).execute()

    # Fetch IDs (filtered by user) to maintain relationships
    cats = {c["name"]: c["id"] for c in sb_admin.table("categories").select("*").eq("user_id", user_id).execute().data}
    uns = {u["name"]: u["id"] for u in sb_admin.table("units").select("*").eq("user_id", user_id).execute().data}

    # 3. Seed metrics
    metrics = [
        {"name": "weight", "category_id": cats.get("body"), "unit_id": uns.get("kg"), "user_id": user_id},
        {"name": "floor press", "category_id": cats.get("fitness"), "unit_id": uns.get("kg"), "user_id": user_id},
        {"name": "sleep", "category_id": cats.get("health"), "unit_id": uns.get("quality"), "user_id": user_id},
        {"name": "yoga", "category_id": cats.get("fitness"), "unit_id": uns.get("minutes"), "user_id": user_id}        
    ]
    sb_admin.table("metrics").insert(metrics).execute()

    # 4. Seed entries
    metrics_map = {m["name"]: m["id"] for m in sb_admin.table("metrics").select("*").eq("user_id", user_id).execute().data}
    today = date.today()
    entries = []
    
    # Generic loop to generate history
    sample_configs = [("weight", 7, 80), ("floor press", 10, 20), ("sleep", 7, 8), ("yoga", 5, 30)]
    
    for m_name, days, start_val in sample_configs:
        m_id = metrics_map.get(m_name)
        for i in range(days):
            entries.append({
                "user_id": user_id,
                "metric_id": m_id,
                "value": start_val + (i * 0.5),
                "recorded_at": (today - timedelta(days=i)).isoformat(),
            })

    res = sb_admin.table("entries").insert(entries).execute()
    print(f"Successfully seeded {len(res.data)} entries for {email}")


def main():
    p = argparse.ArgumentParser(description="Multi-user Dev helpers for Supabase")
    p.add_argument("--users", nargs="+", required=True, help="Emails of users to process")
    p.add_argument("--purge", action="store_true", help="Delete user data")
    p.add_argument("--seed", action="store_true", help="Seed user data")
    p.add_argument("--yes", action="store_true", help="Skip confirmation")
    args = p.parse_args()

    for email in args.users:
        uid = get_user_id(email)
        if not uid:
            continue
        
        if args.purge:
            purge_user_data(uid, email, yes=args.yes)
        if args.seed:
            seed_sample(uid, email)

if __name__ == "__main__":
    main()
