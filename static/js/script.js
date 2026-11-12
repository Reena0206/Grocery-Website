/* =========================================================
   eGrocery frontend
   - Product data, cart & wishlist come from Django (#store-data)
   - Every change is sent to the JSON API; the server is the source of truth
   ========================================================= */
const STATE = JSON.parse(document.getElementById("store-data").textContent);
const URLS = STATE.urls;
const products = STATE.products.filter((p) => !p.bundle);
const bundles = STATE.products.filter((p) => p.bundle);
const byId = new Map(STATE.products.map((p) => [p.id, p]));
let cart = STATE.cart;
let wishlist = STATE.wishlist;

const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);
const INR0 = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
const INR2 = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 2 });
const fmt = (n) => (Number.isInteger(n) ? INR0 : INR2).format(n);   // 1199 -> ₹1,199
const qtyOf = (id) => cart.qty[String(id)] || 0;
const isHome = document.body.classList.contains("page-home");
const isCheckout = document.body.classList.contains("page-checkout");
let cartDirty = false;   // on the checkout page, reload the summary after the drawer closes

/* ---------- category copy for quick view / product page ---------- */
const FOOD = ["vegetables", "meat", "bundles"];
const CAT_INFO = {
  food:      { desc: (n) => `Fresh, hand-picked ${n} sourced directly from trusted local farms. Carefully packed to stay crisp and full of flavour until it reaches your kitchen.`,
               points: [["fa-leaf", "Organic & pesticide-free"], ["fa-truck", "Delivered within 30 minutes"], ["fa-rotate-left", "Easy freshness guarantee"]] },
  baby:      { desc: (n) => `Gentle, trusted ${n} for your little ones and the whole family. Quality-checked and stored at the right temperature.`,
               points: [["fa-shield-heart", "Safe & quality checked"], ["fa-truck", "Delivered within 30 minutes"], ["fa-rotate-left", "Easy returns"]] },
  medicine:  { desc: (n) => `${n[0].toUpperCase() + n.slice(1)} for everyday health and wellness. Sourced from certified suppliers and sealed for safety.`,
               points: [["fa-certificate", "Certified suppliers"], ["fa-box", "Sealed packaging"], ["fa-truck", "Delivered within 30 minutes"]] },
  office:    { desc: (n) => `Reliable ${n} for home, school and the office. Durable, easy to use and great value.`,
               points: [["fa-check", "Durable quality"], ["fa-tags", "Best price guarantee"], ["fa-truck", "Same-day delivery"]] },
  beauty:    { desc: (n) => `Pamper yourself with ${n}. Dermatologically tested, cruelty-free and made for everyday glow.`,
               points: [["fa-flask", "Dermatologically tested"], ["fa-paw", "Cruelty-free"], ["fa-rotate-left", "Easy returns"]] },
  gardening: { desc: (n) => `Grow something beautiful with ${n}. Everything you need for a greener home and garden.`,
               points: [["fa-seedling", "Garden-ready quality"], ["fa-hand-holding-heart", "Great for beginners"], ["fa-truck", "Same-day delivery"]] },
};
const infoFor = (p) => CAT_INFO[FOOD.includes(p.cat) ? "food" : p.cat] || CAT_INFO.food;
// product text comes from the database (Admin → Products → description); fall back to a generated line
const describe = (p) => p.bundle
  ? `A hand-packed box with ${p.desc.toLowerCase()} — everything you need for the week, picked fresh this morning.`
  : (p.desc || infoFor(p).desc(p.name.toLowerCase()));
const pointsHTML = (p) => infoFor(p).points.map(([i, t]) => `<li><i class="fa-solid ${i}"></i> ${t}</li>`).join("");
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* =========================================================
   API
   ========================================================= */
const CSRF = document.querySelector('meta[name="csrf-token"]').content;

async function api(url, body) {
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": CSRF },
      credentials: "same-origin",
      body: JSON.stringify(body || {}),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok && !data.message && !data.error) data.error = "Something went wrong. Please try again.";
    return { ok: res.ok, ...data };
  } catch {
    return { ok: false, error: "You seem to be offline. Please check your connection." };
  }
}

/* =========================================================
   RENDER — product cards
   ========================================================= */
