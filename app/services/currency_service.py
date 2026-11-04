from typing import Dict, List, Tuple

class CurrencyService:
    """
    Multi-Currency and Foreign Exchange (FX) Conversion Engine.
    Provides exchange rate matrix, automatic conversion to base currency,
    and localized formatting.
    """

    # Baseline Exchange Rate Matrix normalized to 1 USD
    # Rates represent value of 1 Foreign Currency unit in USD (e.g. 1 EUR = 1.08 USD)
    RATES_TO_USD: Dict[str, Dict] = {
        "USD": {"code": "USD", "name": "US Dollar", "symbol": "$", "rate_to_usd": 1.0},
        "EUR": {"code": "EUR", "name": "Euro", "symbol": "€", "rate_to_usd": 1.085},
        "GBP": {"code": "GBP", "name": "British Pound", "symbol": "£", "rate_to_usd": 1.282},
        "INR": {"code": "INR", "name": "Indian Rupee", "symbol": "₹", "rate_to_usd": 0.0120},
        "JPY": {"code": "JPY", "name": "Japanese Yen", "symbol": "¥", "rate_to_usd": 0.0065},
        "CAD": {"code": "CAD", "name": "Canadian Dollar", "symbol": "C$", "rate_to_usd": 0.738},
        "AUD": {"code": "AUD", "name": "Australian Dollar", "symbol": "A$", "rate_to_usd": 0.658},
    }

    @classmethod
    def get_supported_currencies(cls) -> List[Dict]:
        """Returns all supported currencies with symbols and metadata."""
        return list(cls.RATES_TO_USD.values())

    @classmethod
    def get_currency_info(cls, code: str) -> Dict:
        """Returns currency definition dict, defaulting to USD if unrecognized."""
        code_upper = (code or "USD").upper().strip()
        return cls.RATES_TO_USD.get(code_upper, cls.RATES_TO_USD["USD"])

    @classmethod
    def convert_to_base(cls, amount: float, from_currency: str, base_currency: str = "USD") -> Tuple[float, float]:
        """
        Converts an amount from a specified currency into the base currency.
        Returns: (converted_amount, applied_exchange_rate)
        """
        from_code = (from_currency or "USD").upper().strip()
        base_code = (base_currency or "USD").upper().strip()

        from_info = cls.get_currency_info(from_code)
        base_info = cls.get_currency_info(base_code)

        # Value in USD
        amount_usd = float(amount) * from_info["rate_to_usd"]

        # Value in target base currency
        if base_code == "USD":
            converted_amount = amount_usd
            rate = from_info["rate_to_usd"]
        else:
            rate = from_info["rate_to_usd"] / base_info["rate_to_usd"]
            converted_amount = float(amount) * rate

        return round(converted_amount, 2), round(rate, 6)

    @classmethod
    def convert(cls, amount: float, from_curr: str, to_curr: str) -> Tuple[float, float]:
        """Converts an amount between any two supported currencies."""
        return cls.convert_to_base(amount, from_currency=from_curr, base_currency=to_curr)

    @classmethod
    def format_amount(cls, amount: float, currency_code: str = "USD") -> str:
        """Formats amount with currency symbol and thousands separators."""
        info = cls.get_currency_info(currency_code)
        symbol = info["symbol"]
        amt = float(amount or 0.0)
        
        # JPY typically doesn't use decimals in common display
        if info["code"] == "JPY":
            return f"{symbol}{int(round(amt)):,}"
        return f"{symbol}{amt:,.2f}"
