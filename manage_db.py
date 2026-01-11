"""
Unified Database Management Tool
Usage:
  python manage_db.py --reset           # Hard reset dev accounts (quatomix & testtom)
  python manage_db.py --seed --users a@b.com  # Seed specific users
  python manage_db.py --purge --users a@b.com # Wipe specific users
"""
import argparse
import psycopg2
from urllib.parse import urlparse
import streamlit as st
from datetime import datetime, timedelta
from supabase_config import sb_admin

# 1. Configuration & Connection
def get_db_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        project_ref = urlparse(url).hostname.split('.')[0]
        password = st.secrets["DB_PASSWORD"]
        db_url = f"postgresql://postgres:{password}@db.{project_ref}.supabase.co:5432/postgres"
        return psycopg2.connect(db_url)
    except Exception as e:
        print(f"❌ Connection Error: Ensure DB_PASSWORD is in secrets. {e}")
        return None

# 2. User ID Lookup
def get_user_id(email: str):
    try:
        res = sb_admin.auth.admin.list_users()
        user = next((u for u in res if u.email == email), None)
        return user.id if user else None
    except Exception:
        return None

# 3. High-Speed SQL Block (used for --reset)
def run_hard_reset():
    conn = get_db_connection()
    if not conn: return
    
    sql = """
    DO $$
    DECLARE
        user_ids uuid[] := ARRAY[
            '5de3f1fd-16ad-49c6-84f7-ad6c0f5d2daf',
            'ed2bb2a4-aa9d-44d5-bf9f-7a2d784c0fba'
        ]::uuid[];
        target_id uuid;
    BEGIN
        FOREACH target_id IN ARRAY user_ids LOOP
            DELETE FROM entries WHERE user_id = target_id;
            DELETE FROM metrics WHERE user_id = target_id;
            DELETE FROM categories WHERE user_id = target_id;

            INSERT INTO categories (name, user_id) VALUES 
                ('body', target_id), ('fitness', target_id), ('health', target_id);

            INSERT INTO metrics (name, description,unit_name, unit_type, range_start, range_end, category_id, user_id) VALUES 
                ('weight', 'Daily body mass tracking', 'kg', 'float', NULL, NULL, (SELECT id FROM categories WHERE name='body' AND user_id=target_id), target_id),
                ('floor press', 'Strength progress for chest press, 'kg', 'float', NULL, NULL, (SELECT id FROM categories WHERE name='fitness' AND user_id=target_id), target_id),
                ('sleep', 'Subjective restfulness score. 0 means no rest, 10 best sleep ever.', 'quality', 'integer_range', 0, 10, (SELECT id FROM categories WHERE name='health' AND user_id=target_id), target_id),
                ('yoga', 'Duration of daily yoga practice', 'minutes', 'integer', NULL, NULL, (SELECT id FROM categories WHERE name='fitness' AND user_id=target_id), target_id);

            INSERT INTO entries (metric_id, user_id, value, recorded_at)
            SELECT m.id, target_id, 
                (CASE 
                    WHEN m.name = 'weight' THEN random() * 10 + 75 
                    WHEN m.name = 'sleep' THEN floor(random() * 11)
                    ELSE random() * 20 + 20 
                END),
                (CURRENT_TIMESTAMP - (s.day || ' days')::interval)
            FROM metrics m CROSS JOIN generate_series(0, 6) AS s(day) WHERE m.user_id = target_id;
        END LOOP;
    END $$;
    """
    try:
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        print("✅ Hard reset complete for development accounts.")
    except Exception as e:
        print(f"❌ Error during reset: {e}")
    finally:
        conn.close()

# 4. Targeted API Operations (used for --users)
def purge_user(user_id, email):
    for table in ["entries", "metrics", "categories"]:
        sb_admin.table(table).delete().eq("user_id", user_id).execute()
    print(f"🗑️ Purged all data for {email}")

def seed_user(user_id, email):
    # Quick seed logic via API
    cat_res = sb_admin.table("categories").insert([{"name": "health", "user_id": user_id}]).execute()
    cat_id = cat_res.data[0]['id']
    sb_admin.table("metrics").insert({
        "name": "sleep", "description": "Subjective restfulness score. 0 means no rest, 10 best sleep ever.",
        "unit_name": "quality", "unit_type": "integer_range", 
        "range_start": 0, "range_end": 10, "category_id": cat_id, "user_id": user_id
    }).execute()
    print(f"🌱 Seeded basic metrics for {email}")

# 5. CLI Controller
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Hard reset dev accounts via SQL")
    parser.add_argument("--users", nargs="+", help="Email addresses for targeted actions")
    parser.add_argument("--purge", action="store_true")
    parser.add_argument("--seed", action="store_true")
    args = parser.parse_args()

    if args.reset:
        run_hard_reset()
    
    if args.users:
        for email in args.users:
            uid = get_user_id(email)
            if not uid:
                print(f"❌ User {email} not found.")
                continue
            if args.purge: purge_user(uid, email)
            if args.seed: seed_user(uid, email)

if __name__ == "__main__":
    main()