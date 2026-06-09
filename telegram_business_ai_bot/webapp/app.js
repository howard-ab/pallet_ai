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
  cartDockButton: document.querySelector("#cartDockButton"),
  cartDockCount: document.querySelector("#cartDockCount"),
  cartDockTotal: document.querySelector("#cartDockTotal"),
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
  }, 1800);
}

function priceValue(price) {
  const match = String(price).replace(/\s/g, "").match(/\d+/);
  return match ? Number(match[0]) : 0;
}

function cartTotalValue() {
  return state.cart.reduce((sum, item) => sum + priceValue(item.price), 0);
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
    button.textContent = "В корзину";
  }, 900);
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
        <button class="add-button" type="button">В корзину</button>
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

function removeCartItem(index) {
  state.cart.splice(index, 1);
  renderCart();
}

function renderCart() {
  const total = cartTotalValue();
  els.cartDockCount.textContent = String(state.cart.length);
  els.cartDockTotal.textContent = `${total} руб.`;
  els.cartTotal.textContent = `${total} руб.`;

  els.cartList.innerHTML = "";
  if (!state.cart.length) {
    const empty = document.createElement("div");
    empty.className = "cart-empty";
    empty.textContent = "Корзина пока пустая. Добавьте товары из витрины.";
    els.cartList.append(empty);
    return;
  }

  state.cart.forEach((item, index) => {
    const row = document.createElement("div");
    row.className = "cart-item";
    row.innerHTML = `
      <div class="cart-item-copy">
        <strong>${item.name}</strong>
        <span>${item.weight} · ${item.price}</span>
      </div>
      <div class="cart-item-actions">
        <button class="cart-remove" type="button">Удалить</button>
      </div>
    `;
    row.querySelector("button").onclick = () => removeCartItem(index);
    els.cartList.append(row);
  });
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

els.cartDockButton.onclick = openCart;
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
    total: cartTotalValue(),
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
