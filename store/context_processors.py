from django.urls import reverse

from .cart import Cart
from .models import Category, Product, SiteSettings
from .wishlist import get_ids


def store_state(request):
    """Data every page needs: menu categories and the JSON the frontend JS starts from."""
    if request.path.startswith("/admin/"):
        return {}
    site = SiteSettings.load()
    cart = Cart(request)
    products = list(Product.objects.active().select_related("category"))
    menu = list(Category.objects.filter(show_in_menu=True))
    counts = {}
    for p in products:
        counts[p.category_id] = counts.get(p.category_id, 0) + 1
    state = {
        "products": [p.to_dict() for p in products],
        "categories": [
            {"slug": c.slug, "name": c.name, "title": c.display_title, "icon": c.icon,
             "count": counts.get(c.id, 0), "url": reverse("shop_category", args=[c.slug])}
            for c in menu
        ],
        "cart": cart.to_dict(),
        "wishlist": get_ids(request),
        "user": request.user.is_authenticated,
        "urls": {
            "cart": reverse("api_cart"),
            "promo": reverse("api_promo"),
            "wishlist": reverse("api_wishlist"),
            "newsletter": reverse("api_newsletter"),
            "checkout": reverse("checkout"),
            "home": reverse("home"),
            "shop": reverse("shop"),
        },
    }
    return {
        "menu_categories": menu,
        "store_state": state,
        "site": site,
        "free_delivery_over": site.free_delivery_over,
    }