function cardHTML(p, showCat = false) {
  const liked = wishlist.includes(p.id);
  const qty = qtyOf(p.id);
  const off = p.oldPrice ? Math.round((1 - p.price / p.oldPrice) * 100) : 0;
  const badge = off ? `<span class="card-badge">-${off}%</span>` : p.isNew ? `<span class="card-badge new">New</span>` : "";
  const action = p.stock <= 0
    ? `<span class="sold-out">Sold out</span>`
    : qty
      ? `<div class="stepper"><button data-dec="${p.id}" aria-label="Decrease">−</button><span>${qty}</span><button data-inc="${p.id}" aria-label="Increase">+</button></div>`
      : `<button class="add-btn" data-add="${p.id}" aria-label="Add ${esc(p.name)} to cart"><i class="fa-solid fa-plus"></i></button>`;

  return `
    <article class="card">
      <div class="card-media" data-view="${p.id}">
        ${badge}
        <img src="${p.img}" alt="${esc(p.name)}" loading="lazy">
        <span class="card-quick"><i class="fa-regular fa-eye"></i> Quick view</span>
      </div>
      <button class="card-fav ${liked ? "liked" : ""}" data-wish="${p.id}" aria-label="${liked ? "Remove from" : "Add to"} wishlist"><i class="fa-${liked ? "solid" : "regular"} fa-heart"></i></button>
      <div class="card-body">
        ${showCat ? `<span class="card-cat">${esc(p.catTitle)}</span>` : ""}
        <h3><a href="${p.url}">${esc(p.name)}</a></h3>
        ${p.bundle
          ? `<p class="desc">${esc(p.desc)}</p>`
          : `<div class="card-meta"><span>${esc(p.unit)}</span><span class="dot"></span><span class="rating"><i class="fa-solid fa-star"></i>${p.rating}</span></div>`}
        <div class="card-bottom">
          <p class="price">${fmt(p.price)}${p.oldPrice ? `<s>${fmt(p.oldPrice)}</s>` : ""}</p>
          ${action}
        </div>
      </div>
    </article>`;
}

/* ---------- re-render a list without losing its horizontal scroll position ---------- */
function setHTML(el, html) {
  const left = el.scrollLeft;
  el.innerHTML = html;
  if (left) { el.style.scrollBehavior = "auto"; el.scrollLeft = left; el.style.scrollBehavior = ""; }
}

/* ---------- home: "Best of each category" — tabs + one scrolling row ---------- */
let aisleCat = STATE.categories.find((c) => c.count)?.slug;

function renderAisle() {
  const row = $("#aisleRow");
  if (!row || !aisleCat) return;
  const cat = STATE.categories.find((c) => c.slug === aisleCat);
  const items = products.filter((p) => p.cat === aisleCat)
    .sort((a, b) => b.rating - a.rating).slice(0, 10);
  setHTML(row, items.map((p) => cardHTML(p)).join(""));
  $$("#aisleTabs .tab").forEach((t) => {
    const on = t.dataset.tab === aisleCat;
    t.classList.toggle("active", on);
    t.setAttribute("aria-selected", on);
  });
  const link = $("#aisleLink");
  link.href = cat.url;
  link.innerHTML = `View all ${cat.count} in ${esc(cat.title)} <i class="fa-solid fa-arrow-right"></i>`;
}

/* ---------- shop page: sidebar filters + grid ---------- */
const shopEl = $("#shopPage");
const shopState = {
  cat: shopEl?.dataset.initialCat || "",
  q: (shopEl?.dataset.q || "").toLowerCase(),
  sort: "default", max: Infinity, sale: false, isNew: false, stock: false,
};

function shopList() {
  let list = products.filter((p) =>
    (!shopState.cat || p.cat === shopState.cat) &&
    (!shopState.q || p.name.toLowerCase().includes(shopState.q) || p.catTitle.toLowerCase().includes(shopState.q)) &&
    p.price <= shopState.max &&
    (!shopState.sale || p.oldPrice) &&
    (!shopState.isNew || p.isNew) &&
    (!shopState.stock || p.stock > 0));
  const sorters = { low: (a, b) => a.price - b.price, high: (a, b) => b.price - a.price,
                    rating: (a, b) => b.rating - a.rating, name: (a, b) => a.name.localeCompare(b.name) };
  if (sorters[shopState.sort]) list = [...list].sort(sorters[shopState.sort]);
  return list;
}

