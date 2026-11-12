from django.contrib.auth import views as auth_views
from django.urls import path

from . import api, views

urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.shop, name="shop"),
    path("shop/<slug:slug>/", views.shop, name="shop_category"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.my_orders, name="my_orders"),
    path("orders/<str:number>/", views.order_detail, name="order_detail"),

    # accounts
    path("accounts/signup/", views.signup, name="signup"),
    path("accounts/login/", auth_views.LoginView.as_view(redirect_authenticated_user=True), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),

    # JSON API
    path("api/products/", api.products, name="api_products"),
    path("api/cart/", api.cart, name="api_cart"),
    path("api/cart/promo/", api.promo, name="api_promo"),
    path("api/wishlist/", api.wishlist, name="api_wishlist"),
    path("api/newsletter/", api.newsletter, name="api_newsletter"),
]
