# importer.py
import streamlit as st
import pandas as pd
import models
import utils
import time

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
                models.save_backup_timestamp()
                st.download_button("📥 Download CSV", data=csv, file_name="quantifi_backup.csv", mime="text/csv", use_container_width=True)
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
        st.caption(f"Found {len(df_import)} entries in CSV.")
        
        # --- 1. PRE-VALIDATION / DRY RUN ---
        errors = []
        ALLOWED_TYPES = ['float', 'integer', 'integer_range'] # Added strict whitelist
        
        # Check for mandatory columns
        required_cols = ['Metric', 'Value', 'Date', 'Type']
        missing = [c for c in required_cols if c not in df_import.columns]
        if missing:
            errors.append(f"Missing mandatory columns: {', '.join(missing)}")
        
        if not errors:
            for idx, row in df_import.iterrows():
                row_num = idx + 2 # Header + 0-index offset
                m_name = str(row.get('Metric', 'Unknown'))

                # A. Validate Type Whitelist
                m_type = str(row.get('Type')).strip().lower()
                if m_type not in ALLOWED_TYPES:
                    errors.append(f"Row {row_num}: Invalid Type '{m_type}'. Must be one of {ALLOWED_TYPES}")

                # B. Validate integer_range specific logic
                if m_type == 'integer_range':
                    try:
                        v_min = float(row['Min']) if pd.notna(row['Min']) else None
                        v_max = float(row['Max']) if pd.notna(row['Max']) else None
                        
                        if v_min is None or v_max is None:
                            errors.append(f"Row {row_num}: Metric '{m_name}' is a range but missing Min/Max.")
                        elif v_min >= v_max:
                            errors.append(f"Row {row_num}: Min ({v_min}) must be less than Max ({v_max}).")
                    except ValueError:
                        errors.append(f"Row {row_num}: Min/Max for '{m_name}' must be numbers.")

                # C. Validate Value column (ensure it's numeric)
                try:
                    float(row['Value'])
                except ValueError:
                    errors.append(f"Row {row_num}: Value '{row['Value']}' is not a valid number.")

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

            log.write("🏗️ **Syncing Schema...**")
            schema_cols = ['Metric', 'Unit', 'Category', 'Type', 'Min', 'Max']
            # Fill missing metadata with defaults
            for col in ['Unit', 'Category', 'Min', 'Max']:
                if col not in df_import.columns: df_import[col] = None
            
            unique_metrics = df_import[schema_cols].drop_duplicates()
            
            for i, (_, row) in enumerate(unique_metrics.iterrows()):
                met_name = str(row['Metric']).strip().lower()
                if not models.get_metric_by_name(met_name):
                    payload = {
                        "name": met_name,
                        "unit_name": str(row['Unit']).lower() if pd.notna(row['Unit']) else None,
                        "category_id": utils.ensure_category_id("NEW_CAT", str(row['Category'])) if pd.notna(row['Category']) else None,
                        "unit_type": str(row['Type']).strip().lower(),
                        "range_start": int(row['Min']) if pd.notna(row['Min']) else None,
                        "range_end": int(row['Max']) if pd.notna(row['Max']) else None
                    }
                    res = models.create_metric(payload)
                    if not res:
                        st.error(f"Failed to create metric: {met_name}. Aborting.")
                        return 

            log.write("📝 **Importing Entries...**")
            all_metrics = models.get_metrics()
            metrics_lookup = {m['name'].lower().strip(): m['id'] for m in all_metrics}
            
            success_count = 0
            for i, (_, row) in enumerate(df_import.iterrows()):
                m_id = metrics_lookup.get(str(row['Metric']).strip().lower())
                if m_id:
                    formatted_date = pd.to_datetime(row['Date']).isoformat()
                    models.create_entry({
                        "metric_id": m_id,
                        "value": float(row['Value']),
                        "recorded_at": formatted_date
                    })
                    success_count += 1
                progress_bar.progress(0.3 + (i / len(df_import) * 0.7))
            

            # Use the mobile-optimized toast and refresh from utils
            utils.finalize_action(
                message=f"Rebuild complete: {success_count} entries synced.",
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
                "Metric": m['name'],
                "Value": 0.0,
                "Date": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                "Unit": m.get('unit_name', ''),
                "Category": "", # User fills this or we look up cat name
                "Type": m.get('unit_type', 'float'),
                "Min": m.get('range_start', ''),
                "Max": m.get('range_end', '')
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