function renderShop(animate = false) {
  const grid = $("#shopGrid");
  if (!grid) return;
  const list = shopList();
  grid.classList.toggle("animate", animate);
  grid.innerHTML = list.map((p) => cardHTML(p, !shopState.cat)).join("");
  $("#resultCount").textContent = list.length;
  $("#shopEmpty").hidden = list.length > 0;
  const cat = STATE.categories.find((c) => c.slug === shopState.cat);
  $("#shopTitle").textContent = cat ? cat.title : "All Categories";
  $("#crumbCat").hidden = !cat;
  if (cat) $("#crumbCat b").textContent = cat.title;
  $$(".side-cat").forEach((b) => b.classList.toggle("active", b.dataset.shopCat === shopState.cat));
}

/* ---------- home: popular products ---------- */
function renderProducts() {
  const grid = $("#productGrid");
  if (grid) grid.innerHTML = products.filter((p) => p.popular).slice(0, 8).map((p) => cardHTML(p, true)).join("");
}

function renderBundles() {
  const grid = $("#bundleGrid");
  if (grid) grid.innerHTML = bundles.map((p) => cardHTML(p)).join("");
}

function renderRelated() {
  const grid = $("#relatedGrid");
  if (!grid) return;
  const exclude = +grid.dataset.exclude;
  const list = products.filter((p) => p.cat === grid.dataset.cat && p.id !== exclude).slice(0, 8);
  grid.innerHTML = list.length ? list.map((p) => cardHTML(p)).join("") : `<p class="muted">More products coming soon.</p>`;
}

/* =========================================================
   RENDER — cart & wishlist drawers
   ========================================================= */
function renderCart() {
  bumpBadge($("#cartCount"), cart.count);
  $("#cartHeadCount").textContent = cart.count ? `(${cart.count})` : "";

  $("#shipMsg").innerHTML = cart.freeLeft > 0
    ? `Add <b>${fmt(cart.freeLeft)}</b> more for <b>FREE delivery</b> 🚚`
    : `🎉 You've unlocked <b>FREE delivery!</b>`;
  $("#shipBar").style.width = cart.freePct + "%";

  $("#cartSubtotal").textContent = fmt(cart.subtotal);
  $("#discountRow").hidden = !cart.discount;
  $("#cartDiscount").textContent = "-" + fmt(cart.discount);
  $("#promoLabel").textContent = cart.promo || "";
  $("#promoNote").hidden = !cart.promoNote;
  $("#promoNote").textContent = cart.promoNote || "";
  $("#cartDelivery").textContent = cart.delivery ? fmt(cart.delivery) : "Free";
  $("#cartDelivery").className = cart.delivery ? "" : "green";
  $("#cartTotal").textContent = fmt(cart.total);
  renderOffers();
  $("#cartFoot").hidden = !cart.count;
  $("#cartExtras").hidden = !cart.count;
  $("#shipProgress").hidden = !cart.count;

  $("#cartItems").innerHTML = cart.items.length
    ? cart.items.map((p) => `
        <div class="line-item">
          <a href="${p.url}"><img src="${p.img}" alt="${esc(p.name)}"></a>
          <div class="line-info">
            <h4>${esc(p.name)}</h4>
            <small>${fmt(p.price)} · ${esc(p.unit)}</small><br>
            <div class="qty"><button data-dec="${p.id}" aria-label="Decrease">−</button><span>${p.qty}</span><button data-inc="${p.id}" aria-label="Increase">+</button></div>
          </div>
          <span class="line-price">${fmt(p.line)}</span>
          <button class="remove" data-remove="${p.id}" aria-label="Remove"><i class="fa-regular fa-trash-can"></i></button>
        </div>`).join("")
    : `<div class="drawer-empty"><i class="fa-solid fa-basket-shopping"></i>Your cart is empty<br><a class="btn" href="${URLS.home}#products" data-close>Start Shopping</a></div>`;
}

