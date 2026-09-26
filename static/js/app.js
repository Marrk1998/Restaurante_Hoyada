function initializeHeroCarousel() {
  const heroCarousel = document.querySelector("[data-hero-carousel]");
  if (!heroCarousel) return;

  const slides = Array.from(heroCarousel.querySelectorAll("[data-hero-slide]"));
  const intervalMs = Number.parseInt(heroCarousel.dataset.interval || "5000", 10);
  if (slides.length === 0) return;

  let activeIndex = slides.findIndex((slide) => slide.classList.contains("is-active"));
  if (activeIndex < 0 && slides.length > 0) {
    activeIndex = 0;
  }
  const currentIndicator = heroCarousel.querySelector("[data-hero-current]");
  const updateIndicator = () => {
    if (currentIndicator) currentIndicator.textContent = String(activeIndex + 1);
  };
  slides.forEach((slide, index) => {
    const isActive = index === activeIndex;
    slide.classList.toggle("is-active", isActive);
    slide.setAttribute("aria-hidden", String(!isActive));
  });
  updateIndicator();

  slides.forEach((slide) => {
    const image = slide.querySelector("img");
    if (!image) return;
    image.addEventListener("error", () => {
      if (image.dataset.fallbackApplied === "true") {
        slide.hidden = true;
        console.error(`No se pudo cargar la imagen del plato: ${image.src}`);
        return;
      }
      image.dataset.fallbackApplied = "true";
      image.src = image.dataset.fallback || "/static/img/platos/ceviche-clasico.jpg";
    });
  });

  const showSlide = (index) => {
    slides[activeIndex].classList.remove("is-active");
    slides[activeIndex].setAttribute("aria-hidden", "true");
    activeIndex = (index + slides.length) % slides.length;
    slides[activeIndex].classList.add("is-active");
    slides[activeIndex].setAttribute("aria-hidden", "false");
    updateIndicator();
  };
  heroCarousel.querySelector("[data-hero-previous]")?.addEventListener("click", () => {
    showSlide(activeIndex - 1);
  });
  heroCarousel.querySelector("[data-hero-next]")?.addEventListener("click", () => {
    showSlide(activeIndex + 1);
  });

  if (slides.length > 1 && Number.isFinite(intervalMs) && intervalMs > 0) {
    window.setInterval(() => {
      showSlide(activeIndex + 1);
    }, intervalMs);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeHeroCarousel, {once: true});
} else {
  initializeHeroCarousel();
}

document.addEventListener("click", async (event) => {
  const addButton = event.target.closest("[data-add]");
  const removeButton = event.target.closest("[data-remove]");
  const clearButton = event.target.closest("[data-clear-cart]");
  if (addButton) {
    addButton.disabled = true;
    try {
      const response = await fetch("/api/cart", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({product_id: addButton.dataset.add, quantity: 1})});
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || "No se pudo agregar el producto.");
      document.querySelectorAll("[data-cart-count]").forEach((node) => node.textContent = data.count);
      const oldLabel = addButton.textContent;
      addButton.textContent = "✓ Agregado";
      setTimeout(() => { addButton.textContent = oldLabel; addButton.disabled = false; }, 900);
    } catch (error) {
      addButton.disabled = false;
      window.alert(error.message);
    }
    return;
  }
  if (!removeButton && !clearButton) return;
  if (clearButton && !window.confirm("¿Cancelar toda la orden?")) return;
  const endpoint = clearButton ? "/api/cart/clear" : "/api/cart/remove";
  const payload = clearButton ? {} : {product_id: removeButton.dataset.remove};
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (data.ok) window.location.reload();
    if (!response.ok || !data.ok) throw new Error(data.error || "No se pudo cancelar el elemento.");
  } catch (error) {
    window.alert(error.message);
  }
});
