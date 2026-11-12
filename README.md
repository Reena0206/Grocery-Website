# eGrocery — Django grocery store

A full online grocery store: product catalogue, cart, promo codes, checkout, user accounts,
order tracking and an admin dashboard to run the shop.

## Features

| Customers | Shop owner (admin at `/admin/`) |
|---|---|
| Browse 7 categories / 60+ products, search with live suggestions, sort | Add / edit products, prices, discounts, stock and images |
| Quick view, product pages, wishlist | Mark products as Popular / New / Bundle |
| Server-side cart with free-delivery progress and promo codes | See every order, change its status (Pending → Delivered) |
| Checkout (cash or card on delivery) — stock is checked and reduced | Revenue & order count on the Orders page |
| Sign up / log in, “My Orders” with live status tracker | Promo codes, Deal of the Day, testimonials, newsletter list |
| Dark mode, fully responsive | |

## Run it on your computer

```bash
# 1. create a virtual environment and install packages
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt

# 2. create the database and load the starter catalogue
python manage.py migrate
python manage.py seed_store

# 3. create your admin login
python manage.py createsuperuser

# 4. start the site
python manage.py runserver
```

Open <http://127.0.0.1:8000> for the shop and <http://127.0.0.1:8000/admin/> for the dashboard.

Run the tests with `python manage.py test store`.

Starter promo codes: **FRESH10** (10% off) and **GREEN20** (20% off orders over ₹999) — change them in the admin.

### Managing the shop (all from `/admin/`)

| What | Where in the admin |
|---|---|
| Categories (name, icon, order, show on home) | Store → Categories |
| Products & bundles (price in ₹, discount, stock, image, description, Popular/New) | Store → Products |
| Deal of the Day | Store → Deals |
| Promo codes | Store → Promo codes |
| Customer reviews | Store → Testimonials |
| Announcement bar, hero text, free-delivery amount & delivery fee, contact details, social links | Store → **Site settings** |
| Orders & their status | Store → Orders |

All prices are in **Indian rupees (₹)**. Images uploaded in the admin are automatically resized to 800px.

`python manage.py seed_store` only **adds** missing starter data and never overwrites your edits
(it is safe to run on every deploy). `python manage.py seed_store --update` resets the starter
products to their original values.

## Project layout

```
egrocery/            settings, URLs, WSGI
store/
  models.py          SiteSettings, Category, Product, Order, OrderItem, PromoCode, Deal, Testimonial, Wishlist, Newsletter
  currency.py        rupee formatting (₹1,23,456) — used by the |inr template filter
  cart.py            session cart — all prices & totals calculated on the server
  views.py           pages: home, product, checkout, order, my orders, sign up
  api.py             JSON API used by the frontend (cart, promo, wishlist, newsletter)
  admin.py           admin dashboard
  management/commands/seed_store.py   loads the starter catalogue
  tests.py
templates/           HTML templates
static/              CSS, JavaScript and site images
media/               uploaded product images (created automatically, not in git)
```

## Going live

The project is production-ready: settings come from environment variables (see `.env.example`),
static files are served by WhiteNoise, and PostgreSQL is supported through `DATABASE_URL`.

### Option A — Render.com (easiest)

1. Push this project to a GitHub repository.
2. On Render: **New + → Blueprint**, pick the repository. `render.yaml` creates the web service,
   a PostgreSQL database and a disk for uploaded images.
3. Fill in `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_PASSWORD`
   when asked — your admin account is created on the first deploy.
4. Add your own domain in Render’s settings and put it in `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.

### Option B — any VPS / other host

```bash
export DEBUG=False SECRET_KEY=... ALLOWED_HOSTS=yourdomain.com \
       CSRF_TRUSTED_ORIGINS=https://yourdomain.com DATABASE_URL=postgres://...
./build.sh                       # install, collectstatic, migrate, seed
gunicorn egrocery.wsgi           # run behind nginx / a load balancer with HTTPS
```

### Notes for production

- **Uploaded images** are stored in `MEDIA_ROOT`. Use a persistent disk (as in `render.yaml`) or
  move them to cloud storage (S3 / Cloudinary) for larger shops.
- **Online card payments** are not included — orders are paid on delivery. Stripe or Razorpay
  can be added at the checkout step.
- **Order e-mails** are not sent yet; configure an e-mail provider (`EMAIL_*` settings) to add them.
- Image credits for the starter catalogue are in `static/images/CREDITS.txt` (linked in the footer).