/* available promo codes — shown in the cart so shoppers know what they can unlock */
function offerHTML(o, btnAttr = "data-offer") {
  const state = o.applied ? "applied" : o.unlocked ? "ready" : "locked";
  const action = o.applied
    ? `<span class="offer-tag"><i class="fa-solid fa-check"></i> Applied</span>`
    : o.unlocked
      ? `<button type="button" class="offer-btn" ${btnAttr}="${esc(o.code)}">Apply</button>`
      : `<span class="offer-lock"><i class="fa-solid fa-lock"></i></span>`;
  const hint = o.applied
    ? `You're saving ${o.percent}% on this order`
    : o.unlocked
      ? `Unlocked — tap Apply to save ${o.percent}%`
      : `Add <b>${fmt(o.left)}</b> more to unlock`;
  return `
    <div class="offer ${state}">
      <div class="offer-pct">${o.percent}%<small>OFF</small></div>
      <div class="offer-info">
        <b class="offer-code">${esc(o.code)}</b>
        <small>${esc(o.desc)}</small>
        <small class="offer-hint">${hint}</small>
        ${state === "locked" ? `<div class="bar"><span style="width:${o.pct}%"></span></div>` : ""}
      </div>
      ${action}
    </div>`;
}

function renderOffers() {
  const box = $("#cartOffers");
  const offers = cart.offers || [];
  box.hidden = !offers.length;
  box.innerHTML = offers.length
    ? `<p class="offers-title"><i class="fa-solid fa-gift"></i> Available offers</p>` + offers.map((o) => offerHTML(o)).join("")
    : "";
}

function renderWishlist() {
  bumpBadge($("#wishCount"), wishlist.length);
  const items = wishlist.map((id) => byId.get(id)).filter(Boolean);
  $("#wishItems").innerHTML = items.length
    ? items.map((p) => `
        <div class="line-item">
          <a href="${p.url}"><img src="${p.img}" alt="${esc(p.name)}"></a>
          <div class="line-info"><h4>${esc(p.name)}</h4><small>${fmt(p.price)} · ${esc(p.unit)}</small></div>
          <button class="btn mini-add" data-add="${p.id}">Add</button>
          <button class="remove" data-wish="${p.id}" aria-label="Remove"><i class="fa-regular fa-trash-can"></i></button>
        </div>`).join("")
    : `<div class="drawer-empty"><i class="fa-regular fa-heart"></i>Your wishlist is empty<br><a class="btn" href="${URLS.home}#products" data-close>Discover Products</a></div>`;

  const pdWish = $(".pd-wish");
  if (pdWish) {
    const liked = wishlist.includes(+pdWish.dataset.wish);
    pdWish.classList.toggle("liked", liked);
    pdWish.innerHTML = `<i class="fa-${liked ? "solid" : "regular"} fa-heart"></i>`;
  }
}

function bumpBadge(el, value) {
  if (el.textContent !== String(value)) {
    el.textContent = value;
    el.classList.remove("bump");
    void el.offsetWidth;
    el.classList.add("bump");
  }
}

function refresh() {
  renderProducts();
  renderBundles();
  renderRelated();
  renderAisle();
  renderShop();
  renderCart();
  renderWishlist();
}

/* =========================================================
   ACTIONS (all go through the server)
   ========================================================= */
async function cartAction(action, id, qty) {
  const r = await api(URLS.cart, { action, product: id, qty });
  if (r.cart) { cart = r.cart; cartDirty = true; refresh(); }
  if (r.error) toast(`<i class="fa-solid fa-circle-exclamation err"></i>${esc(r.error)}`);
  else if (r.message) toast(`<i class="fa-solid fa-circle-info"></i>${esc(r.message)}`);
  return r;
}

async function addToCart(id, qty = 1) {
  const r = await cartAction("add", id, qty);
  if (r.cart && !r.message) toast(`<i class="fa-solid fa-circle-check"></i>${esc(byId.get(id)?.name || "Item")} added to cart`);
}

const changeQty = (id, delta) => cartAction("set", id, qtyOf(id) + delta);

async function toggleWish(id) {
  const r = await api(URLS.wishlist, { product: id });
  if (!r.wishlist) return toast(`<i class="fa-solid fa-circle-exclamation err"></i>${esc(r.error)}`);
  wishlist = r.wishlist;
  refresh();
  const name = esc(byId.get(id)?.name || "Item");
  toast(r.added ? `<i class="fa-solid fa-heart"></i>${name} saved to wishlist` : `<i class="fa-solid fa-heart-crack"></i>${name} removed from wishlist`);
}

let toastTimer;
function toast(html) {
  const t = $("#toast");
  t.innerHTML = html;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 2600);
}

