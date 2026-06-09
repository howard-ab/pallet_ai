const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

const state = {
  catalog: {},
  category: "",
  subcategory: "",
  cart: [],
};

const els = {
  splash: document.querySelector("#splashScreen"),
  appRoot: document.querySelector("#appRoot"),
  categories: document.querySelector("#categoryTabs"),
  subcategories: document.querySelector("#subcategoryChips"),
  products: document.querySelector("#productGrid"),
  cartButton: document.querySelector("#cartButton"),
  cartPanel: document.querySelector("#cartPanel"),
  cartList: document.querySelector("#cartList"),
  cartTotal: document.querySelector("#cartTotal"),
  closeCartButton: document.querySelector("#closeCartButton"),
  orderButton: document.querySelector("#orderButton"),
  clearButton: document.querySelector("#clearButton"),
};

function hideSplash() {
  window.setTimeout(() => {
    els.splash?.classList.add("hidden");
    els.appRoot?.classList.remove("app-hidden");
  }, 2000);
}

function priceValue(price) {
  const match = String(price).replace(/\s/g, "").match(/\d+/);
  return match ? Number(match[0]) : 0;
}

function renderCategories() {
  els.categories.innerHTML = "";
  Object.keys(state.catalog).forEach((category) => {
    const button = document.createElement("button");
    button.className = `tab${category === state.category ? " active" : ""}`;
    button.textContent = category;
    button.onclick = () => {
      state.category = category;
      state.subcategory = Object.keys(state.catalog[category])[0];
      render();
    };
    els.categories.append(button);
  });
}

function renderSubcategories() {
  els.subcategories.innerHTML = "";
  Object.keys(state.catalog[state.category] || {}).forEach((subcategory) => {
    const button = document.createElement("button");
    button.className = `chip${subcategory === state.subcategory ? " active" : ""}`;
    button.textContent = subcategory;
    button.onclick = () => {
      state.subcategory = subcategory;
      render();
    };
    els.subcategories.append(button);
  });
}

function showAddedFeedback(card, button) {
  card.classList.remove("added");
  button.classList.remove("added");
  void card.offsetWidth;
  card.classList.add("added");
  button.classList.add("added");
  button.textContent = "Добавлено ✓";
  window.setTimeout(() => {
    card.classList.remove("added");
    button.classList.remove("added");
    button.textContent = "В корзину ✨";
  }, 1100);
}

function renderProducts() {
  els.products.innerHTML = "";
  const products = state.catalog[state.category]?.[state.subcategory] || [];
  products.forEach((product) => {
    const card = document.createElement("article");
    card.className = "product";
    card.innerHTML = `
      <img src="${product.photo}" alt="${product.name}">
      <div class="product-body">
        <h3>${product.name}</h3>
        <p>${product.description}</p>
        <div class="meta">
          <span>${product.weight}</span>
          <strong>${product.price}</strong>
        </div>
        <button class="add-button" type="button">В корзину ✨</button>
      </div>
    `;
    const button = card.querySelector("button");
    button.onclick = () => {
      state.cart.push(product);
      renderCart();
      showAddedFeedback(card, button);
    };
    els.products.append(card);
  });
}

function renderCart() {
  els.cartButton.textContent = `🧺 Корзина · ${state.cart.length}`;
  els.cartList.innerHTML = "";
  state.cart.forEach((item) => {
    const row = document.createElement("div");
    row.className = "cart-item";
    row.innerHTML = `<strong>${item.name}</strong><span>${item.weight} · ${item.price}</span>`;
    els.cartList.append(row);
  });
  const total = state.cart.reduce((sum, item) => sum + priceValue(item.price), 0);
  els.cartTotal.textContent = `${total} руб.`;
}

function render() {
  renderCategories();
  renderSubcategories();
  renderProducts();
  renderCart();
}

function openCart() {
  els.cartPanel.classList.add("open");
  els.cartPanel.setAttribute("aria-hidden", "false");
}

function closeCart() {
  els.cartPanel.classList.remove("open");
  els.cartPanel.setAttribute("aria-hidden", "true");
}

els.cartButton.onclick = openCart;
els.closeCartButton.onclick = closeCart;
els.clearButton.onclick = () => {
  state.cart = [];
  renderCart();
};
els.orderButton.onclick = () => {
  if (!state.cart.length) return;
  const payload = {
    type: "order",
    items: state.cart.map((item) => ({
      name: item.name,
      price: item.price,
      weight: item.weight,
    })),
    total: state.cart.reduce((sum, item) => sum + priceValue(item.price), 0),
  };
  if (tg) {
    tg.sendData(JSON.stringify(payload));
    tg.close();
  } else {
    alert("Заказ подготовлен. В Telegram он будет отправлен менеджеру.");
  }
};

fetch("./catalog.json")
  .then((response) => response.json())
  .then((catalog) => {
    state.catalog = catalog;
    state.category = Object.keys(catalog)[0];
    state.subcategory = Object.keys(catalog[state.category])[0];
    render();
    hideSplash();
  });
