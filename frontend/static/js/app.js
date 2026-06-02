const root = document.documentElement;
const themeToggle = document.querySelector("[data-theme-toggle]");
const themeIcons = document.querySelectorAll("[data-theme-icon]");
const menuToggle = document.querySelector("[data-menu-toggle]");
const mobileMenu = document.querySelector("[data-mobile-menu]");

const storedTheme = localStorage.getItem("dailybread-theme");
const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;

function setTheme(theme) {
  const useDark = theme === "dark";
  root.classList.toggle("dark", useDark);
  localStorage.setItem("dailybread-theme", theme);
  themeToggle?.setAttribute("aria-pressed", String(useDark));

  themeIcons.forEach((icon) => {
    const isMoon = icon.dataset.themeIcon === "moon";
    icon.classList.toggle("hidden", useDark ? !isMoon : isMoon);
  });
}

setTheme(storedTheme || (prefersDark ? "dark" : "light"));

themeToggle?.addEventListener("click", () => {
  setTheme(root.classList.contains("dark") ? "light" : "dark");
});

menuToggle?.addEventListener("click", () => {
  const isOpen = !mobileMenu?.classList.contains("hidden");
  mobileMenu?.classList.toggle("hidden", isOpen);
  menuToggle.setAttribute("aria-expanded", String(!isOpen));
});
