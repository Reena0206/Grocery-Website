import secrets
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


MAX_IMAGE_PX = 800


def shrink_image(field, max_px=MAX_IMAGE_PX):
    """Resize an uploaded image in place so big photos don't slow the shop down.

    Product cards show images at ~200px, so 800px is plenty (sharp on retina screens too).
    Transparency is kept. Does nothing if the file is already small or isn't an image.
    """
    if not field or not field.name:
        return
    try:
        from PIL import Image
        with field.storage.open(field.name, "rb") as fh:
            img = Image.open(fh)
            img.load()
        if max(img.size) <= max_px:
            return
        fmt = img.format or "PNG"
        img.thumbnail((max_px, max_px), Image.LANCZOS)
        if fmt == "JPEG" and img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        path = field.path  # local file storage
        save_kwargs = {"optimize": True}
        if fmt in ("JPEG", "WEBP"):
            save_kwargs["quality"] = 85
        img.save(path, fmt, **save_kwargs)
    except Exception:  # never block saving a product because of an image problem
        import logging
        logging.getLogger(__name__).warning("Could not resize %s", field.name, exc_info=True)


class SiteSettings(models.Model):
    """One row of editable store-wide text and rules (Admin → Site settings)."""
    store_name = models.CharField(max_length=60, default="eGrocery")

    # announcement bar
    show_announcement = models.BooleanField(default=True)
    announcement = models.CharField(max_length=160, default="Free delivery on orders over ₹499 · Use code FRESH10 for 10% off")

    # delivery rules (used by the cart and checkout)
    free_delivery_over = models.DecimalField("Free delivery over (₹)", max_digits=8, decimal_places=2, default=Decimal("499"))
    delivery_fee = models.DecimalField("Delivery fee (₹)", max_digits=8, decimal_places=2, default=Decimal("40"))
    delivery_minutes = models.PositiveIntegerField("Average delivery time (minutes)", default=30)

    # hero
    hero_badge = models.CharField(max_length=80, default="Delivered in 30 minutes")
    hero_title = models.CharField(max_length=80, default="Everyday groceries,")
    hero_highlight = models.CharField(max_length=40, default="freshly", help_text="Word shown in green italics.")
    hero_title_end = models.CharField(max_length=60, default="delivered.")
    hero_subtitle = models.CharField(max_length=255, default="Farm-fresh produce, quality meat and daily essentials — picked this morning and at your door before you know it.")
    happy_customers = models.CharField(max_length=20, default="12K+", help_text="e.g. 12K+")
    store_rating = models.DecimalField(max_digits=2, decimal_places=1, default=Decimal("4.9"))

    # footer / contact
    footer_about = models.CharField(max_length=255, default="Fresh groceries delivered to your doorstep, every day. Quality you can taste, prices you'll love.")
    phone = models.CharField(max_length=40, default="+91 98765 43210")
    email = models.EmailField(default="hello@egrocery.in")
    address = models.CharField(max_length=160, default="21 MG Road, Bengaluru, Karnataka")
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    twitter_url = models.URLField("X / Twitter URL", blank=True)
    youtube_url = models.URLField(blank=True)

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return "Site settings"

    def save(self, *args, **kwargs):
        self.pk = 1  # always a single row
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Category(models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=120, blank=True, help_text="Long name shown as the product heading, e.g. 'Fruits & Vegetables'.")
    icon = models.CharField(max_length=60, default="fa-solid fa-basket-shopping", help_text="Font Awesome classes, e.g. 'fa-solid fa-carrot'.")
    order = models.PositiveIntegerField(default=0)
    show_in_menu = models.BooleanField(default=True, help_text="Show as a card in the Category section.")

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    @property
    def display_title(self):
        return self.title or self.name


