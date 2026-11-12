"""Session-based shopping cart. All prices are calculated on the server."""
from decimal import ROUND_HALF_UP, Decimal

from .currency import format_inr
from .models import Product, PromoCode, SiteSettings

CART_KEY = "cart"
PROMO_KEY = "promo"
MAX_QTY = 99


def money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class Cart:
    def __init__(self, request):
        self.session = request.session
        self.data = self.session.get(CART_KEY) or {}

    # ---------- changes ----------
    def _save(self):
        self.session[CART_KEY] = self.data
        self.session.modified = True

    def add(self, product, qty=1):
        current = self.data.get(str(product.id), 0)
        self.set(product, current + qty)

    def set(self, product, qty):
        qty = max(0, min(int(qty), MAX_QTY, product.stock))
        if qty:
            self.data[str(product.id)] = qty
        else:
            self.data.pop(str(product.id), None)
        self._save()

    def remove(self, product_id):
        self.data.pop(str(product_id), None)
        self._save()

    def clear(self):
        self.data = {}
        self.session[CART_KEY] = {}
        self.session.pop(PROMO_KEY, None)
        self.session.modified = True

    # ---------- promo ----------
    @property
    def promo(self):
        code = self.session.get(PROMO_KEY)
        if not code:
            return None
        promo = PromoCode.objects.filter(code=code).first()
        if promo and promo.is_valid_now():
            return promo
        self.session.pop(PROMO_KEY, None)
        return None

    def apply_promo(self, code):
        """Returns (ok, message)."""
        code = (code or "").strip().upper()
        if not code:
            self.session.pop(PROMO_KEY, None)
            self.session.modified = True
            return True, "Promo code removed"
        promo = PromoCode.objects.filter(code=code).first()
        if not promo or not promo.is_active:
            return False, f"“{code}” is not a valid promo code"
        if not promo.is_valid_now():
            return False, f"Sorry, {code} has expired"
        if not self.count:
            return False, "Add something to your cart first, then apply the code"
        subtotal = self.subtotal
        if subtotal < promo.min_order:
            short = promo.min_order - subtotal
            return False, (f"Add {format_inr(short)} more to use {code} "
                           f"(minimum order {format_inr(promo.min_order)})")
        self.session[PROMO_KEY] = promo.code
        self.session.modified = True
        return True, f"Code {promo.code} applied — {promo.percent}% off!"

    # ---------- reading ----------
    def lines(self):
        """[(product, qty)] for products that still exist and are active."""
        ids = [int(i) for i in self.data]
        products = Product.objects.active().select_related("category").in_bulk(ids)
        out = []
        for pid in ids:
            p = products.get(pid)
            if p:
                out.append((p, self.data[str(pid)]))
        if len(out) != len(self.data):  # drop vanished products
            self.data = {str(p.id): q for p, q in out}
            self._save()
        return out

    @property
    def count(self):
        return sum(self.data.values())

    @property
    def subtotal(self):
        return money(sum((p.price * q for p, q in self.lines()), Decimal("0")))

    def offers(self, subtotal=None, applied=None):
        """Every promo code a shopper can use right now, with how close the cart is to it."""
        from django.db.models import Q
        from django.utils import timezone
        subtotal = self.subtotal if subtotal is None else subtotal
        codes = (PromoCode.objects.filter(is_active=True)
                 .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=timezone.now()))
                 .order_by("min_order", "-percent"))
        out = []
        for promo in codes:
            min_order = money(promo.min_order)
            left = max(Decimal("0.00"), money(min_order - subtotal))
            if min_order:
                desc = f"{promo.percent}% off on orders above {format_inr(min_order)}"
            else:
                desc = f"{promo.percent}% off on your order"
            out.append({
                "code": promo.code,
                "percent": promo.percent,
                "min_order": min_order,
                "desc": desc,
                "left": left,
                "unlocked": not left,
                "applied": promo.code == applied,
                "pct": min(100, int(subtotal / min_order * 100)) if min_order else 100,
            })
        return out

    def totals(self):
        subtotal = self.subtotal
        promo = self.promo
        promo_note = ""
        if promo and subtotal < promo.min_order:
            # code is saved but the cart dropped below its minimum: tell the shopper
            promo_note = (f"{promo.code} needs a minimum order of {format_inr(promo.min_order)} — "
                          f"add {format_inr(promo.min_order - subtotal)} more")
            promo = None
        discount = money(subtotal * promo.percent / 100) if promo else Decimal("0.00")
        after = subtotal - discount
        site = SiteSettings.load()
        free_over = Decimal(site.free_delivery_over)
        delivery = Decimal("0.00") if (not self.count or after >= free_over) else money(site.delivery_fee)
        return {
            "subtotal": subtotal,
            "discount": discount,
            "delivery": delivery,
            "total": money(after + delivery),
            "promo": promo.code if promo else None,
            "promo_percent": promo.percent if promo else 0,
            "promo_note": promo_note,
            "offers": self.offers(subtotal, promo.code if promo else None),
            "free_left": max(Decimal("0.00"), money(free_over - after)),
            "free_pct": min(100, int(after / free_over * 100)) if free_over else 100,
        }

    def to_dict(self):
        t = self.totals()
        return {
            "items": [
                {**p.to_dict(), "qty": q, "line": float(money(p.price * q))}
                for p, q in self.lines()
            ],
            "qty": self.data,
            "count": self.count,
            "subtotal": float(t["subtotal"]),
            "discount": float(t["discount"]),
            "delivery": float(t["delivery"]),
            "total": float(t["total"]),
            "promo": t["promo"],
            "promoPercent": t["promo_percent"],
            "promoNote": t["promo_note"],
            "offers": [
                {"code": o["code"], "percent": o["percent"], "minOrder": float(o["min_order"]),
                 "desc": o["desc"], "left": float(o["left"]), "unlocked": o["unlocked"],
                 "applied": o["applied"], "pct": o["pct"]}
                for o in t["offers"]
            ],
            "freeLeft": float(t["free_left"]),
            "freePct": t["free_pct"],
        }
