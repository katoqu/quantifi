import supabase_client as sc

def get_categories():
    return sc.fetch("categories")

def get_units():
    return sc.fetch("units")

def get_metrics():
    return sc.fetch("metrics")

def get_entries(metric_id=None):
    entries = sc.fetch("entries")
    if metric_id:
        return [e for e in entries if e.get("metric_id") == metric_id]
    return entries

def create_category(name: str):
    return sc.insert("categories", {"name": name})

def create_unit(payload: dict):
    return sc.insert("units", payload)

def create_metric(payload: dict):
    return sc.insert("metrics", payload)

def create_entry(payload: dict):
    return sc.insert("entries", payload)
