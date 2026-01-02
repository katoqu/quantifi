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
        if st.button("Prepare Export CSV", use_container_width=True):
            data = models.get_flat_export_data()
            if data:
                df = pd.DataFrame(data)
                df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
                csv = df.to_csv(index=False).encode('utf-8')
                models.save_backup_timestamp()
                st.download_button("📥 Download CSV", data=csv, file_name="backup.csv", mime="text/csv", use_container_width=True)
            else:
                st.info("No data found to export.")

    with col_imp:
        st.subheader("Rebuild / Import")
        uploaded_file = st.file_uploader("Upload a QuantifI backup CSV", type="csv")
        wipe_first = st.checkbox("🔥 Wipe database before import", value=False)
        
        if uploaded_file:
            _handle_import_logic(uploaded_file, wipe_first)

def _handle_import_logic(uploaded_file, wipe_first):
    try:
        df_import = pd.read_csv(uploaded_file)
        st.caption(f"Found {len(df_import)} entries in CSV.")
        
        # The Rebuild Button
        if st.button("🚀 Start Rebuild", type="primary", use_container_width=True):
            st.cache_data.clear() # Clear cache to ensure fresh IDs
            
            # FIXED: Log and Progress bar only appear AFTER the button is clicked
            log = st.container(height=250)
            progress_bar = st.progress(0)
            
            # 1. Atomic Wipe
            if wipe_first:
                log.write("🗑️ **Wiping existing database...**")
                models.wipe_user_data()
                log.write("✅ Database cleared.")
                time.sleep(1) # Wait for Supabase to sync

            # 2. Sync Schema (Categories & Metrics)
            log.write("🏗️ **Syncing Schema...**")
            unique_metrics = df_import[['Metric', 'Unit', 'Category']].drop_duplicates()
            
            for i, (_, row) in enumerate(unique_metrics.iterrows()):
                cat_name = str(row['Category']).strip()
                # Unified Category creation via utils helper
                target_cat_id = utils.ensure_category_id("NEW_CAT", cat_name) if cat_name.lower() not in ["none", "nan", ""] else None
                
                met_name = str(row['Metric']).strip().lower()
                if not models.get_metric_by_name(met_name):
                    models.create_metric({
                        "name": met_name,
                        "unit_name": str(row['Unit']).lower() if pd.notna(row['Unit']) else None,
                        "category_id": target_cat_id,
                        "unit_type": "float" 
                    })
                progress_bar.progress((i + 1) / len(unique_metrics) * 0.3)

            # 3. Import Entries
            log.write("📝 **Importing Entries...**")
            all_metrics = models.get_metrics()
            metrics_lookup = {m['name'].lower().strip(): m['id'] for m in all_metrics}
            
            success_count = 0
            for i, (_, row) in enumerate(df_import.iterrows()):
                m_id = metrics_lookup.get(str(row['Metric']).strip().lower())
                if m_id:
                    # Standardize date using midday timestamp
                    raw_date = pd.to_datetime(row['Date'])
                    formatted_date = utils.to_datetz(raw_date.date()).isoformat()
                    
                    models.create_entry({
                        "metric_id": m_id,
                        "value": float(row['Value']),
                        "recorded_at": formatted_date
                    })
                    success_count += 1
                progress_bar.progress(0.3 + (i / len(df_import) * 0.7))
            
            st.success(f"Import complete: {success_count} entries synced.")
            st.cache_data.clear()
            st.rerun()
            
    except Exception as e:
        st.error(f"Critical Importer Error: {e}")