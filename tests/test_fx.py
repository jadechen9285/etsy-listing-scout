import httpx

from etsy_scout.fx import FxRates, money


def rates(*_, **__) -> httpx.Response:
    return httpx.Response(200, json={"base": "USD", "date": "2026-10-16", "rates": {"GBP": 0.75}})


def make_fx(handler=rates, warnings=None) -> FxRates:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return FxRates(client=client, on_warning=(warnings.append if warnings is not None else print))


def test_money_parses_etsy_amounts():
    assert money({"amount": 1799, "divisor": 100, "currency_code": "gbp"}) == (17.99, "GBP")
    assert money({"amount": 500, "divisor": 100}) == (5.0, "USD")
    assert money(None) is None and money({"amount": 1, "divisor": 0}) is None


def test_usd_passes_through_without_loading_rates():
    def boom(request):
        raise AssertionError("rates should not be fetched for USD")

    assert make_fx(boom).to_usd(12.5, "USD") == 12.5


def test_converts_to_usd_and_records_rate_date():
    fx = make_fx()
    assert fx.to_usd(15.0, "GBP") == 20.0
    assert fx.money_to_usd({"amount": 750, "divisor": 100, "currency_code": "GBP"}) == 10.0
    assert fx.date == "2026-10-16"


def test_unknown_currency_and_network_failure_give_none():
    assert make_fx().to_usd(10, "XYZ") is None

    def down(request):
        raise httpx.ConnectError("offline")

    warnings: list[str] = []
    fx = make_fx(down, warnings)
    assert fx.to_usd(10, "EUR") is None
    assert fx.to_usd(20, "GBP") is None
    assert len(warnings) == 1  # warned once, not per price
