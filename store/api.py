"""Small JSON API used by the frontend (cart drawer, wishlist, newsletter)."""
import json

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from . import wishlist as wl
from .cart import Cart
from .models import NewsletterSubscriber, Product


def _body(request):
    try:
        return json.loads(request.body or "{}")
    except (ValueError, UnicodeDecodeError):
        return {}


def _product(data):
    try:
        return Product.objects.active().get(pk=int(data.get("product")))
    except (Product.DoesNotExist, TypeError, ValueError):
        return None


@require_GET
def products(request):
    qs = Product.objects.active().select_related("category")
    if cat := request.GET.get("category"):
        qs = qs.filter(category__slug=cat)
    if q := request.GET.get("q"):
        qs = qs.filter(Q(name__icontains=q) | Q(category__name__icontains=q))
    return JsonResponse({"products": [p.to_dict() for p in qs]})


@require_POST
def cart(request):
    """{"action": "add"|"set"|"remove"|"clear", "product": id, "qty": n}"""
    data = _body(request)
    c = Cart(request)
    action = data.get("action")
    message = ""

    if action == "clear":
        c.clear()
    else:
        product = _product(data)
        if not product:
            return JsonResponse({"error": "Product not found"}, status=404)
        try:
            qty = int(data.get("qty", 1))
        except (TypeError, ValueError):
            return JsonResponse({"error": "Invalid quantity"}, status=400)

        if action == "add":
            if not product.in_stock:
                return JsonResponse({"error": f"{product.name} is out of stock"}, status=409)
            before = c.data.get(str(product.id), 0)
            c.add(product, max(1, qty))
            if c.data.get(str(product.id), 0) == before:
                message = f"Only {product.stock} {product.name} left in stock"
        elif action == "set":
            c.set(product, qty)
        elif action == "remove":
            c.remove(product.id)
        else:
            return JsonResponse({"error": "Unknown action"}, status=400)

    return JsonResponse({"cart": c.to_dict(), "message": message})


@require_POST
def promo(request):
    c = Cart(request)
    ok, message = c.apply_promo(_body(request).get("code"))
    return JsonResponse({"ok": ok, "message": message, "cart": c.to_dict()}, status=200 if ok else 400)


@require_POST
def wishlist(request):
    product = _product(_body(request))
    if not product:
        return JsonResponse({"error": "Product not found"}, status=404)
    added = wl.toggle(request, product)
    return JsonResponse({"added": added, "wishlist": wl.get_ids(request)})


@require_POST
def newsletter(request):
    email = (_body(request).get("email") or "").strip().lower()
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({"ok": False, "message": "Please enter a valid email address"}, status=400)
    _, created = NewsletterSubscriber.objects.get_or_create(email=email)
    msg = "Subscribed! Use code FRESH10 on your first order" if created else "You're already subscribed — thank you!"
    return JsonResponse({"ok": True, "message": msg})