/* =========================================================
   DRAWERS & MODALS
   ========================================================= */
const overlay = $("#overlay");
function openPanel(el) {
  closeAll();
  el.classList.add("open");
  overlay.classList.add("show");
  document.body.style.overflow = "hidden";
}
function closeAll() {
  if (isCheckout && cartDirty) { location.reload(); return; }
  $$(".drawer.open, .modal.open").forEach((d) => d.classList.remove("open"));
  overlay.classList.remove("show");
  document.body.style.overflow = "";
}
$("#cartBtn").addEventListener("click", () => openPanel($("#cartDrawer")));
$("#wishBtn").addEventListener("click", () => openPanel($("#wishDrawer")));
overlay.addEventListener("click", closeAll);
$$(".modal").forEach((m) => m.addEventListener("click", (e) => { if (e.target === m) closeAll(); }));
document.addEventListener("keydown", (e) => e.key === "Escape" && closeAll());

/* ---------- quick view ---------- */
let qvId = null, qvQty = 1;
function openQuickView(id) {
  const p = byId.get(id);
  if (!p) return;
  qvId = id; qvQty = 1;
  $("#qvImg").src = p.img; $("#qvImg").alt = p.name;
  $("#qvCat").textContent = p.catTitle;
  $("#qvName").textContent = p.name;
  $("#qvRating").innerHTML = `<i class="fa-solid fa-star"></i> ${p.rating} · <span>${esc(p.unit)}</span>`;
  $("#qvPrice").textContent = fmt(p.price);
  $("#qvOld").textContent = p.oldPrice ? fmt(p.oldPrice) : "";
  $("#qvDesc").textContent = describe(p);
  $("#qvPoints").innerHTML = pointsHTML(p);
  $("#qvQty").textContent = qvQty;
  $("#qvLink").href = p.url;
  $("#qvAdd").disabled = p.stock <= 0;
  $("#qvAdd").innerHTML = p.stock <= 0 ? "Sold out" : `<i class="fa-solid fa-bag-shopping"></i> Add To Cart`;
  openPanel($("#quickView"));
}
$("#qvMinus").addEventListener("click", () => { qvQty = Math.max(1, qvQty - 1); $("#qvQty").textContent = qvQty; });
$("#qvPlus").addEventListener("click", () => { qvQty = Math.min(99, qvQty + 1); $("#qvQty").textContent = qvQty; });
$("#qvAdd").addEventListener("click", async () => { closeAll(); await addToCart(qvId, qvQty); });

/* ---------- promo ---------- */
async function applyPromo(code) {
  const r = await api(URLS.promo, { code });
  if (r.cart) { cart = r.cart; cartDirty = true; }
  refresh();
  if (r.ok) {
    $("#promoInput").value = "";
    toast(`<i class="fa-solid fa-tag"></i>${esc(r.message)}`);
  } else {
    // keep the reason visible under the field, not just in a toast
    $("#promoNote").hidden = false;
    $("#promoNote").textContent = r.message || r.error;
    toast(`<i class="fa-solid fa-circle-xmark err"></i>${esc(r.message || r.error)}`);
  }
  return r;
}
$("#promoForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const code = $("#promoInput").value.trim();
  if (!code) { $("#promoInput").focus(); return; }
  applyPromo(code);
});
$("#cartOffers").addEventListener("click", (e) => {
  const btn = e.target.closest("[data-offer]");
  if (btn) { btn.disabled = true; applyPromo(btn.dataset.offer); }
});
$("#promoRemove").addEventListener("click", async () => {
  const r = await api(URLS.promo, { code: "" });
  if (r.cart) { cartDirty = true; }
  if (r.cart) { cart = r.cart; refresh(); toast(`<i class="fa-solid fa-tag"></i>Promo code removed`); }
});

/* =========================================================
   GLOBAL CLICK HANDLER
   ========================================================= */
document.addEventListener("click", (e) => {
  const t = e.target.closest("[data-add],[data-wish],[data-inc],[data-dec],[data-remove],[data-view],[data-close],[data-search],[data-open]");
  if (!t) return;
  const d = t.dataset;
  if (d.add) addToCart(+d.add);
  else if (d.wish) toggleWish(+d.wish);
  else if (d.inc) changeQty(+d.inc, 1);
  else if (d.dec) changeQty(+d.dec, -1);
  else if (d.remove) cartAction("remove", +d.remove);
  else if (d.view) { e.preventDefault(); openQuickView(+d.view); }
  else if (d.search) runSearch(d.search);
  else if (d.open) { e.preventDefault(); openPanel(document.getElementById(d.open)); }
  else if ("close" in d) closeAll();
});

