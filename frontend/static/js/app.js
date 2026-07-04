const menuToggle = document.querySelector("[data-menu-toggle]");
const mobileMenu = document.querySelector("[data-mobile-menu]");

menuToggle?.addEventListener("click", () => {
  const isOpen = !mobileMenu?.classList.contains("hidden");
  mobileMenu?.classList.toggle("hidden", isOpen);
  menuToggle.setAttribute("aria-expanded", String(!isOpen));
});
