import pytest


st = pytest.importorskip("streamlit")
AppTest = pytest.importorskip("streamlit.testing.v1").AppTest


def test_visualize_period_allows_6m_even_for_sparse_data():
    script = """
import streamlit as st
import pandas as pd
from ui import visualize

metric_id = "m1"
st.session_state["viz_period_m1"] = "6M"

df = pd.DataFrame([{"recorded_at": "2026-03-01T12:00:00Z", "value": 1}])
visualize.show_visualizations(
    df,
    "min",
    "Yoga",
    metric_kind="count",
    unit_type="integer",
    show_pills=True,
    metric_id=metric_id,
)

st.text("period=" + str(st.session_state.get("viz_period_m1")))
"""
    at = AppTest.from_string(script)
    at.run()

    assert any(el.value == "period=6M" for el in at.text)


def test_visualize_period_state_is_stable_across_metric_name_changes():
    script = """
import streamlit as st
import pandas as pd
from ui import visualize

metric_id = "m1"
st.session_state.setdefault("viz_period_m1", "Year")

flip = st.checkbox("Flip name", value=False)
m_name = "Sleep" if not flip else "SLEEP"

df = pd.DataFrame([{"recorded_at": "2026-03-01T12:00:00Z", "value": 2.0}])
visualize.show_visualizations(
    df,
    "pts",
    m_name,
    metric_kind="quantitative",
    unit_type="float",
    show_pills=True,
    metric_id=metric_id,
)

st.text("period=" + str(st.session_state.get("viz_period_m1")))
"""
    at = AppTest.from_string(script)
    at.run()
    assert any(el.value == "period=Year" for el in at.text)

    assert len(at.checkbox) == 1
    at.checkbox[0].set_value(True)
    at.run()

    assert any(el.value == "period=Year" for el in at.text)
