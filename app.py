import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client
from datetime import datetime, timezone, time
from zoneinfo import ZoneInfo

SUPABASE_URL = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
USER_TZ = ZoneInfo("Europe/London")  # example user timezone      

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("Simple Metric Tracker")

def fetch(table: str):
    res = sb.table(table).select("*").execute()
    return res.data or []

st.markdown("Manage lookup values (categories & units) and create metrics below.")

with st.expander("Manage categories", expanded=False):
        new_cat = st.text_input("New category")
        if st.button("Add category") and new_cat.strip():
            name_norm = new_cat.strip().lower()
            existing = sb.table("categories").select("id,name").execute().data or []
            if any(c["name"].lower() == name_norm for c in existing):
                st.info("Category already exists (case-insensitive)")
            else:
                sb.table("categories").insert({"name": name_norm}).execute()
                st.success("Category added")

with st.expander("Manage units", expanded=False):
        new_unit = st.text_input("New unit")
        # allow specifying unit type and optional integer range
        unit_type = st.selectbox("Unit type", ("float", "integer", "integer range"))
        range_start = None
        range_end = None
        if unit_type == "integer range":
            col1, col2 = st.columns(2)
            with col1:
                range_start = st.number_input("Range start", step=1)
            with col2:
                range_end = st.number_input("Range end", step=1)

        if st.button("Add unit") and new_unit.strip():
            name_norm = new_unit.strip().lower()
            existing = sb.table("units").select("id,name").execute().data or []
            if any(u["name"].lower() == name_norm for u in existing):
                st.info("Unit already exists (case-insensitive)")
            else:
                payload = {"name": name_norm, "unit_type": ("integer_range" if unit_type == "integer range" else unit_type)}
                if range_start is not None and range_end is not None:
                    payload["range_start"] = int(range_start)
                    payload["range_end"] = int(range_end)
                sb.table("units").insert(payload).execute()
                st.success("Unit added")

        # show existing units with type/range
        units_list = sb.table("units").select("*").order("name", desc=False).execute().data or []
        if units_list:
            rows = []
            for u in units_list:
                name = u.get("name", "").title()
                utype = u.get("unit_type", "float")
                if utype == "integer_range":
                    rs = u.get("range_start")
                    re = u.get("range_end")
                    range_str = f"{rs} - {re}" if rs is not None or re is not None else ""
                else:
                    range_str = ""
                rows.append({"name": name, "type": utype, "range": range_str})
            try:
                df_units = pd.DataFrame(rows)
                st.dataframe(df_units)
            except Exception:
                st.write(rows)


# Fetch lookup lists
cats = fetch("categories")
units = fetch("units")
# display names in Title Case while storing them lowercase in DB
cat_options = [(None, "— none —")] + [(c["id"], c["name"].title()) for c in cats]
unit_options = [(None, "— none —")] + [(u["id"], u["name"].title()) for u in units]


with st.expander("Add metric"):
    mn = st.text_input("Metric name")
    # category selectbox showing names but returning id
    cat_choice = st.selectbox("Category", [o[0] for o in cat_options], format_func=lambda i: next((n for (_id, n) in cat_options if _id == i), "— none —"))
    unit_choice = st.selectbox("Unit", [o[0] for o in unit_options], format_func=lambda i: next((n for (_id, n) in unit_options if _id == i), "— none —"))
    if st.button("Create metric") and mn.strip():
        name_norm = mn.strip().lower()
        existing_metrics = fetch("metrics")
        if any(m.get("name", "").lower() == name_norm for m in existing_metrics):
            st.info("Metric already exists (case-insensitive)")
        else:
            payload = {"name": name_norm}
            if cat_choice:
                payload["category_id"] = cat_choice
            if unit_choice:
                payload["unit_id"] = unit_choice
            sb.table("metrics").insert(payload).execute()
            st.success("Metric created")


# Select metric
metrics = fetch("metrics")
metric_id = None
selected_metric = None
if metrics:
    # build lookup maps (display Title Case names) and keep unit metadata
    cat_map = {c["id"]: c["name"].title() for c in cats}
    unit_map = {u["id"]: u["name"].title() for u in units}
    unit_meta = {u["id"]: u for u in units}

    def metric_label(m):
        name = m.get("name")
        display_name = name.title() if isinstance(name, str) else name
        unit = unit_map.get(m.get("unit_id"))
        if unit:
            return f"{display_name} ({unit})"
        return display_name

    metric_idx = st.selectbox("Metric", options=list(range(len(metrics))), format_func=lambda i: metric_label(metrics[i]))
    selected_metric = metrics[metric_idx]
    metric_id = selected_metric["id"]

    # Add entry
    with st.form("entry"):
        # show hint about unit type (if any)
        selected_unit = unit_meta.get(selected_metric.get("unit_id")) if unit_meta else None
        if selected_unit:
            utype = selected_unit.get("unit_type", "float")
            if utype == "integer":
                st.caption("Unit expects integer values")
            elif utype == "integer_range":
                rs = selected_unit.get("range_start")
                re = selected_unit.get("range_end")
                st.caption(f"Unit expects integer values in range [{rs}, {re}]")

        val = st.number_input("Value", format="%.1f")
        date = st.date_input("Recorded date")
        datetz = datetime.combine(date, time.min, tzinfo=USER_TZ)
        submitted = st.form_submit_button("Add entry")
        if submitted:
            # validate against unit type if provided
            valid = True
            if selected_unit:
                utype = selected_unit.get("unit_type", "float")
                if utype == "integer":
                    if not float(val).is_integer():
                        st.error("Value must be an integer for this unit")
                        valid = False
                    else:
                        val = int(val)
                elif utype == "integer_range":
                    if not float(val).is_integer():
                        st.error("Value must be an integer for this unit")
                        valid = False
                    else:
                        ival = int(val)
                        rs = selected_unit.get("range_start")
                        re = selected_unit.get("range_end")
                        try:
                            if rs is not None and ival < int(rs):
                                st.error(f"Value must be >= {rs}")
                                valid = False
                            if re is not None and ival > int(re):
                                st.error(f"Value must be <= {re}")
                                valid = False
                        except ValueError:
                            st.error("Invalid stored unit range configuration")
                            valid = False
                        if valid:
                            val = ival

            if valid:
                sb.table("entries").insert({"metric_id": metric_id, "value": val, "recorded_at": datetz.isoformat()}).execute()
                st.success("Entry added")

# Show entries and plot
if metric_id:
    entries = sb.table("entries").select("*").eq("metric_id", metric_id).order("recorded_at", desc=False).execute().data or []
else:
    entries = []

dfe = pd.DataFrame(entries)

if not dfe.empty:
    dfe["recorded_at"] = pd.to_datetime(dfe["recorded_at"])
    y_col = unit_map.get(selected_metric.get("unit_id"), "value")
    
    # 1. Create scatter with built-in OLS trendline (Ordinary Least Squares)
    # Requires 'statsmodels' library installed: pip install statsmodels
    fig = px.scatter(
        dfe, x="recorded_at", y="value", 
        trendline="ols",
        title="Time course",
        labels={"recorded_at": "Recorded date", "value": y_col}
    )

    # 2. Add horizontal average line
    y_avg = dfe["value"].mean()
    fig.add_hline(y=y_avg, line_dash="dash", line_color="gray", annotation_text="Average")

    # 3. Final styling
    fig.update_xaxes(tickformat="%b %d, %Y")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No entries yet for this metric.")