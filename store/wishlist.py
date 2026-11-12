"""Wishlist: saved in the database for logged-in users, in the session for guests."""
from .models import Product, WishlistItem

SESSION_KEY = "wishlist"


def get_ids(request):
    if request.user.is_authenticated:
        return list(WishlistItem.objects.filter(user=request.user).values_list("product_id", flat=True))
    return list(request.session.get(SESSION_KEY, []))


def toggle(request, product):
    """Returns True if the product is now in the wishlist."""
    if request.user.is_authenticated:
        item, created = WishlistItem.objects.get_or_create(user=request.user, product=product)
        if not created:
            item.delete()
        return created
    ids = list(request.session.get(SESSION_KEY, []))
    if product.id in ids:
        ids.remove(product.id)
        added = False
    else:
        ids.append(product.id)
        added = True
    request.session[SESSION_KEY] = ids
    return added


def merge_session_into_user(request, user):
    ids = request.session.pop(SESSION_KEY, [])
    for product in Product.objects.filter(id__in=ids):
        WishlistItem.objects.get_or_create(user=user, product=product)
