"""Load the starter catalogue (prices in Indian rupees).

    python manage.py seed_store            # add anything that's missing, never touch existing rows
    python manage.py seed_store --update   # also reset existing starter products to these values

The deploy scripts run the plain version, so changes made in the admin are never overwritten.
"""
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from store.models import Category, Deal, Product, PromoCode, SiteSettings, Testimonial

IMAGES = Path(settings.BASE_DIR) / "static" / "images"

CATEGORIES = [
    # slug, name, title, icon, show_in_menu
    ("meat", "Fish & Meat", "Fish & Meat", "fa-solid fa-fish", True),
    ("vegetables", "Vegetables", "Fruits & Vegetables", "fa-solid fa-carrot", True),
    ("medicine", "Medicine", "Medicine & Health", "fa-solid fa-capsules", True),
    ("baby", "Baby", "Baby & Dairy", "fa-solid fa-baby-carriage", True),
    ("office", "Office", "Office Supplies", "fa-solid fa-paperclip", True),
    ("beauty", "Beauty", "Beauty & Care", "fa-solid fa-spray-can-sparkles", True),
    ("gardening", "Gardening", "Gardening", "fa-solid fa-seedling", True),
    ("bundles", "Bundle Pack", "Bundle Pack", "fa-solid fa-box-open", False),
]

