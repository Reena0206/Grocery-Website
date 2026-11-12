"""Indian rupee formatting: 1199 -> ₹1,199 · 123456.5 -> ₹1,23,456.50"""
from decimal import Decimal, InvalidOperation


def format_inr(value, symbol=True):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return value
    sign = "-" if amount < 0 else ""
    amount = abs(amount).quantize(Decimal("0.01"))
    whole, paise = divmod(amount, 1)
    digits = str(int(whole))
    # Indian grouping: last 3 digits, then groups of 2
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups + [tail])
    text = digits if paise == 0 else f"{digits}.{int(paise * 100):02d}"
    return f"{sign}{'₹' if symbol else ''}{text}"
