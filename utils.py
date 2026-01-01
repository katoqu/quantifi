import pandas as pd
import models
import datetime as dt

def normalize_name(name: str):
    """Standardizes names for database storage."""
    return name.strip().lower()

def format_metric_label(metric, unit_map=None):
    """
    Refactored: Now pulls unit_name directly from the metric object.
    The unit_map parameter is kept as an optional None for backward compatibility 
    during the transition but is no longer used.
    """
    name = metric.get("name", "").title()
    # Direct access instead of dictionary lookup
    unit = metric.get("unit_name", "").title()
    return f"{name} ({unit})" if unit else name

def collect_data(selected_metric, unit_meta=None):
    """
    Fetches entries for a metric and extracts unit/name metadata 
    directly from the metric object.
    """
    mid = selected_metric.get("id")
    m_name = selected_metric.get("name", "Metric").title()
    # Pull unit directly from the metric record
    m_unit = selected_metric.get("unit_name", "") 

    entries = models.get_entries(metric_id=mid)
    
    if not entries:
        return pd.DataFrame(), m_unit, m_name
        
    dfe = pd.DataFrame(entries)
    dfe["recorded_at"] = pd.to_datetime(dfe["recorded_at"])
    dfe = dfe.sort_values("recorded_at")
    
    return dfe, m_unit, m_name

def to_datetz(date_obj):
    """Converts a date object to a datetime with a basic timestamp."""
    return dt.datetime.combine(date_obj, dt.time(12, 0))