/* =========================================================
   SEARCH (hero) + HOME PAGE
   ========================================================= */
const searchInput = $("#searchInput");
const suggest = $("#suggest");

function runSearch(term) {
  location.href = `${URLS.shop}?q=${encodeURIComponent(term.trim())}`;
}

if (searchInput) {
  searchInput.addEventListener("input", () => {
    const q = searchInput.value.trim().toLowerCase();
    if (!q) { suggest.hidden = true; return; }
    const matches = STATE.products.filter((p) => p.name.toLowerCase().includes(q)).slice(0, 6);
    suggest.innerHTML = matches.length
      ? matches.map((p) => `<li data-view="${p.id}"><img src="${p.img}" alt="">${esc(p.name)}<span>${fmt(p.price)}</span></li>`).join("")
        + `<li class="suggest-all" data-search="${esc(q)}">See all results for “${esc(q)}” <i class="fa-solid fa-arrow-right"></i></li>`
      : `<li>No matches for “${esc(q)}”</li>`;
    suggest.hidden = false;
  });
  document.addEventListener("click", (e) => { if (!e.target.closest("#searchForm")) suggest.hidden = true; });
  searchInput.addEventListener("keydown", (e) => { if (e.key === "Escape") suggest.hidden = true; });
}

if (isHome) {
  // category tabs
  $$("#aisleTabs .tab").forEach((t) => t.addEventListener("click", () => {
    aisleCat = t.dataset.tab;
    $("#aisleRow").scrollLeft = 0;
    renderAisle();
  }));
  $$("#aisles .row-arrow").forEach((b) => b.addEventListener("click", () => {
    const sc = $("#aisleRow");
    sc.scrollBy({ left: +b.dataset.scroll * sc.clientWidth * 0.8, behavior: "smooth" });
  }));

  // newsletter
  $("#newsForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const r = await api(URLS.newsletter, { email: $("#newsEmail").value });
    toast(`<i class="fa-solid ${r.ok ? "fa-envelope-circle-check" : "fa-circle-xmark err"}"></i>${esc(r.message || r.error)}`);
    if (r.ok) $("#newsEmail").value = "";
  });

  // hero counters
  const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
  $$("[data-count]").forEach((el) => {
    const target = parseFloat(el.dataset.count), decimals = +(el.dataset.dec || 0), start = performance.now();
    if (calm) { el.textContent = target.toFixed(decimals); return; }
    const step = (now) => {
      const p = Math.min(1, (now - start) / 1600);
      el.textContent = (target * (1 - Math.pow(1 - p, 3))).toFixed(decimals);
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  });
}

// deal countdown (to midnight)
if ($("#countdown")) {
  const tick = () => {
    const now = new Date(), end = new Date(now);
    end.setHours(24, 0, 0, 0);
    let s = Math.floor((end - now) / 1000);
    const h = Math.floor(s / 3600); s %= 3600;
    const m = Math.floor(s / 60); s %= 60;
    $("#cdH").textContent = String(h).padStart(2, "0");
    $("#cdM").textContent = String(m).padStart(2, "0");
    $("#cdS").textContent = String(s).padStart(2, "0");
  };
  tick();
  setInterval(tick, 1000);
}

/* =========================================================
   SHOP PAGE
   ========================================================= */