class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def items(self):
        return self.active().filter(is_bundle=False)

    def bundles(self):
        return self.active().filter(is_bundle=True)


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True, blank=True)
    unit = models.CharField(max_length=40, help_text="e.g. 1 KG, 500 G, 12 PCS")
    description = models.TextField(blank=True, help_text="Bundles: what's inside (short list). Other products: the text shown on the product page and quick view.")
    price = models.DecimalField("Price (₹)", max_digits=8, decimal_places=2)
    old_price = models.DecimalField("Old price (₹)", max_digits=8, decimal_places=2, null=True, blank=True, help_text="Set to show a discount badge.")
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=Decimal("4.5"),
                                 validators=[MinValueValidator(0), MaxValueValidator(5)])
    image = models.ImageField(upload_to="products/")
    stock = models.PositiveIntegerField(default=100)
    is_popular = models.BooleanField(default=False, help_text="Show in 'Popular Product'.")
    is_new = models.BooleanField(default=False)
    is_bundle = models.BooleanField(default=False, help_text="Show in 'Popular Bundle Pack'.")
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "product"
            slug, n = base, 2
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)
        shrink_image(self.image)

    def get_absolute_url(self):
        return reverse("product_detail", args=[self.slug])

    @property
    def discount_percent(self):
        if self.old_price and self.old_price > self.price:
            return round((1 - self.price / self.old_price) * 100)
        return 0

    @property
    def savings(self):
        return self.old_price - self.price if self.old_price and self.old_price > self.price else 0

    @property
    def in_stock(self):
        return self.stock > 0

    def to_dict(self):
        """Shape used by the frontend JavaScript."""
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "url": self.get_absolute_url(),
            "unit": self.unit,
            "desc": self.description,
            "price": float(self.price),
            "oldPrice": float(self.old_price) if self.old_price else None,
            "rating": float(self.rating),
            "img": self.image.url if self.image else "",
            "cat": self.category.slug,
            "catTitle": self.category.display_title,
            "popular": self.is_popular,
            "isNew": self.is_new,
            "bundle": self.is_bundle,
            "stock": self.stock,
        }


class Deal(models.Model):
    """'Deal of the Day' banner on the home page (the newest active one is shown)."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="deals")
    headline = models.CharField(max_length=120, default="Fresh Strawberries")
    text = models.CharField(max_length=255, default="Sweet, juicy and hand-picked this morning. Hurry — the offer ends at midnight.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Deal: {self.headline}"


class PromoCode(models.Model):
    code = models.CharField(max_length=30, unique=True)
    percent = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(90)])
    is_active = models.BooleanField(default=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    min_order = models.DecimalField("Minimum order (₹)", max_digits=8, decimal_places=2, default=0, help_text="Minimum subtotal to use this code.")

    def __str__(self):
        return f"{self.code} ({self.percent}%)"

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def is_valid_now(self):
        from django.utils import timezone
        return self.is_active and (self.valid_until is None or self.valid_until >= timezone.now())


class Testimonial(models.Model):
    name = models.CharField(max_length=80)
    role = models.CharField(max_length=80, default="Verified buyer")
    text = models.TextField()
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=5,
                                 validators=[MinValueValidator(0), MaxValueValidator(5)])
    photo = models.ImageField(upload_to="testimonials/", blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.name

    @property
    def stars(self):
        """List like ['full','full','full','full','half'] for the template."""
        r = float(self.rating)
        out = []
        for i in range(1, 6):
            out.append("full" if r >= i else "half" if r >= i - 0.5 else "empty")
        return out


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class WishlistItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product")
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user} ♥ {self.product}"


def _order_number():
    return "EG" + "".join(secrets.choice("0123456789") for _ in range(8))


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        PACKED = "packed", "Packed"
        OUT_FOR_DELIVERY = "out_for_delivery", "Out for delivery"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class Payment(models.TextChoices):
        COD = "cod", "Cash on delivery"
        CARD_ON_DELIVERY = "card", "Card on delivery"

    number = models.CharField(max_length=20, unique=True, default=_order_number, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="orders")
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=80)
    note = models.CharField(max_length=255, blank=True, help_text="Delivery instructions")
    payment_method = models.CharField(max_length=10, choices=Payment.choices, default=Payment.COD)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    promo_code = models.CharField(max_length=30, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.number}"

    def get_absolute_url(self):
        return reverse("order_detail", args=[self.number])

    @property
    def item_count(self):
        return sum(i.quantity for i in self.items.all())

    @property
    def progress_step(self):
        steps = ["pending", "confirmed", "packed", "out_for_delivery", "delivered"]
        return steps.index(self.status) if self.status in steps else -1


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=120)
    unit = models.CharField(max_length=40, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.quantity} × {self.name}"

    @property
    def line_total(self):
        return self.price * self.quantity