# name, unit, price ₹, old price ₹, rating, image file, category, popular, new
P = [
    ("Apple", "1 KG", 180, 220, 4.8, "apple.png", "vegetables", True, False),
    ("Chili", "250 G", 30, None, 4.5, "chilli.png", "vegetables", False, False),
    ("Onion", "1 KG", 40, None, 4.6, "red-onions.png", "vegetables", False, False),
    ("Orange", "1 KG", 120, 150, 4.7, "orange.png", "vegetables", False, False),
    ("Banana", "1 Dozen", 60, None, 4.9, "banana.png", "vegetables", True, True),
    ("Lemon", "500 G", 50, None, 4.4, "lemon.png", "vegetables", False, False),
    ("Potato", "1 KG", 35, 45, 4.6, "potatoes.png", "vegetables", True, False),
    ("Garlic", "500 G", 110, None, 4.5, "garlic.png", "vegetables", False, False),
    ("Tomato", "1 KG", 40, None, 4.8, "tomato.png", "vegetables", True, True),
    ("Broccoli", "1 PC", 90, None, 4.6, "broccoli.png", "vegetables", False, False),
    ("Carrot", "1 KG", 60, None, 4.7, "carrots.png", "vegetables", False, False),
    ("Cucumber", "1 KG", 50, None, 4.3, "cucumber.png", "vegetables", False, False),
    ("Strawberry", "500 G", 140, 200, 4.9, "strawberries.png", "vegetables", False, False),
    ("Mango", "1 KG", 160, None, 4.8, "mango.png", "vegetables", False, True),
    ("Avocado", "2 PCS", 299, None, 4.6, "avocado.png", "vegetables", False, False),
    ("Pineapple", "1 PC", 90, None, 4.5, "pineapple.png", "vegetables", False, False),

    ("Salmon", "500 G", 1199, 1499, 4.9, "salmon.png", "meat", True, False),
    ("Chicken", "1 KG", 260, None, 4.7, "chicken.png", "meat", True, False),
    ("Beef", "1 KG", 480, None, 4.6, "beef.png", "meat", False, False),
    ("Fish", "1 KG", 350, None, 4.5, "fish.png", "meat", False, False),
    ("Prawns", "500 G", 499, 599, 4.8, "prawns.png", "meat", False, True),
    ("Lamb", "1 KG", 750, None, 4.6, "lamb.png", "meat", False, False),
    ("Bacon", "250 G", 399, None, 4.7, "bacon.png", "meat", False, False),
    ("Tuna", "500 G", 549, None, 4.5, "tuna.png", "meat", False, False),
    ("Duck", "1 PC", 899, None, 4.4, "duck.png", "meat", False, False),

    ("Milk", "1 L", 68, None, 4.7, "milk.png", "baby", True, False),
    ("Eggs", "12 PCS", 84, None, 4.8, "eggs.png", "baby", True, False),
    ("Cheese", "200 G", 140, None, 4.6, "cheese.png", "baby", False, False),
    ("Yogurt", "900 G", 120, None, 4.6, "yogurt.png", "baby", False, False),
    ("Butter", "500 G", 285, None, 4.5, "butter.png", "baby", False, False),
    ("Baby Lotion", "300 ML", 299, 375, 4.7, "baby-lotion.png", "baby", False, False),
    ("Baby Wipes", "80 PCS", 149, None, 4.8, "baby-wipes.png", "baby", False, False),
    ("Pacifier", "1 PC", 199, None, 4.5, "pacifier-pink.png", "baby", False, False),
    ("Kids Toothbrush", "1 PC", 49, None, 4.4, "kids-toothbrush.png", "baby", False, False),

    ("Ginger", "250 G", 40, None, 4.4, "ginger.png", "medicine", False, False),
    ("Honey", "500 G", 249, None, 4.9, "honey.png", "medicine", False, False),
    ("First Aid Kit", "1 Kit", 599, 799, 4.8, "first-aid-kit.png", "medicine", False, False),
    ("Hand Sanitizer", "500 ML", 199, None, 4.6, "hand-sanitizer.png", "medicine", False, False),
    ("Face Mask", "10 PCS", 149, None, 4.5, "face-mask.png", "medicine", False, False),
    ("Vitamin C", "20 Tabs", 129, None, 4.7, "vitamin-c.png", "medicine", False, True),

    ("Ballpoint Pen", "1 PC", 20, None, 4.5, "ballpoint-pen.png", "office", False, False),
    ("Scissors", "1 PC", 79, None, 4.6, "scissors.png", "office", False, False),
    ("Calculator", "1 PC", 899, 1199, 4.8, "calculator.png", "office", False, False),
    ("Colored Pencils", "24 PCS", 180, None, 4.9, "colored-pencils.png", "office", False, True),
    ("Stapler", "1 PC", 149, None, 4.4, "stapler.png", "office", False, False),
    ("Sticky Notes", "12 Pads", 199, None, 4.7, "sticky-notes.png", "office", False, False),

    ("Mascara", "10 ML", 349, None, 4.6, "mascara.png", "beauty", False, False),
    ("Eyeshadow Palette", "1 PC", 799, 1099, 4.8, "eyeshadow-palette.png", "beauty", False, False),
    ("Face Powder", "15 G", 299, None, 4.5, "face-powder.png", "beauty", False, False),
    ("Red Lipstick", "1 PC", 249, None, 4.7, "red-lipstick.png", "beauty", False, True),
    ("Nail Polish", "12 ML", 129, None, 4.6, "nail-polish.png", "beauty", False, False),
    ("Hand Soap", "475 ML", 199, None, 4.7, "hand-soap.png", "beauty", False, False),
    ("Body Wash", "500 ML", 299, None, 4.5, "body-wash.png", "beauty", False, False),

    ("Spinach", "1 Bunch", 30, None, 4.5, "spinach.png", "gardening", False, False),
    ("Pumpkin", "1 PC", 60, None, 4.4, "pumpkin.png", "gardening", False, False),
    ("Watering Can", "5 L", 349, None, 4.7, "watering-can.png", "gardening", False, False),
    ("Garden Gloves", "1 Pair", 199, None, 4.6, "garden-gloves.png", "gardening", False, False),
    ("Hand Trowel", "1 PC", 249, None, 4.5, "hand-trowel.png", "gardening", False, False),
    ("Plant Pot", "1 PC", 399, 499, 4.8, "plant-pot.png", "gardening", False, False),
    ("House Plant", "1 PC", 599, None, 4.9, "house-plant.png", "gardening", False, True),
]

# name, contents, price ₹, old price ₹, rating, image
BUNDLES = [
    ("Big Pack", "Mango, Avocado, Cucumber +3", 1199, 1449, 4.9, "big_basket.png"),
    ("Large Pack", "Potato, Onion, Garlic +2", 799, 949, 4.8, "large_basket.png"),
    ("Small Pack", "Tomato, Chili, Lemon", 299, None, 4.7, "small_basket.png"),
]

# starter product descriptions per category (edit any of them in the admin)
DESCRIPTIONS = {
    "vegetables": "Fresh, hand-picked {n} sourced directly from trusted local farms. Carefully packed to stay crisp and full of flavour until it reaches your kitchen.",
    "meat": "Fresh {n}, cleaned and cut by experienced butchers and delivered chilled so it stays fresh until you cook it.",
    "baby": "Gentle, trusted {n} for your little ones and the whole family. Quality-checked and stored at the right temperature.",
    "medicine": "{N} for everyday health and wellness. Sourced from certified suppliers and sealed for safety.",
    "office": "Reliable {n} for home, school and the office. Durable, easy to use and great value.",
    "beauty": "Pamper yourself with {n}. Dermatologically tested, cruelty-free and made for an everyday glow.",
    "gardening": "Grow something beautiful with {n}. Everything you need for a greener home and garden.",
}

