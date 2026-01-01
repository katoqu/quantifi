import streamlit as st
import pandas as pd
import models
import utils
import time

def show_data_lifecycle_management():
    """
    Handles Export, Wipe, and Rebuild logic with robust error handling 
    for cached data and database synchronization.
    """
    st.divider()
    st.header("💾 Data Management & Backups")
    
    col_exp, col_imp = st.columns(2)
    
    # --- SECTION 1: EXPORT ---
    with col_exp:
        st.subheader("Export Data")
        st.write("Save your entire history to a flat CSV file.")
        
        if st.button("Prepare Export CSV", use_container_width=True):
            data = models.get_flat_export_data()
            if data:
                df = pd.DataFrame(data)
                # Normalize date format for clean export
                df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
                
                csv = df.to_csv(index=False).encode('utf-8')

                # Save the timestamp
                models.save_backup_timestamp()
 
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"quantifi_backup_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.info("No data found to export.")

    # --- SECTION 2: REBUILD / IMPORT ---
    with col_imp:
        st.subheader("Rebuild / Import")
        uploaded_file = st.file_uploader("Upload a QuantifI backup CSV", type="csv")
        
        # Danger Zone Toggle
        wipe_first = st.checkbox("🔥 Wipe existing data before import", value=False)
        
        if uploaded_file:
            try:
                df_import = pd.read_csv(uploaded_file)
                st.caption(f"Found {len(df_import)} entries in CSV.")
                
                if st.button("🚀 Start Rebuild", type="primary", use_container_width=True):
                    # 1. CRITICAL: Clear all streamlit cache immediately
                    # This ensures the importer doesn't use old versions of get_metrics()
                    st.cache_data.clear()
                    
                    # Setup Logging and Progress UI
                    log = st.container(height=250)
                    progress_bar = st.progress(0)
                    
                    # Counters for Summary
                    cats_created = 0
                    metrics_created = 0
                    entries_success = 0
                    entries_failed = 0
                    
                    # 2. Optional Wipe
                    if wipe_first:
                        log.write("🗑️ **Wiping existing database...**")
                        models.wipe_user_data()
                        log.write("✅ Database cleared.")
                    
                    # 3. STEP 1: Sync Schema (Categories & Metrics)
                    log.write("🏗️ **Syncing Schema...**")
                    unique_metrics = df_import[['Metric', 'Unit', 'Category']].drop_duplicates()
                    
                    for i, (_, row) in enumerate(unique_metrics.iterrows()):
                        # Process Category
                        cat_name = str(row['Category']).strip()
                        cat = None
                        if cat_name.lower() not in ["none", "nan", ""]:
                            cat = models.get_category_by_name(cat_name)
                            if not cat:
                                models.create_category(cat_name)
                                cat = models.get_category_by_name(cat_name)
                                cats_created += 1
                                log.write(f"📁 Created Category: `{cat_name}`")
                        
                        # Process Metric
                        met_name = str(row['Metric']).strip().lower()
                        metric = models.get_metric_by_name(met_name)
                        if not metric:
                            models.create_metric({
                                "name": met_name,
                                "unit_name": str(row['Unit']).lower() if pd.notna(row['Unit']) else None,
                                "category_id": cat['id'] if cat else None,
                                "unit_type": "float" 
                            })
                            metrics_created += 1
                            log.write(f"📊 Created Metric: `{met_name}`")
                        
                        progress_bar.progress((i + 1) / len(unique_metrics) * 0.3)

                    # 4. STEP 2: THE CRITICAL SYNC BUFFER
                    log.write("🔄 **Synchronizing with Database...**")
                    time.sleep(1)      # Give Supabase time to update indices
                    st.cache_data.clear() # Clear cache again for the final ID lookup
                    
                    # Refresh ID lookup
                    all_metrics = models.get_metrics()
                    metrics_lookup = {m['name'].lower().strip(): m['id'] for m in all_metrics}
                    
                    # 5. STEP 3: Import Historical Entries
                    log.write(f"📝 **Importing {len(df_import)} Entries...**")
                    df_import['Date'] = pd.to_datetime(df_import['Date']).dt.strftime('%Y-%m-%d')
                    total_rows = len(df_import)
                    
                    for i, (_, row) in enumerate(df_import.iterrows()):
                        m_name_norm = str(row['Metric']).strip().lower()
                        m_id = metrics_lookup.get(m_name_norm)
                        
                        if m_id:
                            try:
                                models.create_entry({
                                    "metric_id": m_id,
                                    "value": float(row['Value']),
                                    "recorded_at": row['Date']
                                })
                                entries_success += 1
                            except Exception as e:
                                log.write(f"⚠️ Row {i} Error: {e}")
                                entries_failed += 1
                        else:
                            log.write(f"❌ Error: Metric ID missing for `{m_name_norm}`")
                            entries_failed += 1
                        
                        if i % 10 == 0 or i == total_rows - 1:
                            progress_bar.progress(0.3 + (i / total_rows * 0.7))
                    
                    # 6. Final Summary
                    st.markdown("---")
                    st.subheader("🏁 Rebuild Summary")
                    s_col1, s_col2, s_col3 = st.columns(3)
                    s_col1.metric("Categories Created", cats_created)
                    s_col2.metric("Metrics Created", metrics_created)
                    s_col3.metric("Entries Imported", entries_success)
                    
                    if entries_failed > 0:
                        st.warning(f"Note: {entries_failed} entries failed to import. See log for details.")
                    
                    st.cache_data.clear()
                    if st.button("Finish & Refresh Dashboard"):
                        st.rerun()
                        
            except Exception as e:
                st.error(f"Critical Importer Error: {e}")