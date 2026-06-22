function startupMark(step) {
  const marker = new Image();
  marker.src = `./startup-check.gif?step=${encodeURIComponent(step)}&t=${Date.now()}`;
}

startupMark("app-start");

let tg = null;
try {
  tg = window.Telegram && window.Telegram.WebApp
    ? window.Telegram.WebApp
    : null;
} catch (error) {
  console.warn("Telegram WebApp SDK initialization failed", error);
  tg = null;
}
startupMark("telegram-detected");

const searchParams = new URLSearchParams(window.location.search);
const checkoutApiUrl = searchParams.get("api") || "";
startupMark("search-params-ready");

const CATEGORY_ORDER = [
  "Сухофрукты",
  "Орехи",
  "Сушёные ягоды",
  "Специи и пряности",
  "Восточные сладости",
  "Орехи и фрукты в шоколаде",
  "Бобовые и семена",
  "Натуральные масла",
  "Восточная керамика",
  "Подарочные наборы",
];

const EMPTY_CATEGORY_COPY = {
  "Натуральные масла": "Скоро добавим натуральные масла в витрину. Пока можно выбрать другие позиции и оформить заказ через менеджера.",
  "Восточная керамика": "Раздел с восточной керамикой готовится. Если нужна пиала, блюдо или сервировочная керамика, напишите менеджеру.",
  "Подарочные наборы": "Подарочные наборы собираются вручную под запрос. Напишите менеджеру, и мы подберем красивый вариант под бюджет.",
};

const QUICK_WEIGHT_OPTIONS_KG = [0.25, 0.5, 1];
const DISCOUNT_RATE = 0.10;

const state = {
  rawCatalog: {},
  catalog: {},
  category: "",
  subcategory: "",
  cart: [],
  searchQuery: "",
  featured: [],
  flatProducts: [],
  discountedProductKeys: new Set(),
};

