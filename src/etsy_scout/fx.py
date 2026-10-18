"""Currency handling for Etsy prices.

Etsy returns every price in the seller's own currency (GBP, EUR, CAD, ...). The research
sheet compares prices in US dollars, so prices are converted with the day's reference rates
from Frankfurter (European Central Bank data, free, no key): https://frankfurter.dev
"""

from __future__ import annotations

from collections.abc import Callable

import httpx

RATES_URL = "https://api.frankfurter.dev/v1/latest"


def money(price: dict | None) -> tuple[float, str] | None:
    """Etsy money object -> (amount, currency).

    {"amount": 1799, "divisor": 100, "currency_code": "GBP"} -> (17.99, "GBP")
    """
    if not price or not price.get("divisor"):
        return None
    amount = round(price["amount"] / price["divisor"], 2)
    return amount, (price.get("currency_code") or "USD").upper()


class FxRates:
    """USD conversion rates, fetched once per instance on first use."""

    def __init__(
        self,
        client: httpx.Client | None = None,
        on_warning: Callable[[str], None] = print,
    ):
        self._client = client or httpx.Client(timeout=20)
        self._on_warning = on_warning
        self._rates: dict[str, float] | None = None
        self.date: str | None = None  # date of the rates, e.g. "2026-10-16"

    def _load(self) -> dict[str, float]:
        if self._rates is None:
            try:
                resp = self._client.get(RATES_URL, params={"base": "USD"})
                resp.raise_for_status()
                data = resp.json()
                self._rates = {k.upper(): float(v) for k, v in data["rates"].items()}
                self.date = data.get("date")
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                self._on_warning(
                    f"warning: could not load exchange rates ({exc}); "
                    "non-USD prices will be left empty."
                )
                self._rates = {}
        return self._rates

    def to_usd(self, amount: float | None, currency: str | None) -> float | None:
        """Convert `amount` in `currency` to USD; None if the currency rate is unknown."""
        if amount is None:
            return None
        currency = (currency or "USD").upper()
        if currency == "USD":
            return round(amount, 2)
        rate = self._load().get(currency)  # 1 USD = `rate` units of `currency`
        return round(amount / rate, 2) if rate else None

    def money_to_usd(self, price: dict | None) -> float | None:
        """Etsy money object straight to USD."""
        parsed = money(price)
        return self.to_usd(*parsed) if parsed else None
