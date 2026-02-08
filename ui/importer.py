# importer.py
import streamlit as st
import pandas as pd
import models
import utils
import time
import auth
from datetime import datetime

ALLOWED_TYPES = ["float", "integer", "integer_range"]
ALLOWED_KINDS = ["quantitative", "count", "score"]


def parse_import_frames(df_import: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Splits an import CSV into:
    - df_entries: metric entry rows (RowType='entry')
    - df_changes: lifestyle change rows (RowType='change')

    Backward compatible: if RowType is missing, all rows are treated as entries.
    """
    df = df_import.copy()
    if "RowType" not in df.columns:
        df["RowType"] = "entry"
    df["RowType"] = (
        df["RowType"]
        .fillna("entry")
        .astype(str)
        .str.strip()
        .str.lower()
        .replace({"": "entry"})
    )
    df_entries = df[df["RowType"] == "entry"].copy()
    df_changes = df[df["RowType"] == "change"].copy()
    return df_entries, df_changes


def validate_import_frames(df_entries: pd.DataFrame, df_changes: pd.DataFrame) -> list[str]:
    """
    Validates entry/change rows without touching Streamlit or Supabase.
    Returns a list of human-readable error strings.
    """
    errors: list[str] = []

    if df_entries is not None and not df_entries.empty:
        required_cols = ["Metric", "Value", "Date", "Type", "Archived"]
        missing = [c for c in required_cols if c not in df_entries.columns]
        if missing:
            errors.append(f"Missing mandatory columns for entries: {', '.join(missing)}")
        else:
            for idx, row in df_entries.iterrows():
                row_num = idx + 2
                m_name = str(row.get("Metric", "Unknown"))

                m_type = str(row.get("Type")).strip().lower()
                if m_type not in ALLOWED_TYPES:
                    errors.append(
                        f"Row {row_num}: Invalid Type '{m_type}'. Must be one of {ALLOWED_TYPES}"
                    )

                if "Kind" in df_entries.columns and pd.notna(row.get("Kind")):
                    m_kind = str(row.get("Kind")).strip().lower()
                    if m_kind and m_kind not in ALLOWED_KINDS:
                        errors.append(
                            f"Row {row_num}: Invalid Kind '{m_kind}'. Must be one of {ALLOWED_KINDS}"
                        )

                if m_type == "integer_range":
                    try:
                        v_min = float(row["Min"]) if pd.notna(row.get("Min")) else None
                        v_max = float(row["Max"]) if pd.notna(row.get("Max")) else None
                        if v_min is None or v_max is None:
                            errors.append(
                                f"Row {row_num}: Metric '{m_name}' is a range but missing Min/Max."
                            )
                        elif v_min >= v_max:
                            errors.append(
                                f"Row {row_num}: Min ({v_min}) must be less than Max ({v_max})."
                            )
                    except ValueError:
                        errors.append(
                            f"Row {row_num}: Min/Max for '{m_name}' must be numbers."
                        )

                v = row.get("Value")
                if pd.notna(v) and str(v).strip() != "":
                    try:
                        float(v)
                    except (TypeError, ValueError):
                        errors.append(f"Row {row_num}: Value '{v}' is not a valid number.")

    if df_changes is not None and not df_changes.empty:
        required_cols = ["Title", "Date"]
        missing = [c for c in required_cols if c not in df_changes.columns]
        if missing:
            errors.append(f"Missing mandatory columns for changes: {', '.join(missing)}")
        else:
            for idx, row in df_changes.iterrows():
                row_num = idx + 2
                title = str(row.get("Title") or "").strip()
                if not title:
                    errors.append(f"Row {row_num}: Change Title cannot be empty.")
                raw_date = row.get("Date")
                if pd.isna(raw_date) or str(raw_date).strip() == "":
                    errors.append(f"Row {row_num}: Change Date cannot be empty.")

    return errors


@st.fragment
def show_data_lifecycle_management():
    st.header("Backup & Recovery")
    col_exp, col_imp = st.columns(2)
    
    with col_exp:
        st.subheader("Export Data")
        if st.button("Prepare Enhanced Export CSV", use_container_width=True):
            data = models.get_flat_export_data()
            if data:
                df = pd.DataFrame(data)
                # Standardize Date format
                df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d %H:%M:%S')
                csv = df.to_csv(index=False).encode('utf-8')
                user = auth.get_current_user()
                username = user.email.split('@')[0] if user else "user"
                datestr = datetime.now().strftime('%Y-%m-%d')

                fname = f"quantifi_backup_{username}_{datestr}.csv"
                models.save_backup_timestamp()
                st.download_button("📥 Download CSV", data=csv, file_name= fname,
                                    mime="text/csv", use_container_width=True)
            else:
                st.info("No data found to export.")

    with col_imp:
        st.subheader("Rebuild / Import")
        uploaded_file = st.file_uploader("Upload Enhanced CSV", type="csv")
        wipe_first = st.checkbox("🔥 Wipe database before import", value=False)
        
        if uploaded_file:
            _handle_import_logic(uploaded_file, wipe_first)

    st.divider()
    # Add the template downloader at the bottom
    _render_template_downloader()

def _handle_import_logic(uploaded_file, wipe_first):
    try:
        df_import = pd.read_csv(uploaded_file)
        df_entries, df_changes = parse_import_frames(df_import)
        st.caption(
            f"Found {len(df_import)} rows: {len(df_entries)} entries, {len(df_changes)} changes."
        )
        
        # --- 1. PRE-VALIDATION / DRY RUN ---
        errors = validate_import_frames(df_entries, df_changes)

        if errors:
            st.error("❌ **Dry Run Failed: Import Aborted.**")
            with st.expander("View Validation Errors", expanded=True):
                for err in errors:
                    st.write(f"- {err}")
            return

        # --- 2. EXECUTION PHASE (Only reached if Dry Run passes) ---
        if st.button("🚀 Start Rebuild", type="primary", use_container_width=True):
            st.cache_data.clear() 
            log = st.container(height=300)
            progress_bar = st.progress(0)
            
            if wipe_first:
                log.write("🗑️ **Wiping existing database...**")
                models.wipe_user_data() 
                log.write("✅ Database cleared.")
                time.sleep(1)

            if not df_entries.empty:
                log.write("🏗️ **Syncing Schema...**")
            schema_cols = ['Metric', 'Description', 'Unit', 'Category', 'Type', 'Min', 'Max', 'Archived']
            # Fill missing metadata with defaults
            for col in ['Description', 'Unit', 'Category', 'Min', 'Max', 'Archived', 'Kind', 'HigherIsBetter']:
                if col not in df_entries.columns:
                    df_entries[col] = None
            
            unique_metrics = df_entries[schema_cols].drop_duplicates() if not df_entries.empty else pd.DataFrame()
            
            for i, (_, row) in enumerate(unique_metrics.iterrows()):
                met_name = str(row['Metric']).strip().lower()
                if not models.get_metric_by_name(met_name):
                    m_type = str(row['Type']).strip().lower()
                    if pd.notna(row.get("Kind")):
                        m_kind = str(row.get("Kind")).strip().lower()
                    else:
                        m_kind = "score" if m_type == "integer_range" else ("count" if m_type == "integer" else "quantitative")

                    # Keep `unit_type` aligned to kind for consistent behavior.
                    if m_kind == "score":
                        m_type = "integer_range"
                    elif m_kind == "count":
                        m_type = "integer"
                    else:
                        m_type = "float"

                    payload = {
                        "name": met_name,
                        "description": str(row['Description']) if pd.notna(row['Description']) else None,
                        "is_archived": bool(row['Archived']) if pd.notna(row['Archived']) else False,
                        "unit_name": str(row['Unit']).lower() if pd.notna(row['Unit']) else None,
                        "category_id": utils.ensure_category_id("NEW_CAT", str(row['Category'])) if pd.notna(row['Category']) else None,
                        "unit_type": m_type,
                        "metric_kind": m_kind,
                        "range_start": int(row['Min']) if pd.notna(row['Min']) else None,
                        "range_end": int(row['Max']) if pd.notna(row['Max']) else None
                    }
                    if pd.notna(row.get("HigherIsBetter")):
                        payload["higher_is_better"] = bool(row.get("HigherIsBetter"))
                    res = models.create_metric(payload)
                    if not res:
                        st.error(f"Failed to create metric: {met_name}. Aborting.")
                        return 

            success_entries = 0
            success_changes = 0
            total_rows = max(1, len(df_entries) + len(df_changes))

            if not df_entries.empty:
                log.write("📝 **Importing Entries...**")
                all_metrics = models.get_metrics()
                metrics_lookup = {m['name'].lower().strip(): m['id'] for m in all_metrics}

                for i, (_, row) in enumerate(df_entries.iterrows()):
                    m_id = metrics_lookup.get(str(row["Metric"]).strip().lower())
                    if m_id:
                        formatted_date = pd.to_datetime(row["Date"]).isoformat()
                        raw_val = row.get("Value")
                        if pd.isna(raw_val) or str(raw_val).strip() == "":
                            val = None
                        else:
                            val = float(raw_val)
                        payload = {"metric_id": m_id, "value": val, "recorded_at": formatted_date}
                        if "Target" in df_entries.columns and pd.notna(row.get("Target")) and str(row.get("Target")).strip():
                            payload["target_action"] = str(row.get("Target")).strip()
                        models.create_entry(payload)
                        success_entries += 1
                    progress_bar.progress((i + 1) / total_rows)

            if not df_changes.empty:
                log.write("📝 **Importing Changes...**")
                for j, (_, row) in enumerate(df_changes.iterrows()):
                    formatted_date = pd.to_datetime(row["Date"]).isoformat()
                    title = str(row.get("Title") or "").strip()
                    notes = str(row.get("Notes") or "").strip()
                    cat_name = row.get("Category")
                    cat_id = None
                    if pd.notna(cat_name) and str(cat_name).strip():
                        cat_id = utils.ensure_category_id("NEW_CAT", str(cat_name))
                    models.create_change_event(
                        {
                            "title": title,
                            "notes": (notes if notes else None),
                            "category_id": cat_id,
                            "recorded_at": formatted_date,
                        }
                    )
                    success_changes += 1
                    progress_bar.progress((len(df_entries) + j + 1) / total_rows)
            

            # Use the mobile-optimized toast and refresh from utils
            utils.finalize_action(
                message=f"Rebuild complete: {success_entries} entries, {success_changes} changes synced.",
                icon="🚀",
                delay=2 # Slightly longer delay to let the user read the count
            )

    except Exception as e:
        st.error(f"Critical Importer Error: {e}")

def _render_template_downloader():
    """Generates a CSV template based on current metric definitions."""
    st.subheader("Manual Data Entry")
    st.markdown("Use this template to format your data correctly for import.")
    
    # 1. Fetch current metrics to build a pre-filled schema
    metrics_list = models.get_metrics()
    
    if metrics_list:
        template_rows = []
        for m in metrics_list:
            # We fetch category name via models/utils if needed, 
            # or just use None for a blank template.
            template_rows.append({
                "RowType": "entry",
                "Metric": m['name'],
                "Description": m.get('description', ''),
                "Archived": m.get('is_archived', False),
                "Value": "",
                "Date": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                "Unit": m.get('unit_name', ''),
                "Category": "", # User fills this or we look up cat name
                "Type": m.get('unit_type', 'float'),
                "Kind": m.get('metric_kind', ''),
                "Min": m.get('range_start', ''),
                "Max": m.get('range_end', '')
                ,
                "HigherIsBetter": m.get("higher_is_better", True),
                "Title": "",
                "Notes": "",
            })
        
        df_template = pd.DataFrame(template_rows)
        csv_template = df_template.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label="📝 Download Import Template",
            data=csv_template,
            file_name="quantifi_template.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("Create at least one metric to generate a template.")
