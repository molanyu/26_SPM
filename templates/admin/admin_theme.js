(function () {
  var storageKey = "admin-theme";
  var allowedThemes = { light: true, dark: true };

  function normalizeTheme(theme) {
    return allowedThemes[theme] ? theme : "light";
  }

  function readStoredTheme() {
    try {
      return normalizeTheme(window.localStorage.getItem(storageKey));
    } catch (error) {
      return "light";
    }
  }

  function writeStoredTheme(theme) {
    try {
      window.localStorage.setItem(storageKey, theme);
    } catch (error) {
      return;
    }
  }

  function applyTheme(theme) {
    var normalizedTheme = normalizeTheme(theme);
    document.documentElement.setAttribute("data-theme", normalizedTheme);
    document.documentElement.style.colorScheme = normalizedTheme === "dark" ? "dark" : "light";
    updateThemeLabels(normalizedTheme);
    return normalizedTheme;
  }

  function updateThemeLabels(theme) {
    var label = theme === "dark" ? "深色" : "浅色";
    var title = theme === "dark" ? "切换到浅色主题" : "切换到深色主题";
    var valueNodes = document.querySelectorAll("[data-theme-toggle-value]");
    var buttonNodes = document.querySelectorAll("[data-theme-toggle]");

    for (var index = 0; index < valueNodes.length; index += 1) {
      valueNodes[index].textContent = label;
    }

    for (var buttonIndex = 0; buttonIndex < buttonNodes.length; buttonIndex += 1) {
      buttonNodes[buttonIndex].setAttribute("title", title);
      buttonNodes[buttonIndex].setAttribute("aria-label", title);
    }
  }

  function bindThemeToggles() {
    var buttons = document.querySelectorAll("[data-theme-toggle]");
    for (var index = 0; index < buttons.length; index += 1) {
      buttons[index].addEventListener("click", function () {
        var nextTheme = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
        applyTheme(nextTheme);
        writeStoredTheme(nextTheme);
      });
    }
  }

  applyTheme(readStoredTheme());

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindThemeToggles, { once: true });
  } else {
    bindThemeToggles();
  }
}());
