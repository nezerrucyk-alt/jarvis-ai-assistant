(() => {
  "use strict";

  const REPO_PLACEHOLDER = "__GITHUB_REPOSITORY__";
  const FALLBACK_SLUG = "nezerrucyk-alt/jarvis-ai-assistant";
  const repoLink = "https://github.com/__GITHUB_REPOSITORY__";
  const repoSlug = repoLink.includes(REPO_PLACEHOLDER)
    ? FALLBACK_SLUG
    : repoLink.replace(/^https:\/\/github\.com\//, "").replace(/\/$/, "");

  document.querySelectorAll('a[href*="__GITHUB_REPOSITORY__"]').forEach((link) => {
    link.href = link.href.replace(REPO_PLACEHOLDER, repoSlug);
  });

  /* ── language switch ─────────────────────────────────── */
  const originalText = new Map();
  const titleUk = document.title;
  const titleEn = "J.A.R.V.I.S. — voice AI assistant for Windows";
  const descMeta = document.querySelector('meta[name="description"]');
  const descUk = descMeta ? descMeta.content : "";
  const descEn =
    "J.A.R.V.I.S. is a Windows voice AI assistant with PC control, Roblox Studio MCP, screen vision, translation, local plugins and 67 models.";

  function setLanguage(lang) {
    const isEn = lang === "en";
    document.documentElement.lang = isEn ? "en" : "uk";
    document.querySelectorAll("[data-en]").forEach((node) => {
      if (!originalText.has(node)) {
        originalText.set(node, node.innerHTML);
      }
      node.innerHTML = isEn ? node.dataset.en : originalText.get(node);
    });
    document.querySelectorAll("[data-lang]").forEach((button) => {
      const active = button.dataset.lang === lang;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    document.title = isEn ? titleEn : titleUk;
    if (descMeta) descMeta.content = isEn ? descEn : descUk;
    try {
      localStorage.setItem("jarvis-lang", lang);
    } catch (_) {
      /* private mode */
    }
  }

  document.querySelectorAll("[data-lang]").forEach((button) => {
    button.addEventListener("click", () => setLanguage(button.dataset.lang));
  });

  let savedLang = "uk";
  try {
    savedLang = localStorage.getItem("jarvis-lang") || "uk";
  } catch (_) {
    /* private mode */
  }
  setLanguage(savedLang === "en" ? "en" : "uk");

  /* ── mobile menu ─────────────────────────────────────── */
  const menuButton = document.getElementById("menuBtn");
  const navLinks = document.getElementById("navLinks");
  if (menuButton && navLinks) {
    menuButton.addEventListener("click", () => {
      const open = navLinks.classList.toggle("open");
      menuButton.setAttribute("aria-expanded", String(open));
    });
    navLinks.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        navLinks.classList.remove("open");
        menuButton.setAttribute("aria-expanded", "false");
      });
    });
  }

  /* ── screenshot lightbox ────────────────────────────── */
  const lightbox = document.getElementById("lightbox");
  const lightboxImg = document.getElementById("lightboxImg");
  const lightboxClose = document.getElementById("lightboxClose");

  function closeLightbox() {
    if (!lightbox) return;
    lightbox.classList.remove("open");
    document.body.style.overflow = "";
  }

  document.querySelectorAll(".shot").forEach((shot) => {
    shot.addEventListener("click", () => {
      if (!lightbox || !lightboxImg) return;
      lightboxImg.src = shot.dataset.full || "";
      lightboxImg.alt = shot.querySelector("img")?.alt || "J.A.R.V.I.S.";
      lightbox.classList.add("open");
      document.body.style.overflow = "hidden";
      lightboxClose?.focus();
    });
  });

  lightboxClose?.addEventListener("click", closeLightbox);
  lightbox?.addEventListener("click", (event) => {
    if (event.target === lightbox) closeLightbox();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeLightbox();
  });

  /* ── download links + counter ───────────────────────── */
  const downloadNodes = Array.from(document.querySelectorAll(".js-download"));
  const countNodes = [
    document.getElementById("downloadCount"),
    document.getElementById("footerDownloads"),
  ].filter(Boolean);

  function setCounter(value) {
    const formatted = new Intl.NumberFormat("uk-UA").format(value);
    countNodes.forEach((node) => {
      node.textContent = formatted;
    });
  }

  function useFallbackDownload() {
    downloadNodes.forEach((node) => {
      node.href = "downloads/JARVIS.exe";
      node.setAttribute("download", "");
    });
  }

  async function initDownload() {
    try {
      const response = await fetch(
        `https://api.github.com/repos/${repoSlug}/releases?per_page=20`,
        { headers: { Accept: "application/vnd.github+json" } }
      );
      if (!response.ok) throw new Error(`GitHub API ${response.status}`);
      const releases = await response.json();
      if (!Array.isArray(releases) || releases.length === 0) {
        useFallbackDownload();
        setCounter(0);
        return;
      }

      let total = 0;
      let windowsAsset = null;
      releases.forEach((release) => {
        (release.assets || []).forEach((asset) => {
          total += Number(asset.download_count || 0);
          if (!windowsAsset && /windows|win64|win32|\.exe$/i.test(asset.name || "")) {
            windowsAsset = asset;
          }
        });
      });

      setCounter(total);
      if (windowsAsset?.browser_download_url) {
        downloadNodes.forEach((node) => {
          node.href = windowsAsset.browser_download_url;
          node.removeAttribute("download");
          node.setAttribute("target", "_blank");
          node.setAttribute("rel", "noopener");
        });
      } else {
        const latest = releases.find((release) => !release.draft) || releases[0];
        downloadNodes.forEach((node) => {
          node.href =
            latest.html_url || `https://github.com/${repoSlug}/releases/latest`;
          node.removeAttribute("download");
          node.setAttribute("target", "_blank");
          node.setAttribute("rel", "noopener");
        });
      }
    } catch (error) {
      console.warn("Release lookup failed:", error);
      useFallbackDownload();
      setCounter(0);
    }
  }

  initDownload();

  /* ── copy SHA256 ────────────────────────────────────── */
  const shaNode = document.getElementById("shaValue");
  if (shaNode) {
    shaNode.style.cursor = "copy";
    shaNode.title = "Натисни, щоб скопіювати SHA256";
    shaNode.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(shaNode.textContent.trim());
        const old = shaNode.textContent;
        shaNode.textContent = "Скопійовано ✓";
        setTimeout(() => {
          shaNode.textContent = old;
        }, 1400);
      } catch (_) {
        /* clipboard blocked */
      }
    });
  }
})();