const els = {
  splash: document.querySelector("#splashScreen"),
  appRoot: document.querySelector("#appRoot"),
  categories: document.querySelector("#categoryTabs"),
  subcategories: document.querySelector("#subcategoryChips"),
  products: document.querySelector("#productGrid"),
  searchInput: document.querySelector("#searchInput"),
  searchSubmitButton: document.querySelector("#searchSubmitButton"),
  clearSearchButton: document.querySelector("#clearSearchButton"),
  featuredSection: document.querySelector("#featuredSection"),
  weeklyGrid: document.querySelector("#weeklyGrid"),
  catalogEyebrow: document.querySelector("#catalogEyebrow"),
  catalogTitle: document.querySelector("#catalogTitle"),
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
startupMark("dom-ready");

function initializeTelegramWebApp() {
  if (!tg) return;
  try {
    if (typeof tg.ready === "function") {
      tg.ready();
    }
    if (typeof tg.expand === "function") {
      tg.expand();
    }
  } catch (error) {
    console.warn("Telegram WebApp SDK activation failed", error);
  }
}

function hideSplash() {
  window.setTimeout(() => {
    if (els.splash) {
      els.splash.classList.add("hidden");
    }
    if (els.appRoot) {
      els.appRoot.classList.remove("app-hidden");
    }
  }, 3000);
}

function normalizeText(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/ё/g, "е")
    .replace(/[^a-zа-я0-9\s]/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function priceValue(price) {
  const match = String(price).replace(/\s/g, "").match(/\d+/);
  return match ? Number(match[0]) : 0;
}

function parseWeightKg(weight) {
  const normalized = String(weight).trim().toLowerCase().replace(",", ".");
  const match = normalized.match(/(\d+(?:\.\d+)?)/);
  if (!match) return 1;
  const value = Number(match[1]);
  if (!Number.isFinite(value) || value <= 0) return 1;
  if (normalized.includes("г") && !normalized.includes("кг")) {
    return value / 1000;
  }
  return value;
}

function formatWeightKg(value) {
  const rounded = Math.round(value * 100) / 100;
  const text = Number.isInteger(rounded) ? String(rounded) : String(rounded).replace(".", ",");
  return `${text} кг`;
}

function formatRub(value) {
  return `${Math.round(value)} руб.`;
}

function buildWeightedProduct(product, selectedWeightKg) {
  const baseWeightKg = parseWeightKg(product.weight);
  const unitPricePerKg = priceValue(product.price) / baseWeightKg;
  const originalPriceValue = Math.round(unitPricePerKg * selectedWeightKg);
  const discountedPriceValue = product.isDiscounted
    ? Math.max(1, Math.round(originalPriceValue * (1 - DISCOUNT_RATE)))
    : originalPriceValue;
  return {
    ...product,
    unitPricePerKg,
    selectedWeightKg,
    selectedWeightLabel: formatWeightKg(selectedWeightKg),
    weight: formatWeightKg(selectedWeightKg),
    originalPriceValue,
    discountedPriceValue,
    originalPrice: formatRub(originalPriceValue),
    price: formatRub(discountedPriceValue),
  };
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

function dedupeProducts(products) {
  const seen = new Map();
  products.forEach((product) => {
    const key = [product.name, product.origin, product.photo || product.photo_url || "", product.rawCategory || "", product.rawSubcategory || ""].join("::");
    if (!seen.has(key)) {
      seen.set(key, product);
    }
  });
  return Array.from(seen.values());
}

function productIdentityKey(product) {
  return [
    normalizeText(product.name),
    normalizeText(product.origin),
    normalizeText(product.rawCategory || ""),
    normalizeText(product.rawSubcategory || ""),
  ].join("::");
}

function applyDiscountFlag(products, discountedKeys) {
  return products.map((product) => ({
    ...product,
    isDiscounted: discountedKeys.has(productIdentityKey(product)),
  }));
}

function applyDiscountFlagToCatalog(catalog, discountedKeys) {
  const result = {};
  Object.entries(catalog).forEach(([category, subcategories]) => {
    result[category] = {};
    Object.entries(subcategories).forEach(([subcategory, products]) => {
      result[category][subcategory] = applyDiscountFlag(products, discountedKeys);
    });
  });
  return result;
}

function flattenCatalog(rawCatalog) {
  const products = [];
  Object.entries(rawCatalog).forEach(([category, subcategories]) => {
    Object.entries(subcategories).forEach(([subcategory, items]) => {
      items.forEach((item) => {
        products.push({
          ...item,
          rawCategory: category,
          rawSubcategory: subcategory,
        });
      });
    });
  });
  return products;
}

function productText(product) {
  return normalizeText([
    product.name,
    product.description,
    product.origin,
    product.rawCategory,
    product.rawSubcategory,
  ].join(" "));
}

function matchesKeywords(product, keywords) {
  const haystack = productText(product);
  return keywords.some((keyword) => haystack.includes(normalizeText(keyword)));
}

function isChocolateProduct(product) {
  return matchesKeywords(product, ["шоколад", "глазур", "драже"]);
}

function takeRawProducts(rawCatalog, category, subcategory, predicate = null) {
  const categoryItems = rawCatalog[category] || {};
  const items = (categoryItems[subcategory] || []).map((item) => ({
    ...item,
    rawCategory: category,
    rawSubcategory: subcategory,
  }));
  return predicate ? items.filter(predicate) : items;
}

function buildDisplayCatalog(rawCatalog) {
  const allProducts = flattenCatalog(rawCatalog);
  const sweetsProducts = takeRawProducts(rawCatalog, "Напитки и сладости", "Сладости");
  const spiceProducts = takeRawProducts(rawCatalog, "Бакалея", "Специи");
  const grainProducts = takeRawProducts(rawCatalog, "Бакалея", "Крупы и бобовые");
  const seedProducts = takeRawProducts(rawCatalog, "Бакалея", "Семена");
  const chocolateProducts = dedupeProducts([
    ...allProducts.filter(isChocolateProduct),
    ...takeRawProducts(rawCatalog, "Орехи", "Орехи в глазури"),
  ]);
  const driedBerryProducts = dedupeProducts([
    ...takeRawProducts(rawCatalog, "Сухофрукты", "Изюм"),
    ...allProducts.filter((product) => matchesKeywords(product, ["клубник", "ягод", "вишн", "клюкв", "смородин", "черешн"])),
  ]);
  const naturalOilProducts = dedupeProducts(
    allProducts.filter((product) => matchesKeywords(product, ["масло", "оливков", "кунжутн", "льнян"]))
  );
  const ceramicProducts = dedupeProducts(
    allProducts.filter((product) => matchesKeywords(product, ["керамик", "пиала", "блюдо", "тарел", "чаша"]))
  );
  const giftProducts = dedupeProducts(
    allProducts.filter((product) => {
      const nameOnly = normalizeText(product.name);
      return nameOnly.includes("подар") || nameOnly.includes("набор") || nameOnly.includes("корзин");
    })
  );

  return {
    "Сухофрукты": {
      "Курага": takeRawProducts(rawCatalog, "Сухофрукты", "Курага"),
      "Изюм": takeRawProducts(rawCatalog, "Сухофрукты", "Изюм"),
      "Финики": takeRawProducts(rawCatalog, "Сухофрукты", "Финики"),
      "Цукаты": takeRawProducts(rawCatalog, "Сухофрукты", "Цукаты"),
      "Прочие сухофрукты": takeRawProducts(rawCatalog, "Сухофрукты", "Прочие сухофрукты"),
    },
    "Орехи": {
      "Фисташки": takeRawProducts(rawCatalog, "Орехи", "Фисташки", (product) => !isChocolateProduct(product)),
      "Миндаль и фундук": takeRawProducts(rawCatalog, "Орехи", "Миндаль и фундук", (product) => !isChocolateProduct(product)),
      "Грецкий орех": takeRawProducts(rawCatalog, "Орехи", "Грецкий орех", (product) => !isChocolateProduct(product)),
      "Ореховые смеси": takeRawProducts(rawCatalog, "Орехи", "Ореховые смеси", (product) => !isChocolateProduct(product)),
    },
    "Сушёные ягоды": {
      "Изюм и ягоды": driedBerryProducts,
    },
    "Специи и пряности": {
      "Специи": spiceProducts,
    },
    "Восточные сладости": {
      "Сладости": dedupeProducts(sweetsProducts.filter((product) => !isChocolateProduct(product))),
    },
    "Орехи и фрукты в шоколаде": {
      "Шоколад и глазурь": chocolateProducts,
    },
    "Бобовые и семена": {
      "Семена": seedProducts,
      "Бобовые и крупы": grainProducts,
    },
    "Натуральные масла": {
      "Масла": naturalOilProducts,
    },
    "Восточная керамика": {
      "Керамика": ceramicProducts,
    },
    "Подарочные наборы": {
      "Подарки": giftProducts,
    },
  };
}

function pickFeaturedProducts(allProducts) {
  const selected = [];
  const wanted = [
    ["курага", "урюк"],
    ["фисташ"],
    ["финик"],
    ["шоколад"],
    ["нут", "семен", "чиа"],
  ];

  wanted.forEach((keywords) => {
    const found = allProducts.find((product) => matchesKeywords(product, keywords) && !selected.includes(product));
    if (found) {
      selected.push(found);
    }
  });

  if (selected.length < 5) {
    allProducts.forEach((product) => {
      if (selected.length >= 5) return;
      if (!selected.includes(product)) {
        selected.push(product);
      }
    });
  }

  return selected.slice(0, 5);
}

function isSubsequence(query, target) {
  let position = 0;
  for (let index = 0; index < target.length; index += 1) {
    const char = target.charAt(index);
    if (char === query[position]) {
      position += 1;
      if (position === query.length) {
        return true;
      }
    }
  }
  return false;
}

function searchScore(product, query) {
  const normalizedQuery = normalizeText(query);
  if (!normalizedQuery) return 0;

  const haystack = productText(product);
  const compactQuery = normalizedQuery.replace(/\s/g, "");
  const compactHaystack = haystack.replace(/\s/g, "");
  const name = normalizeText(product.name);
  let score = 0;

  if (name.startsWith(normalizedQuery)) {
    score += 120;
  }
  if (haystack.includes(normalizedQuery)) {
    score += 90;
    score += Math.max(0, 20 - haystack.indexOf(normalizedQuery));
  }

  normalizedQuery.split(" ").filter(Boolean).forEach((token) => {
    if (name.includes(token)) score += 28;
    else if (haystack.includes(token)) score += 14;
  });

  if (compactQuery && isSubsequence(compactQuery, compactHaystack)) {
    score += 18;
  }

  return score;
}

function getSearchResults(query) {
  const normalizedQuery = normalizeText(query);
  if (!normalizedQuery) return [];

  return dedupeProducts(state.flatProducts)
    .map((product) => ({ product, score: searchScore(product, normalizedQuery) }))
    .filter((entry) => entry.score > 0)
    .sort((left, right) => right.score - left.score || left.product.name.localeCompare(right.product.name, "ru"))
    .map((entry) => entry.product)
    .slice(0, 24);
}

function setDefaultCategory() {
  const categories = Object.keys(state.catalog);
  if (!categories.length) return;
  if (!state.catalog[state.category]) {
    state.category = categories[0];
  }
  const subcategories = Object.keys(state.catalog[state.category] || {});
  if (!subcategories.length) {
    state.subcategory = "";
    return;
  }
  if (!state.catalog[state.category][state.subcategory]) {
    state.subcategory = subcategories[0];
  }
}

function updateCatalogHeading(resultCount = 0) {
  if (state.searchQuery) {
    els.catalogEyebrow.textContent = "Поиск";
    els.catalogTitle.textContent = resultCount
      ? `Найдено ${resultCount} товаров`
      : "Ничего не найдено";
    return;
  }

  els.catalogEyebrow.textContent = "Каталог";
  els.catalogTitle.textContent = "Выберите категорию и соберите корзину";
}

function applySearch() {
  const query = String(els.searchInput ? els.searchInput.value : "").trim();
  state.searchQuery = query;
  if (els.searchInput) {
    els.searchInput.blur();
  }
  render();
}

function resetSearch() {
  state.searchQuery = "";
  if (els.searchInput) {
    els.searchInput.value = "";
    els.searchInput.blur();
  }
  render();
}

function renderCategories() {
  els.categories.innerHTML = "";
  CATEGORY_ORDER.filter((category) => state.catalog[category]).forEach((category) => {
    const button = document.createElement("button");
    button.className = `tab${category === state.category ? " active" : ""}`;
    button.textContent = category;
    button.onclick = () => {
      state.category = category;
      state.subcategory = Object.keys(state.catalog[category] || {})[0] || "";
      state.searchQuery = "";
      if (els.searchInput) {
        els.searchInput.value = "";
      }
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
  const hidden = Boolean(state.searchQuery);
  els.subcategories.classList.toggle("is-hidden", hidden);
  if (hidden) {
    return;
  }

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

function createProductCard(product, options = {}) {
  const { featured = false } = options;
  const hasDiscount = Boolean(product.isDiscounted);
  const defaultWeightKg = parseWeightKg(product.weight);
  let selectedWeightKg = defaultWeightKg;
  const card = document.createElement("article");
  card.className = `product${featured ? " featured" : ""}`;
  card.innerHTML = `
    <img src="${product.photo || product.photo_url || ""}" alt="${product.name}">
    <div class="product-body">
      ${(featured || hasDiscount) ? `
        <div class="product-badges">
          ${hasDiscount ? '<span class="product-badge discount">-10% скидка</span>' : ''}
          ${featured ? '<span class="product-badge">Товар недели</span>' : ''}
        </div>
      ` : ""}
      <h3>${product.name}</h3>
      <div class="meta">
        <span>${product.origin}</span>
        <span class="selected-weight">${formatWeightKg(selectedWeightKg)}</span>
        <div class="selected-price-block${hasDiscount ? ' has-discount' : ''}">
          ${hasDiscount ? '<span class="selected-price-old"></span>' : ''}
          <strong class="selected-price"></strong>
        </div>
      </div>
      <div class="weight-picker">
        <div class="weight-presets">
          ${QUICK_WEIGHT_OPTIONS_KG.map((value) => `
            <button class="weight-chip${Math.abs(value - selectedWeightKg) < 0.001 ? " active" : ""}" type="button" data-weight="${value}">
              ${formatWeightKg(value)}
            </button>
          `).join("")}
        </div>
        <div class="weight-custom">
          <input class="weight-input" type="text" inputmode="decimal" placeholder="Свой вес, кг">
          <button class="weight-apply" type="button">OK</button>
        </div>
      </div>
      <div class="product-actions">
        <button class="info-button" type="button">Инфо</button>
        <button class="add-button" type="button">В корзину</button>
      </div>
    </div>
  `;

  const infoButton = card.querySelector(".info-button");
  const addButton = card.querySelector(".add-button");
  const selectedWeightEl = card.querySelector(".selected-weight");
  const selectedPriceEl = card.querySelector(".selected-price");
  const selectedOldPriceEl = card.querySelector(".selected-price-old");
  const weightChips = Array.from(card.querySelectorAll(".weight-chip"));
  const weightInput = card.querySelector(".weight-input");
  const weightApply = card.querySelector(".weight-apply");

  function refreshSelection() {
    const weighted = buildWeightedProduct(product, selectedWeightKg);
    selectedWeightEl.textContent = weighted.weight;
    selectedPriceEl.textContent = weighted.price;
    if (selectedOldPriceEl) {
      selectedOldPriceEl.textContent = weighted.originalPrice;
    }
    weightChips.forEach((chip) => {
      const chipWeight = Number(chip.dataset.weight || 0);
      chip.classList.toggle("active", Math.abs(chipWeight - selectedWeightKg) < 0.001);
    });
  }

  weightChips.forEach((chip) => {
    chip.onclick = () => {
      selectedWeightKg = Number(chip.dataset.weight || defaultWeightKg);
      refreshSelection();
    };
  });

  weightApply.onclick = () => {
    const raw = String(weightInput.value || "").trim().replace(",", ".");
    const customWeight = Number(raw);
    if (!Number.isFinite(customWeight) || customWeight <= 0) {
      if (tg && tg.showAlert) {
        tg.showAlert("Введите вес в килограммах, например 0.5 или 1.5");
      } else {
        alert("Введите вес в килограммах, например 0.5 или 1.5");
      }
      return;
    }
    selectedWeightKg = Math.round(customWeight * 100) / 100;
    refreshSelection();
  };

  infoButton.onclick = () => openProductInfo(product);
  addButton.onclick = () => {
    addToCart(buildWeightedProduct(product, selectedWeightKg));
    renderCart();
    showAddedFeedback(card, addButton);
  };

  return card;
}

function renderFeaturedProducts() {
  if (!els.weeklyGrid) return;
  els.weeklyGrid.innerHTML = "";
  state.featured.forEach((product) => {
    els.weeklyGrid.append(createProductCard(product, { featured: true }));
  });
}

function renderEmptyState(title, description) {
  const card = document.createElement("article");
  card.className = "empty-catalog";
  card.innerHTML = `
    <strong>${title}</strong>
    <p>${description}</p>
  `;
  els.products.append(card);
}

function renderProducts() {
  els.products.innerHTML = "";

  if (state.searchQuery) {
    const results = getSearchResults(state.searchQuery);
    updateCatalogHeading(results.length);
    if (!results.length) {
      renderEmptyState(
        "Ничего не найдено",
        "Попробуйте другое слово или часть названия. Например: курага, финики, шоколад, фундук.",
      );
      return;
    }
    results.forEach((product) => {
      els.products.append(createProductCard(product));
    });
    return;
  }

  updateCatalogHeading();
  const currentCategory = state.catalog[state.category] || {};
  const products = currentCategory[state.subcategory] || [];
  if (!products.length) {
    renderEmptyState(
      `${state.category} скоро появятся в витрине`,
      EMPTY_CATEGORY_COPY[state.category] || "Раздел наполняется. Напишите менеджеру, если хотите уточнить наличие заранее.",
    );
    return;
  }

  products.forEach((product) => {
    els.products.append(createProductCard(product));
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
        <div class="cart-item-price${item.isDiscounted ? " discounted" : ""}">
          ${item.isDiscounted ? `<span class="cart-old-price">${item.weight} · ${item.originalPrice}</span>` : ""}
          <span class="cart-current-price">${item.weight} · ${item.price}</span>
        </div>
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
  setDefaultCategory();
  renderCategories();
  renderSubcategories();
  renderFeaturedProducts();
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

if (els.searchInput) {
  els.searchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      applySearch();
    }
  });
}

if (els.searchSubmitButton) {
  els.searchSubmitButton.onclick = () => {
    applySearch();
  };
}

if (els.clearSearchButton) {
  els.clearSearchButton.onclick = () => {
    resetSearch();
  };
}

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
    if (tg && tg.showAlert) {
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
  if (tg && checkoutApiUrl && tg.initData) {
    els.orderButton.disabled = true;
    els.orderButton.textContent = "Отправляем...";
    fetch(checkoutApiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ...payload,
        init_data: tg.initData,
        launch_source: "webapp",
      }),
    })
      .then((response) => response.json()
        .catch(() => ({}))
        .then((data) => ({ response: response, data: data })))
      .then((result) => {
        const response = result.response;
        const data = result.data;
        if (!response.ok || !data.ok) {
          throw new Error(data.error || "checkout_failed");
        }
        const waitingForConfirmation = Boolean(
          data.awaiting_address_confirmation || data.awaiting_profile,
        );
        els.orderButton.textContent = waitingForConfirmation
          ? "Проверьте чат ✓"
          : "Заказ принят ✓";
        state.cart = [];
        renderCart();
        closeCart();
        const successMessage = waitingForConfirmation
          ? (data.message || "Проверьте чат бота и подтвердите адрес доставки.")
          : `Заказ принят. Номер: ${data.order_number || "-"}. Ответ придет в чат бота.`;
        if (tg.showAlert) {
          tg.showAlert(successMessage);
        } else {
          alert(successMessage);
        }
      })
      .catch(() => {
        els.orderButton.disabled = false;
        els.orderButton.textContent = "Оформить заказ";
        if (tg.showAlert) {
          tg.showAlert("Не удалось отправить заказ через витрину. Попробуйте снова или откройте каталог заново.");
        } else {
          alert("Не удалось отправить заказ.");
        }
      });
    return;
  }

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

startupMark("before-catalog-fetch");
fetch("./catalog.json")
  .then((response) => response.json())
  .then((rawCatalog) => {
    state.rawCatalog = rawCatalog;
    const flatProducts = flattenCatalog(rawCatalog);
    const featuredProducts = pickFeaturedProducts(flatProducts);
    state.discountedProductKeys = new Set(featuredProducts.map((product) => productIdentityKey(product)));
    state.flatProducts = applyDiscountFlag(flatProducts, state.discountedProductKeys);
    state.catalog = applyDiscountFlagToCatalog(buildDisplayCatalog(rawCatalog), state.discountedProductKeys);
    state.featured = applyDiscountFlag(featuredProducts, state.discountedProductKeys);
    state.category = CATEGORY_ORDER.find((category) => state.catalog[category]) || Object.keys(state.catalog)[0] || "";
    state.subcategory = Object.keys(state.catalog[state.category] || {})[0] || "";
    render();
    initializeTelegramWebApp();
    hideSplash();
  });
