import json
import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .currency import format_inr
from .models import Category, Order, Product, PromoCode, SiteSettings, WishlistItem

TMP_MEDIA = tempfile.mkdtemp()
def _png():
    from io import BytesIO
    from PIL import Image
    buf = BytesIO()
    Image.new("RGBA", (4, 4), (34, 164, 71, 255)).save(buf, "PNG")
    return buf.getvalue()


PNG = _png()


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class StoreTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def setUp(self):
        # small round numbers keep the cart maths easy to read
        SiteSettings.objects.create(free_delivery_over=30, delivery_fee=3)
        self.cat = Category.objects.create(name="Vegetables", slug="vegetables")
        self.apple = self.make("Apple", "2.00", stock=50)
        self.salmon = self.make("Salmon", "18.00", stock=2)
        PromoCode.objects.create(code="fresh10", percent=10)

    def make(self, name, price, stock=100):
        return Product.objects.create(category=self.cat, name=name, unit="1 KG", price=Decimal(price), stock=stock,
                                      image=SimpleUploadedFile(f"{name}.png", PNG, content_type="image/png"))

    def post(self, name, data):
        return self.client.post(reverse(name), json.dumps(data), content_type="application/json")

    # ---------- pages ----------
    def test_pages_render(self):
        self.assertContains(self.client.get(reverse("home")), "Everyday groceries,")
        self.assertContains(self.client.get(self.apple.get_absolute_url()), "Apple")
        self.assertEqual(self.client.get(reverse("login")).status_code, 200)
        self.assertEqual(self.client.get(reverse("signup")).status_code, 200)

    def test_shop_pages(self):
        r = self.client.get(reverse("shop"))
        self.assertContains(r, "All Categories")
        self.assertContains(r, 'data-shop-cat="vegetables"')
        r = self.client.get(reverse("shop_category", args=["vegetables"]))
        self.assertContains(r, 'data-initial-cat="vegetables"')
        self.assertEqual(self.client.get("/shop/does-not-exist/").status_code, 404)
        # the frontend gets every menu category with its product count
        self.assertEqual(r.context["store_state"]["categories"][0]["count"], 2)

    def test_rupee_formatting(self):
        self.assertEqual(format_inr(1199), "₹1,199")
        self.assertEqual(format_inr("123456.5"), "₹1,23,456.50")
        self.assertEqual(format_inr(Decimal("34.20")), "₹34.20")
        self.assertContains(self.client.get(self.apple.get_absolute_url()), "₹2")

    def test_site_settings_drive_delivery_and_text(self):
        site = SiteSettings.load()
        site.free_delivery_over, site.delivery_fee, site.hero_title = 10, 5, "Groceries for Bengaluru"
        site.save()
        r = self.post("api_cart", {"action": "add", "product": self.apple.id}).json()["cart"]
        self.assertEqual(r["delivery"], 5.0)                      # under ₹10
        r = self.post("api_cart", {"action": "add", "product": self.salmon.id}).json()["cart"]
        self.assertEqual(r["delivery"], 0.0)                      # over ₹10
        self.assertContains(self.client.get(reverse("home")), "Groceries for Bengaluru")
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_seed_never_overwrites_admin_changes(self):
        from django.core.management import call_command
        from io import StringIO
        call_command("seed_store", stdout=StringIO())
        mango = Product.objects.get(name="Mango")
        self.assertEqual(mango.price, Decimal("160"))            # starter price in rupees
        self.assertTrue(mango.description)                       # description stored in the database
        Product.objects.filter(pk=mango.pk).update(price=999)     # owner edits the price in the admin
        call_command("seed_store", stdout=StringIO())             # e.g. runs again on deploy
        mango.refresh_from_db()
        self.assertEqual(mango.price, Decimal("999"))

    def test_slug_is_generated_and_unique(self):
        other = self.make("Apple", "3.00")
        self.assertEqual(self.apple.slug, "apple")
        self.assertEqual(other.slug, "apple-2")

    # ---------- cart ----------
    def test_cart_totals_and_delivery_fee(self):
        r = self.post("api_cart", {"action": "add", "product": self.apple.id, "qty": 3}).json()["cart"]
        self.assertEqual(r["count"], 3)
        self.assertEqual(r["subtotal"], 6.0)
        self.assertEqual(r["delivery"], 3.0)          # under $30
        self.assertEqual(r["total"], 9.0)

        r = self.post("api_cart", {"action": "add", "product": self.salmon.id, "qty": 2}).json()["cart"]
        self.assertEqual(r["subtotal"], 42.0)
        self.assertEqual(r["delivery"], 0.0)          # free over $30

    def test_cart_respects_stock(self):
        r = self.post("api_cart", {"action": "add", "product": self.salmon.id, "qty": 10}).json()
        self.assertEqual(r["cart"]["qty"][str(self.salmon.id)], 2)

    def test_cart_set_zero_removes(self):
        self.post("api_cart", {"action": "add", "product": self.apple.id})
        r = self.post("api_cart", {"action": "set", "product": self.apple.id, "qty": 0}).json()
        self.assertEqual(r["cart"]["count"], 0)

    def test_unknown_product_404(self):
        self.assertEqual(self.post("api_cart", {"action": "add", "product": 9999}).status_code, 404)

    def test_promo_code(self):
        self.post("api_cart", {"action": "add", "product": self.salmon.id, "qty": 2})
        bad = self.post("api_promo", {"code": "NOPE"})
        self.assertEqual(bad.status_code, 400)
        r = self.post("api_promo", {"code": "fresh10"}).json()
        self.assertTrue(r["ok"])
        self.assertEqual(r["cart"]["discount"], 3.6)
        self.assertEqual(r["cart"]["total"], 32.4)

    def test_promo_messages_explain_why(self):
        # empty cart
        r = self.post("api_promo", {"code": "FRESH10"}).json()
        self.assertFalse(r["ok"])
        self.assertIn("Add something to your cart first", r["message"])
        # below the minimum order: says how much more to add
        PromoCode.objects.create(code="BIG20", percent=20, min_order=50)
        self.post("api_cart", {"action": "add", "product": self.apple.id})          # ₹2
        r = self.post("api_promo", {"code": "big20"}).json()
        self.assertIn("Add ₹48 more to use BIG20", r["message"])
        # unknown code
        self.assertIn("not a valid promo code", self.post("api_promo", {"code": "XYZ"}).json()["message"])

    def test_saved_promo_shows_note_when_cart_drops_below_minimum(self):
        PromoCode.objects.create(code="BIG20", percent=20, min_order=30)
        self.post("api_cart", {"action": "add", "product": self.salmon.id, "qty": 2})  # ₹36
        self.assertTrue(self.post("api_promo", {"code": "BIG20"}).json()["ok"])
        cart = self.post("api_cart", {"action": "set", "product": self.salmon.id, "qty": 1}).json()["cart"]
        self.assertEqual(cart["discount"], 0.0)
        self.assertIn("add ₹12 more", cart["promoNote"])

    def test_cart_lists_available_offers(self):
        from django.utils import timezone
        from datetime import timedelta
        PromoCode.objects.create(code="BIG20", percent=20, min_order=50)
        PromoCode.objects.create(code="OFF5", percent=5, is_active=False)                       # hidden
        PromoCode.objects.create(code="OLD", percent=5, valid_until=timezone.now() - timedelta(days=1))  # hidden
        cart = self.post("api_cart", {"action": "add", "product": self.salmon.id}).json()["cart"]  # ₹18
        offers = {o["code"]: o for o in cart["offers"]}
        self.assertEqual(list(offers), ["FRESH10", "BIG20"])        # cheapest to unlock first
        self.assertTrue(offers["FRESH10"]["unlocked"])
        self.assertFalse(offers["BIG20"]["unlocked"])
        self.assertEqual(offers["BIG20"]["left"], 32.0)             # ₹50 − ₹18
        self.assertEqual(offers["BIG20"]["pct"], 36)
        cart = self.post("api_promo", {"code": "FRESH10"}).json()["cart"]
        self.assertTrue({o["code"]: o for o in cart["offers"]}["FRESH10"]["applied"])

    def test_checkout_page_has_promo_box(self):
        self.post("api_cart", {"action": "add", "product": self.salmon.id, "qty": 2})
        self.assertContains(self.client.get(reverse("checkout")), 'id="checkoutPromo"')
        self.post("api_promo", {"code": "FRESH10"})
        r = self.client.get(reverse("checkout"))
        self.assertContains(r, "FRESH10</b> applied")
        self.assertContains(r, "Place Order · ₹32.40")

    def test_csrf_is_enforced(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        r = c.post(reverse("api_cart"), json.dumps({"action": "add", "product": self.apple.id}), content_type="application/json")
        self.assertEqual(r.status_code, 403)

    # ---------- checkout ----------
    def checkout_data(self, **kw):
        return {"full_name": "Jane Doe", "email": "jane@example.com", "phone": "+1 555 123 4567",
                "address": "1 Market St", "city": "NY", "note": "", "payment_method": "cod", **kw}

    def test_checkout_creates_order_reduces_stock_and_clears_cart(self):
        self.post("api_cart", {"action": "add", "product": self.salmon.id, "qty": 2})
        self.post("api_promo", {"code": "FRESH10"})
        r = self.client.post(reverse("checkout"), self.checkout_data())
        order = Order.objects.get()
        self.assertRedirects(r, f"{order.get_absolute_url()}?placed=1")
        self.assertEqual(order.total, Decimal("32.40"))
        self.assertEqual(order.promo_code, "FRESH10")
        self.assertEqual(order.items.get().quantity, 2)
        self.salmon.refresh_from_db()
        self.assertEqual(self.salmon.stock, 0)
        self.assertEqual(self.client.session["cart"], {})
        # guest who placed it can view it, a stranger can't
        self.assertEqual(self.client.get(order.get_absolute_url()).status_code, 200)
        from django.test import Client
        self.assertEqual(Client().get(order.get_absolute_url()).status_code, 404)

    def test_checkout_rejects_bad_phone(self):
        self.post("api_cart", {"action": "add", "product": self.apple.id})
        r = self.client.post(reverse("checkout"), self.checkout_data(phone="12"))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Order.objects.exists())

    def test_checkout_empty_cart_redirects(self):
        self.assertRedirects(self.client.get(reverse("checkout")), reverse("home"))

    def test_checkout_stops_when_stock_ran_out(self):
        self.post("api_cart", {"action": "add", "product": self.salmon.id, "qty": 2})
        Product.objects.filter(pk=self.salmon.pk).update(stock=1)   # someone else bought one
        self.client.post(reverse("checkout"), self.checkout_data())
        self.assertFalse(Order.objects.exists())

    # ---------- accounts & wishlist ----------
    def test_signup_logs_in_and_guest_wishlist_is_kept_on_login(self):
        self.post("api_wishlist", {"product": self.apple.id})
        r = self.client.post(reverse("signup"), {
            "first_name": "Jane", "username": "jane", "email": "jane@example.com",
            "password1": "Sup3r-secret-pw", "password2": "Sup3r-secret-pw"})
        self.assertRedirects(r, reverse("home"))
        user = User.objects.get(username="jane")
        self.assertTrue(WishlistItem.objects.filter(user=user, product=self.apple).exists())
        r = self.post("api_wishlist", {"product": self.apple.id}).json()
        self.assertFalse(r["added"])
        self.assertEqual(r["wishlist"], [])

    def test_signup_race_shows_error_instead_of_crashing(self):
        """Simulates a double-click: the username is taken between validation and saving."""
        from unittest import mock
        from django.db import IntegrityError
        data = {"first_name": "Reena", "username": "reena", "email": "reena@example.com",
                "password1": "Sup3r-secret-pw", "password2": "Sup3r-secret-pw"}
        with mock.patch("store.views.SignUpForm.save", side_effect=IntegrityError("UNIQUE constraint failed")):
            r = self.client.post(reverse("signup"), data)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "This username was just taken")

    def test_duplicate_username_is_a_form_error(self):
        User.objects.create_user("reena", "x@example.com", "pw")
        r = self.client.post(reverse("signup"), {
            "first_name": "R", "username": "Reena", "email": "other@example.com",
            "password1": "Sup3r-secret-pw", "password2": "Sup3r-secret-pw"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "already exists")

    def test_signup_ignores_unsafe_next(self):
        r = self.client.post(reverse("signup") + "?next=https://evil.example.com/", {
            "first_name": "A", "username": "anna", "email": "anna@example.com",
            "password1": "Sup3r-secret-pw", "password2": "Sup3r-secret-pw"})
        self.assertRedirects(r, reverse("home"))

    def test_my_orders_requires_login(self):
        r = self.client.get(reverse("my_orders"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("login"), r.url)

    def test_admin_pages_load(self):
        admin = User.objects.create_superuser("boss", "boss@example.com", "pw-for-tests-only")
        self.client.force_login(admin)
        for model in ["product", "category", "order", "promocode", "deal", "testimonial", "newslettersubscriber", "wishlistitem"]:
            self.assertEqual(self.client.get(reverse(f"admin:store_{model}_changelist")).status_code, 200, model)
        self.assertEqual(self.client.get(reverse("admin:store_product_change", args=[self.apple.id])).status_code, 200)

    def test_newsletter(self):
        self.assertEqual(self.post("api_newsletter", {"email": "bad"}).status_code, 400)
        self.assertTrue(self.post("api_newsletter", {"email": "a@b.com"}).json()["ok"])
        self.assertIn("already", self.post("api_newsletter", {"email": "A@b.com"}).json()["message"])
