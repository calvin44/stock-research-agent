from pytest import raises

from backend.utils import fmt_percentage, humanize_number, safe_float, validate_ticker_info


class TestSafeFloat:
    def test_none(self):
        assert safe_float(None) is None

    def test_valid(self):
        assert safe_float(1.5) == 1.5

    def test_nan(self):
        assert safe_float(float("nan")) is None

    def test_invalid_string(self):
        assert safe_float("invalid") is None

    def test_zero(self):
        assert safe_float(0) == 0.0

    def test_boolean_true(self):
        assert safe_float(True) == 1.0

    def test_boolean_false(self):
        assert safe_float(False) == 0.0

    def test_positive_infinity(self):
        assert safe_float(float("inf")) is None

    def test_negative_infinity(self):
        assert safe_float(float("-inf")) is None


class TestHumanizeNumber:
    def test_none(self):
        assert humanize_number(None) is None

    def test_trillion(self):
        assert humanize_number(89_000_000_000_000) == "89.00T"

    def test_billion(self):
        assert humanize_number(89_000_000_000) == "89.00B"

    def test_million(self):
        assert humanize_number(89_000_000) == "89.00M"

    def test_small_number(self):
        assert humanize_number(890_000) == "890000"


class TestFmtPercentage:
    def test_string(self):
        assert fmt_percentage("") is None  # type: ignore

    def test_none(self):
        assert fmt_percentage(None) is None

    def test_rounds_down(self):
        assert fmt_percentage(89.8989888) == 89.9

    def test_rounds_up(self):
        assert fmt_percentage(89.555) == 89.56


class TestValidateTickerInfo:
    ticker = "AAPL"

    def test_empty_dict(self):
        with raises(ValueError) as exp_info:
            validate_ticker_info({}, self.ticker)
        assert "AAPL" in str(exp_info.value)

    def test_single_key_dict(self):
        with raises(ValueError) as exp_info:
            validate_ticker_info({"trailingPegRatio": None}, self.ticker)
        assert "AAPL" in str(exp_info.value)

    def test_valid_dict(self):
        mock_info = {str(i): i for i in range(50)}
        validate_ticker_info(mock_info, self.ticker)
