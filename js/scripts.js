/* Braille Mind — small progressive-enhancement script
   Handles: theme toggle (light/dark, remembers choice) and mobile nav. */
(function () {
  "use strict";

  // ---- Theme ----
  var root = document.documentElement;
  var stored = null;
  try { stored = localStorage.getItem("bm-theme"); } catch (e) {}
  if (stored === "light" || stored === "dark") {
    root.setAttribute("data-theme", stored);
  }

  function currentTheme() {
    var attr = root.getAttribute("data-theme");
    if (attr) return attr;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function setToggleLabel(btn) {
    var isDark = currentTheme() === "dark";
    btn.setAttribute("aria-pressed", String(isDark));
    btn.setAttribute("aria-label", isDark ? "Switch to light theme" : "Switch to dark theme");
    btn.textContent = isDark ? "☀️" : "🌙"; // sun / moon
  }

  document.addEventListener("DOMContentLoaded", function () {
    var toggle = document.querySelector(".theme-toggle");
    if (toggle) {
      setToggleLabel(toggle);
      toggle.addEventListener("click", function () {
        var next = currentTheme() === "dark" ? "light" : "dark";
        root.setAttribute("data-theme", next);
        try { localStorage.setItem("bm-theme", next); } catch (e) {}
        setToggleLabel(toggle);
      });
    }

    // ---- Mobile nav ----
    var navToggle = document.querySelector(".nav-toggle");
    var navLinks = document.querySelector(".nav-links");
    if (navToggle && navLinks) {
      navToggle.addEventListener("click", function () {
        var open = navLinks.classList.toggle("open");
        navToggle.setAttribute("aria-expanded", String(open));
      });
    }
  });
})();
