from pytest import mark, raises

from backend.agent.agent import run_research


@mark.integration
class TestRunResearch:
    ticker = "AAPL"

    def test_valid_ticker_returns_complete_analysis(self):
        """Smoke test: agent runs end-to-end, returns the right ticker"""
        analysis = run_research(self.ticker)
        assert analysis.ticker == self.ticker

    def test_data_sources_not_hallucinated(self):
        """Regression test for the data_sources fabrication bug (see decision.md #6)"""
        analysis = run_research(self.ticker)
        for item in analysis.recent_news:
            assert item.source_url in analysis.data_sources

    def test_disclaimer_always_present(self):
        """Compliance check - SYSTEM_PROMPT requires this explicitly"""
        analysis = run_research(self.ticker)
        assert analysis.disclaimer != ""

    def test_invalid_ticker(self):
        with raises(ValueError):
            run_research("INVALID_TICKER")
