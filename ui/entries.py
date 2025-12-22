import streamlit as st
import pandas as pd
import plotly.express as px
import models
import utils

def show_entry_form(selected_metric, unit_meta):
    if not selected_metric:
        return
    metric_id = selected_metric.get("id")
    selected_unit = unit_meta.get(selected_metric.get("unit_id")) if unit_meta else None

    with st.form("entry"):
        if selected_unit:
            utype = selected_unit.get("unit_type", "float")
            if utype == "integer":
                st.caption("Unit expects integer values")
            elif utype == "integer_range":
                rs = selected_unit.get("range_start")
                re = selected_unit.get("range_end")
                st.caption(f"Unit expects integer values in range [{rs}, {re}]")

        val = st.number_input("Value", format="%.3f")
        date = st.date_input("Recorded date")
        datetz = utils.to_datetz(date)
        submitted = st.form_submit_button("Add entry")
        if submitted:
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

            if valid and metric_id:
                models.create_entry({"metric_id": metric_id, "value": val, "recorded_at": datetz.isoformat()})
                st.success("Entry added")

def show_entries_plot(selected_metric, unit_map):
    if not selected_metric:
        st.info("No metric selected.")
        return
    metric_id = selected_metric.get("id")
    entries = models.get_entries(metric_id)
    dfe = pd.DataFrame(entries)
    if not dfe.empty:
        dfe["recorded_at"] = pd.to_datetime(dfe["recorded_at"])
        y_col = unit_map.get(selected_metric.get("unit_id"), "value")
        fig = px.scatter(
            dfe, x="recorded_at", y="value",
            trendline="ols",
            title="Time course",
            labels={"recorded_at": "Recorded date", "value": y_col}
        )
        y_avg = dfe["value"].mean()
        fig.add_hline(y=y_avg, line_dash="dash", line_color="gray", annotation_text="Average")
        fig.update_xaxes(tickformat="%b %d, %Y")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No entries yet for this metric.")
