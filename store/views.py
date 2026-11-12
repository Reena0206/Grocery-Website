from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .cart import Cart
from .forms import CheckoutForm, SignUpForm
from .models import Category, Deal, Order, OrderItem, Product, Testimonial

ORDERS_SESSION_KEY = "guest_orders"


def home(request):
    categories = Category.objects.filter(show_in_menu=True).annotate(
        count=Count("products", filter=Q(products__is_active=True))
    )
    deal = Deal.objects.filter(is_active=True, product__is_active=True).select_related("product").first()
    cheapest_bundle = Product.objects.bundles().order_by("price").first()
    veg_max_off = max((p.discount_percent for p in Product.objects.items().filter(category__slug="vegetables")), default=0)
    return render(request, "store/home.html", {
        "categories": categories,
        "category_counts": {c.slug: c.count for c in categories},
        "bundle_from": cheapest_bundle.price if cheapest_bundle else None,
        "veg_max_off": veg_max_off,
        "deal": deal,
        "testimonials": Testimonial.objects.filter(is_active=True)[:6],
    })


def shop(request, slug=None):
    """All categories page; /shop/<slug>/ opens with that category selected."""
    category = get_object_or_404(Category, slug=slug, show_in_menu=True) if slug else None
    return render(request, "store/shop.html", {"category": category})


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.active().select_related("category"), slug=slug)
    return render(request, "store/product_detail.html", {"product": product})


def checkout(request):
    cart = Cart(request)
    lines = cart.lines()
    if not lines:
        messages.info(request, "Your cart is empty — add something tasty first!")
        return redirect("home")

    initial = {}
    if request.user.is_authenticated:
        u = request.user
        initial = {"full_name": u.get_full_name() or u.username, "email": u.email}
        last = u.orders.first()
        if last:
            initial.update(phone=last.phone, address=last.address, city=last.city)

    form = CheckoutForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            # lock rows and re-check stock so two buyers can't take the last item
            locked = Product.objects.select_for_update().in_bulk([p.id for p, _ in lines])
            problems = [p.name for p, q in lines if locked[p.id].stock < q]
            if problems:
                messages.error(request, f"Sorry, not enough stock for: {', '.join(problems)}. Please update your cart.")
                return redirect("checkout")

            totals = cart.totals()
            order = form.save(commit=False)
            order.user = request.user if request.user.is_authenticated else None
            order.subtotal = totals["subtotal"]
            order.discount = totals["discount"]
            order.delivery_fee = totals["delivery"]
            order.total = totals["total"]
            order.promo_code = totals["promo"] or ""
            order.save()
            OrderItem.objects.bulk_create([
                OrderItem(order=order, product=p, name=p.name, unit=p.unit, price=p.price, quantity=q)
                for p, q in lines
            ])
            for p, q in lines:
                Product.objects.filter(pk=p.pk).update(stock=F("stock") - q)

        cart.clear()
        guest_orders = request.session.get(ORDERS_SESSION_KEY, [])
        request.session[ORDERS_SESSION_KEY] = guest_orders + [order.number]
        return redirect(f"{order.get_absolute_url()}?placed=1")

    return render(request, "store/checkout.html", {
        "form": form,
        "lines": [(p, q, p.price * q) for p, q in lines],
        "totals": cart.totals(),
    })


def order_detail(request, number):
    order = get_object_or_404(Order.objects.prefetch_related("items"), number=number)
    owns = request.user.is_authenticated and order.user_id == request.user.id
    placed_here = number in request.session.get(ORDERS_SESSION_KEY, [])
    if not (owns or placed_here or request.user.is_staff):
        raise Http404
    return render(request, "store/order_detail.html", {
        "order": order,
        "just_placed": request.GET.get("placed") == "1",
        "steps": ["Placed", "Confirmed", "Packed", "On the way", "Delivered"],
    })


@login_required
def my_orders(request):
    orders = request.user.orders.prefetch_related("items")
    return render(request, "store/my_orders.html", {"orders": orders})


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
        except IntegrityError:
            # two sign-ups with the same username arrived at the same moment (e.g. double click)
            form.add_error("username", "This username was just taken. If it was you, please log in.")
        else:
            login(request, user)
            messages.success(request, f"Welcome to eGrocery, {user.first_name or user.username}!")
            next_url = request.GET.get("next")
            if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                next_url = "home"
            return redirect(next_url)
    return render(request, "registration/signup.html", {"form": form})
