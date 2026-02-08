import pytest


pytest.importorskip("streamlit")


from ui.capture import (  # noqa: E402
    _infer_float_step_and_format,
    _infer_float_step_and_format_from_history,
    _round_down,
)


def test_infer_float_step_and_format_integer():
    """Integer input infers step=1 and 0-decimal format."""
    step, fmt = _infer_float_step_and_format(5)
    assert step == 1.0
    assert fmt == "%.0f"


def test_infer_float_step_and_format_decimal():
    """Decimal input infers small step and 2-decimal format."""
    step, fmt = _infer_float_step_and_format(2.75)
    assert step == pytest.approx(0.01)
    assert fmt == "%.2f"


def test_round_down_respects_decimals():
    """Rounding down respects the requested decimal precision."""
    assert _round_down(1.239, 2) == 1.23
    assert _round_down(1.2, 0) == 1.0


def test_infer_from_history_returns_reasonable_step():
    """History-based step inference returns a positive step and a format."""
    values = [1.0, 1.1, 1.2, 1.25]
    step, fmt = _infer_float_step_and_format_from_history(values)
    assert step > 0
    assert fmt.startswith("%.")