TESTIMONIALS = [
    ("James Brooks", 5, "client-1.jpg", "Fresh vegetables delivered right to my door every morning. The quality is excellent and the prices are better than my local market."),
    ("Robert Harlan", 4.5, "client-2.jpg", "The bundle packs save me so much time. Everything my family needs for the week arrives in one box, neatly packed and always on time."),
    ("Emma Murphy", 5, "client-3.jpg", "Ordering takes less than a minute, and free delivery is a huge bonus. The fruits are always ripe and tasty."),
]


def attach(field, filename):
    """Copy a starter image from static/images into media storage (only once)."""
    if field and field.name and field.storage.exists(field.name):
        return
    src = IMAGES / filename
    if src.exists():
        with src.open("rb") as fh:
            field.save(filename, File(fh), save=False)


class Command(BaseCommand):
    help = "Add the starter categories, products, bundles, deal, promo codes, testimonials and site settings."

    def add_arguments(self, parser):
        parser.add_argument("--update", action="store_true",
                            help="Also reset existing starter products/categories to the values in this file.")

    def handle(self, *args, update=False, **opts):
        created = {"categories": 0, "products": 0}

        cats = {}
        for i, (slug, name, title, icon, menu) in enumerate(CATEGORIES):
            values = {"name": name, "title": title, "icon": icon, "order": i, "show_in_menu": menu}
            cat = Category.objects.filter(slug=slug).first()
            if cat is None:
                cat = Category.objects.create(slug=slug, **values)
                created["categories"] += 1
            elif update:
                Category.objects.filter(pk=cat.pk).update(**values)
            cats[slug] = cat

        def upsert(order, name, unit, price, old, rating, image, cat, popular=False, new=False, bundle=False, desc=""):
            product = Product.objects.filter(name=name, category=cats[cat]).first()
            is_new_row = product is None
            if not is_new_row and not update:
                return product
            product = product or Product(name=name, category=cats[cat])
            product.unit = unit
            product.price = Decimal(str(price))
            product.old_price = Decimal(str(old)) if old else None
            product.rating = Decimal(str(rating))
            product.is_popular, product.is_new, product.is_bundle = popular, new, bundle
            product.order = order
            if bundle:
                product.description = desc
            elif not product.description:
                text = DESCRIPTIONS[cat]
                product.description = text.replace("{n}", name.lower()).replace("{N}", name)
            attach(product.image, image)
            product.save()
            created["products"] += is_new_row
            return product

        for i, (name, unit, price, old, rating, image, cat, popular, new) in enumerate(P):
            upsert(i, name, unit, price, old, rating, image, cat, popular, new)
        for i, (name, desc, price, old, rating, image) in enumerate(BUNDLES):
            upsert(i, name, "1 Box", price, old, rating, image, "bundles", bundle=True, desc=desc)

        strawberry = Product.objects.filter(name="Strawberry").first()
        if strawberry and not Deal.objects.exists():
            Deal.objects.create(product=strawberry, headline="Fresh Strawberries")

        for code, percent, min_order in [("FRESH10", 10, 0), ("GREEN20", 20, 999)]:
            promo, made = PromoCode.objects.get_or_create(code=code, defaults={"percent": percent, "min_order": min_order})
            if update and not made:
                promo.percent, promo.min_order = percent, min_order
                promo.save()

        for i, (name, rating, photo, text) in enumerate(TESTIMONIALS):
            t = Testimonial.objects.filter(name=name).first()
            if t and not update:
                continue
            t = t or Testimonial(name=name)
            t.text, t.rating, t.order = text, Decimal(str(rating)), i
            attach(t.photo, photo)
            t.save()

        SiteSettings.load()  # creates the settings row with rupee defaults if missing

        self.stdout.write(self.style.SUCCESS(
            f"Catalogue ready: {Category.objects.count()} categories, {Product.objects.items().count()} products, "
            f"{Product.objects.bundles().count()} bundles, {PromoCode.objects.count()} promo codes, "
            f"{Testimonial.objects.count()} testimonials "
            f"(new this run: {created['categories']} categories, {created['products']} products"
            f"{'; existing items updated' if update else ''})."))
