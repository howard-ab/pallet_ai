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
  infoPanel: document.querySelector("#infoPanel"),
  closeInfoButton: document.querySelector("#closeInfoButton"),
  infoTitle: document.querySelector("#infoTitle"),
  infoDescription: document.querySelector("#infoDescription"),
  infoOrigin: document.querySelector("#infoOrigin"),
  infoWeight: document.querySelector("#infoWeight"),
  infoPrice: document.querySelector("#infoPrice"),
};

function hideSplash() {
  window.setTimeout(() => {
    els.splash?.classList.add("hidden");
    els.appRoot?.classList.remove("app-hidden");
  }, 3000);
}

function priceValue(price) {
  const match = String(price).replace(/\s/g, "").match(/\d+/);
  return match ? Number(match[0]) : 0;
}

function itemKey(item) {
  return [item.name, item.weight, item.price].join("::");
}

function itemQuantity(item) {
  return Number(item.quantity || 1);
}

function cartTotalValue() {
  return state.cart.reduce((sum, item) => sum + priceValue(item.price) * itemQuantity(item), 0);
}

function cartItemsCount() {
  return state.cart.reduce((sum, item) => sum + itemQuantity(item), 0);
}

function addToCart(product) {
  const key = itemKey(product);
  const existing = state.cart.find((item) => itemKey(item) === key);
  if (existing) {
    existing.quantity = itemQuantity(existing) + 1;
    return;
  }
  state.cart.push({ ...product, quantity: 1 });
}

function changeCartQuantity(index, delta) {
  const item = state.cart[index];
  if (!item) return;
  const nextQuantity = itemQuantity(item) + delta;
  if (nextQuantity <= 0) {
    state.cart.splice(index, 1);
    renderCart();
    return;
  }
  item.quantity = nextQuantity;
  renderCart();
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
  window.requestAnimationFrame(() => {
    els.categories.scrollLeft = 0;
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
  window.requestAnimationFrame(() => {
    els.subcategories.scrollLeft = 0;
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
        <div class="meta">
          <span>${product.origin}</span>
          <span>${product.weight}</span>
          <strong>${product.price}</strong>
        </div>
        <div class="product-actions">
          <button class="info-button" type="button">Инфо</button>
          <button class="add-button" type="button">В корзину</button>
        </div>
      </div>
    `;
    const infoButton = card.querySelector(".info-button");
    const addButton = card.querySelector(".add-button");
    infoButton.onclick = () => openProductInfo(product);
    addButton.onclick = () => {
      addToCart(product);
      renderCart();
      showAddedFeedback(card, addButton);
    };
    els.products.append(card);
  });
}

function renderCart() {
  const total = cartTotalValue();
  els.cartDockCount.textContent = String(cartItemsCount());
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
        <div class="qty-stepper">
          <button class="qty-button" type="button" aria-label="Уменьшить количество">−</button>
          <span class="qty-value">${itemQuantity(item)}</span>
          <button class="qty-button" type="button" aria-label="Увеличить количество">+</button>
        </div>
      </div>
    `;
    const [minusButton, plusButton] = row.querySelectorAll("button");
    minusButton.onclick = () => changeCartQuantity(index, -1);
    plusButton.onclick = () => changeCartQuantity(index, 1);
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

function openProductInfo(product) {
  els.infoTitle.textContent = product.name;
  els.infoDescription.textContent = product.description;
  els.infoOrigin.textContent = product.origin;
  els.infoWeight.textContent = product.weight;
  els.infoPrice.textContent = product.price;
  els.infoPanel.classList.add("open");
  els.infoPanel.setAttribute("aria-hidden", "false");
}

function closeProductInfo() {
  els.infoPanel.classList.remove("open");
  els.infoPanel.setAttribute("aria-hidden", "true");
}

els.cartDockButton.onclick = openCart;
els.closeCartButton.onclick = closeCart;
els.closeInfoButton.onclick = closeProductInfo;
els.clearButton.onclick = () => {
  state.cart = [];
  renderCart();
};

els.infoPanel.onclick = (event) => {
  if (event.target === els.infoPanel) {
    closeProductInfo();
  }
};

els.cartPanel.onclick = (event) => {
  if (event.target === els.cartPanel) {
    closeCart();
  }
};

els.orderButton.onclick = () => {
  if (!state.cart.length) {
    if (tg?.showAlert) {
      tg.showAlert("Сначала добавьте товары в корзину.");
    } else {
      alert("Сначала добавьте товары в корзину.");
    }
    return;
  }
  const payload = {
    type: "order",
    items: state.cart.map((item) => ({
      name: item.name,
      price: item.price,
      weight: item.weight,
      quantity: itemQuantity(item),
    })),
    total: cartTotalValue(),
  };
  if (tg) {
    els.orderButton.disabled = true;
    els.orderButton.textContent = "Отправляем...";
    tg.sendData(JSON.stringify(payload));
    window.setTimeout(() => {
      els.orderButton.textContent = "Отправлено в бот";
      if (tg.showAlert) {
        tg.showAlert("Заказ отправлен в бот. Дождитесь ответа в чате и закройте это окно вручную.");
      }
    }, 500);
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