if (shopEl) {
  const shopUrl = (slug) => (slug ? STATE.categories.find((c) => c.slug === slug).url : URLS.shop);

  // counts + price slider range from the real catalogue
  $("#allCount").textContent = products.length;
  $$("[data-side-count]").forEach((el) => {
    el.textContent = STATE.categories.find((c) => c.slug === el.dataset.sideCount)?.count || 0;
  });
  const topPrice = Math.ceil(Math.max(...products.map((p) => p.price)));
  const maxPrice = topPrice > 500 ? Math.ceil(topPrice / 10) * 10 : topPrice;
  const range = $("#priceRange");
  range.min = 0; range.max = maxPrice; range.value = maxPrice; range.step = maxPrice > 500 ? 10 : 1;
  $("#priceLabel").textContent = fmt(maxPrice);

  $$(".side-cat").forEach((b) => b.addEventListener("click", () => {
    shopState.cat = b.dataset.shopCat;
    history.pushState({ cat: shopState.cat }, "", shopUrl(shopState.cat) + location.search);
    document.title = `${shopState.cat ? b.dataset.title : "All Categories"} – eGrocery`;
    renderShop(true);
    if (innerWidth <= 860) $("#shopSide").classList.remove("open");
    window.scrollTo({ top: shopEl.offsetTop - 90, behavior: "smooth" });
  }));
  window.addEventListener("popstate", (e) => {
    shopState.cat = e.state?.cat ?? shopEl.dataset.initialCat;
    renderShop(true);
  });
  history.replaceState({ cat: shopState.cat }, "");

  let typing;
  $("#shopSearch").addEventListener("input", (e) => {
    clearTimeout(typing);
    typing = setTimeout(() => { shopState.q = e.target.value.trim().toLowerCase(); renderShop(true); }, 150);
  });
  $("#shopSort").addEventListener("change", (e) => { shopState.sort = e.target.value; renderShop(true); });
  range.addEventListener("input", () => {
    shopState.max = +range.value;
    $("#priceLabel").textContent = fmt(+range.value);
    renderShop();
  });
  $("#onlySale").addEventListener("change", (e) => { shopState.sale = e.target.checked; renderShop(true); });
  $("#onlyNew").addEventListener("change", (e) => { shopState.isNew = e.target.checked; renderShop(true); });
  $("#onlyStock").addEventListener("change", (e) => { shopState.stock = e.target.checked; renderShop(true); });
  $("#filterToggle").addEventListener("click", () => $("#shopSide").classList.toggle("open"));

  const resetFilters = () => {
    Object.assign(shopState, { q: "", sort: "default", max: Infinity, sale: false, isNew: false, stock: false });
    $("#shopSearch").value = ""; $("#shopSort").value = "default";
    range.value = maxPrice; $("#priceLabel").textContent = fmt(maxPrice);
    ["#onlySale", "#onlyNew", "#onlyStock"].forEach((s) => ($(s).checked = false));
    renderShop(true);
  };
  $("#resetFilters").addEventListener("click", resetFilters);
  $("#shopEmptyReset").addEventListener("click", () => { shopState.cat = ""; history.pushState({ cat: "" }, "", URLS.shop); resetFilters(); });
}

/* =========================================================
   CHECKOUT PAGE: promo code box (reloads so the server-calculated totals update)
   ========================================================= */
if (isCheckout) {
  const msg = $("#checkoutPromoMsg");
  $("#checkoutPromo")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const input = $("#checkoutPromoInput");
    const code = input.value.trim();
    if (!code) { msg.hidden = false; msg.textContent = "Please type a promo code first."; input.focus(); return; }
    const btn = e.target.querySelector("button");
    btn.disabled = true; btn.textContent = "Applying…";
    const r = await api(URLS.promo, { code });
    if (r.ok) { location.reload(); return; }
    btn.disabled = false; btn.textContent = "Apply";
    msg.hidden = false; msg.textContent = r.message || r.error;
    input.select();
  });
  const offersBox = $("#checkoutOffers");
  const offers = cart.offers || [];
  if (offersBox && offers.length) {
    offersBox.hidden = false;
    offersBox.innerHTML = `<p class="offers-title"><i class="fa-solid fa-gift"></i> Available offers</p>` +
      offers.map((o) => offerHTML(o, "data-checkout-offer")).join("");
    offersBox.addEventListener("click", async (e) => {
      const btn = e.target.closest("[data-checkout-offer]");
      if (!btn) return;
      btn.disabled = true; btn.textContent = "Applying…";
      const r = await api(URLS.promo, { code: btn.dataset.checkoutOffer });
      if (r.ok) { location.reload(); return; }
      btn.disabled = false; btn.textContent = "Apply";
      msg.hidden = false; msg.textContent = r.message || r.error;
    });
  }
  $("#checkoutPromoRemove")?.addEventListener("click", async () => {
    await api(URLS.promo, { code: "" });
    location.reload();
  });
}

