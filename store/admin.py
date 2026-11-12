from django.contrib import admin
from django.db.models import Count, Sum
from django.utils.html import format_html

from django.shortcuts import redirect
from django.urls import reverse

from .currency import format_inr
from .models import (Category, Deal, NewsletterSubscriber, Order, OrderItem, Product,
                     PromoCode, SiteSettings, Testimonial, WishlistItem)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """A single settings page: the list view jumps straight to the edit form."""
    fieldsets = [
        ("Store", {"fields": ["store_name"]}),
        ("Announcement bar", {"fields": ["show_announcement", "announcement"]}),
        ("Delivery (used by the cart & checkout)", {"fields": ["free_delivery_over", "delivery_fee", "delivery_minutes"]}),
        ("Home page hero", {"fields": ["hero_badge", "hero_title", "hero_highlight", "hero_title_end", "hero_subtitle",
                                       "happy_customers", "store_rating"]}),
        ("Footer & contact", {"fields": ["footer_about", "phone", "email", "address"]}),
        ("Social links (leave empty to hide)", {"fields": ["facebook_url", "instagram_url", "twitter_url", "youtube_url"]}),
    ]

    def changelist_view(self, request, extra_context=None):
        obj = SiteSettings.load()
        return redirect(reverse("admin:store_sitesettings_change", args=[obj.pk]))

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


def thumb(image, size=48):
    if not image:
        return "—"
    return format_html('<img src="{}" style="width:{}px;height:{}px;object-fit:contain;'
                       'background:#f1faf3;border-radius:8px;padding:2px">', image.url, size, size)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "icon_preview", "product_count", "order", "show_in_menu"]
    list_editable = ["order", "show_in_menu"]
    prepopulated_fields = {"slug": ["name"]}

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_count=Count("products"))

    @admin.display(description="Products", ordering="_count")
    def product_count(self, obj):
        return obj._count

    @admin.display(description="Icon")
    def icon_preview(self, obj):
        return format_html('<i class="{}"></i> <code>{}</code>', obj.icon, obj.icon)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["image_thumb", "name", "category", "price", "old_price", "stock", "rating",
                    "is_popular", "is_new", "is_bundle", "is_active"]
    list_display_links = ["image_thumb", "name"]
    list_editable = ["price", "old_price", "stock", "is_popular", "is_new", "is_active"]
    list_filter = ["category", "is_active", "is_popular", "is_new", "is_bundle"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ["name"]}
    readonly_fields = ["image_preview", "created_at"]
    list_per_page = 50
    fieldsets = [
        (None, {"fields": ["name", "slug", "category", "unit", "description"]}),
        ("Price & stock", {"fields": ["price", "old_price", "stock", "rating"]}),
        ("Image", {"fields": ["image", "image_preview"]}),
        ("Display", {"fields": ["is_active", "is_popular", "is_new", "is_bundle", "order", "created_at"]}),
    ]
    actions = ["mark_popular", "unmark_popular", "restock"]

    @admin.display(description="")
    def image_thumb(self, obj):
        return thumb(obj.image)

    @admin.display(description="Preview")
    def image_preview(self, obj):
        return thumb(obj.image, 160)

    @admin.action(description="Show in Popular Product")
    def mark_popular(self, request, qs):
        qs.update(is_popular=True)

    @admin.action(description="Remove from Popular Product")
    def unmark_popular(self, request, qs):
        qs.update(is_popular=False)

    @admin.action(description="Restock to 100")
    def restock(self, request, qs):
        qs.update(stock=100)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["product", "name", "unit", "price", "quantity", "line_total"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["number", "full_name", "phone", "city", "item_count", "total", "payment_method", "status", "created_at"]
    list_editable = ["status"]
    list_filter = ["status", "payment_method", "created_at"]
    search_fields = ["number", "full_name", "email", "phone"]
    date_hierarchy = "created_at"
    readonly_fields = ["number", "user", "subtotal", "discount", "delivery_fee", "total", "promo_code", "created_at", "updated_at"]
    inlines = [OrderItemInline]
    fieldsets = [
        ("Order", {"fields": ["number", "status", "user", "created_at", "updated_at"]}),
        ("Customer", {"fields": ["full_name", "email", "phone", "address", "city", "note", "payment_method"]}),
        ("Amounts", {"fields": ["subtotal", "discount", "promo_code", "delivery_fee", "total"]}),
    ]

    def changelist_view(self, request, extra_context=None):
        stats = Order.objects.exclude(status=Order.Status.CANCELLED).aggregate(revenue=Sum("total"), orders=Count("id"))
        extra_context = {**(extra_context or {}), "title": (
            f"Orders — {stats['orders'] or 0} orders · {format_inr(stats['revenue'] or 0)} revenue (excl. cancelled)")}
        return super().changelist_view(request, extra_context)


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ["code", "percent", "min_order", "valid_until", "is_active"]
    list_editable = ["is_active"]


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ["headline", "product", "is_active", "created_at"]
    list_editable = ["is_active"]
    autocomplete_fields = ["product"]


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ["photo_thumb", "name", "rating", "is_active", "order"]
    list_editable = ["is_active", "order"]

    @admin.display(description="")
    def photo_thumb(self, obj):
        return thumb(obj.photo, 36)


@admin.register(NewsletterSubscriber)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ["email", "created_at"]
    search_fields = ["email"]


@admin.register(WishlistItem)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ["user", "product", "created_at"]
    list_filter = ["product__category"]