/* =========================================================
   PRODUCT PAGE
   ========================================================= */
if ($("#pdAdd")) {
  let q = 1;
  const p = byId.get(+$("#pdAdd").dataset.id);
  $("#pdMinus").addEventListener("click", () => { q = Math.max(1, q - 1); $("#pdQty").textContent = q; });
  $("#pdPlus").addEventListener("click", () => { q = Math.min(99, q + 1); $("#pdQty").textContent = q; });
  $("#pdAdd").addEventListener("click", () => addToCart(p.id, q));
}
if ($("#pdDesc")) {
  const p = byId.get(+$("#pdDesc").dataset.id);
  if (p) {
    if (!$("#pdDesc").textContent.trim() || p.bundle) $("#pdDesc").textContent = describe(p);
    $("#pdPoints").innerHTML = pointsHTML(p);
  }
}

/* =========================================================
   THEME, NAV, USER MENU, SCROLL, REVEAL
   ========================================================= */
const themeBtn = $("#themeBtn");
function setThemeIcon() {
  const dark = document.documentElement.dataset.theme === "dark";
  themeBtn.innerHTML = `<i class="fa-solid fa-${dark ? "sun" : "moon"}"></i>`;
}
themeBtn.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("eg-theme", next); } catch {}
  setThemeIcon();
});
setThemeIcon();

const navMenu = $("#navMenu");
$("#menuToggle").addEventListener("click", () => navMenu.classList.toggle("open"));
navMenu.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => navMenu.classList.remove("open")));

const userBtn = $("#userBtn");
if (userBtn) {
  userBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    const open = $("#userMenu").classList.toggle("open");
    userBtn.setAttribute("aria-expanded", open);
  });
  document.addEventListener("click", (e) => { if (!e.target.closest("#userMenu")) $("#userMenu").classList.remove("open"); });
}

$("#topbarClose")?.addEventListener("click", () => $("#topbar").classList.add("hide"));

const sections = isHome ? ["home", "categories", "deal", "packages"].map((id) => document.getElementById(id)).filter(Boolean) : [];
function onScroll() {
  const y = window.scrollY;
  $("#header").classList.toggle("scrolled", y > 10);
  $("#toTop").classList.toggle("show", y > 600);
  if (!isHome) return;
  let current = "home";
  sections.forEach((s) => { if (y + 160 >= s.offsetTop) current = s.id; });
  $$(".nav-link").forEach((l) => l.classList.toggle("active", l.dataset.section === current));
}
window.addEventListener("scroll", onScroll, { passive: true });
$("#toTop").addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));

const io = new IntersectionObserver((entries) => {
  entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } });
}, { threshold: 0.12 });
$$(".reveal").forEach((el) => io.observe(el));

/* ---------- stop double submits on normal forms (sign up, log in, checkout) ---------- */
$$("form[method='post']").forEach((form) => form.addEventListener("submit", (e) => {
  if (form.dataset.sending) { e.preventDefault(); return; }
  form.dataset.sending = "1";
  form.querySelectorAll("button[type='submit']").forEach((b) => {
    b.disabled = true;
    b.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Please wait…`;
  });
}));
// re-enable if the user comes back with the browser's Back button
window.addEventListener("pageshow", (e) => {
  if (e.persisted) location.reload();
});

/* ---------- Django flash messages → toasts ---------- */
const flash = [...$$("#flash li")];
flash.forEach((li, i) => setTimeout(() => {
  const icon = li.dataset.level.includes("error") ? "fa-circle-exclamation err" : li.dataset.level.includes("success") ? "fa-circle-check" : "fa-circle-info";
  toast(`<i class="fa-solid ${icon}"></i>${esc(li.textContent)}`);
}, i * 2800));

/* =========================================================
   INIT
   ========================================================= */
$("#year").textContent = new Date().getFullYear();
refresh();
onScroll();

// old links like /#cat-office or /?q=milk now open the Shop page
if (isHome) {
  const hashCat = location.hash.match(/^#cat-([\w-]+)/);
  const q = new URLSearchParams(location.search).get("q");
  const cat = hashCat && STATE.categories.find((c) => c.slug === hashCat[1]);
  if (cat) location.replace(cat.url);
  else if (q) location.replace(`${URLS.shop}?q=${encodeURIComponent(q)}`);
}
