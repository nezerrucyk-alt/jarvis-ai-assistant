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
  const titleEn = "J.A.R.V.I.S. — voice AI assistant for Windows, macOS and Linux";
  const descMeta = document.querySelector('meta[name="description"]');
  const descUk = descMeta ? descMeta.content : "";
  const descEn =
    "J.A.R.V.I.S. is a desktop voice AI assistant for Windows, macOS and Linux: chat, voice, plugins, screen vision, translation and 78 models.";

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

  /* ── install tabs ───────────────────────────────────── */
  const osTabs = Array.from(document.querySelectorAll("[data-os-tab]"));
  const osPanes = Array.from(document.querySelectorAll("[data-os-pane]"));

  function setOS(os, persist = true) {
    if (!osPanes.some((pane) => pane.dataset.osPane === os)) os = "windows";
    osTabs.forEach((tab) => {
      const active = tab.dataset.osTab === os;
      tab.classList.toggle("active", active);
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    osPanes.forEach((pane) => {
      const active = pane.dataset.osPane === os;
      pane.classList.toggle("active", active);
      pane.hidden = !active;
    });
    if (persist) {
      try {
        localStorage.setItem("jarvis-os", os);
      } catch (_) {
        /* private mode */
      }
    }
  }

  osTabs.forEach((tab) => {
    tab.addEventListener("click", () => setOS(tab.dataset.osTab));
  });

  function detectOS() {
    const ua = navigator.userAgent.toLowerCase();
    if (ua.includes("mac")) return "macos";
    if (ua.includes("linux") || ua.includes("android")) return "linux";
    return "windows";
  }

  let savedOS = detectOS();
  try {
    savedOS = localStorage.getItem("jarvis-os") || savedOS;
  } catch (_) {
    /* private mode */
  }
  setOS(savedOS, false);

  /* ── download links + counter ───────────────────────── */
  const downloadNodes = Array.from(
    document.querySelectorAll(".js-download[data-download]")
  );
  const countNodes = [
    document.getElementById("downloadCount"),
    document.getElementById("footerDownloads"),
  ].filter(Boolean);
  const fallbackLinks = {
    windows: `https://github.com/${repoSlug}/releases/latest/download/JARVIS.exe`,
    macos: `https://github.com/${repoSlug}/releases/latest/download/JARVIS-macOS.zip`,
    linux: `https://github.com/${repoSlug}/releases/latest/download/JARVIS-Linux.tar.gz`,
  };

  function setCounter(value) {
    const formatted = new Intl.NumberFormat("uk-UA").format(value);
    countNodes.forEach((node) => {
      node.textContent = formatted;
    });
  }

  function setDownload(platform, url) {
    downloadNodes
      .filter((node) => node.dataset.download === platform)
      .forEach((node) => {
        node.href = url;
        node.removeAttribute("download");
        node.setAttribute("target", "_blank");
        node.setAttribute("rel", "noopener");
      });
  }

  function useFallbackDownloads() {
    Object.entries(fallbackLinks).forEach(([platform, url]) => {
      setDownload(platform, url);
    });
  }

  function matchesPlatform(platform, name) {
    const lower = (name || "").toLowerCase();
    if (platform === "windows") {
      return lower.endsWith(".exe") && /win|jarvis/.test(lower);
    }
    if (platform === "macos") {
      return lower.includes("macos") || lower.includes("darwin") || lower.endsWith(".dmg");
    }
    if (platform === "linux") {
      return (
        lower.includes("linux") ||
        lower.endsWith(".appimage") ||
        lower.endsWith(".tar.gz")
      );
    }
    return false;
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
        useFallbackDownloads();
        setCounter(0);
        return;
      }

      let total = 0;
      const found = {};
      releases.forEach((release) => {
        (release.assets || []).forEach((asset) => {
          total += Number(asset.download_count || 0);
          ["windows", "macos", "linux"].forEach((platform) => {
            if (!found[platform] && matchesPlatform(platform, asset.name)) {
              found[platform] = asset.browser_download_url;
            }
          });
        });
      });

      setCounter(total);
      Object.entries(fallbackLinks).forEach(([platform, fallback]) => {
        setDownload(platform, found[platform] || fallback);
      });
    } catch (error) {
      console.warn("Release lookup failed:", error);
      useFallbackDownloads();
      setCounter(0);
    }
  }

  initDownload();

  /* ── copy SHA256 ────────────────────────────────────── */
  document.querySelectorAll(".js-sha").forEach((node) => {
    node.addEventListener("click", async () => {
      const full = node.dataset.sha || "";
      if (!full) return;
      try {
        await navigator.clipboard.writeText(full);
        const old = node.textContent;
        node.textContent = "Скопійовано ✓";
        setTimeout(() => {
          node.textContent = old;
        }, 1400);
      } catch (_) {
        /* clipboard blocked */
      }
    });
  });

  /* ── scroll progress, sticky nav, back to top ───────── */
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const progressBar = document.getElementById("scrollProgress");
  const navBar = document.querySelector(".nav");
  const toTop = document.getElementById("toTop");

  function onScroll() {
    const root = document.documentElement;
    const max = root.scrollHeight - window.innerHeight;
    const ratio = max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0;
    if (progressBar) progressBar.style.transform = `scaleX(${ratio})`;
    if (navBar) navBar.classList.toggle("scrolled", window.scrollY > 12);
    if (toTop) toTop.classList.toggle("show", window.scrollY > 720);
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll);
  onScroll();

  toTop?.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
  });

  /* ── reveal on scroll ───────────────────────────────── */
  const revealTargets = document.querySelectorAll("[data-reveal], [data-stagger]");
  if ("IntersectionObserver" in window && !reduceMotion) {
    const revealObserver = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("in");
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -40px 0px" }
    );
    revealTargets.forEach((node) => revealObserver.observe(node));
  } else {
    revealTargets.forEach((node) => node.classList.add("in"));
  }

  /* ── animated counters ──────────────────────────────── */
  function animateCounter(node) {
    const target = Number(node.dataset.count || 0);
    if (!Number.isFinite(target)) return;
    if (reduceMotion) {
      node.textContent = String(target);
      return;
    }
    const duration = 1100;
    let started = null;
    function frame(timestamp) {
      if (started === null) started = timestamp;
      const progress = Math.min(1, (timestamp - started) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      node.textContent = String(Math.round(target * eased));
      if (progress < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  const counters = Array.from(document.querySelectorAll("[data-count]"));
  if ("IntersectionObserver" in window && !reduceMotion) {
    const counterObserver = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          animateCounter(entry.target);
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.5 }
    );
    counters.forEach((node) => counterObserver.observe(node));
  } else {
    counters.forEach(animateCounter);
  }

  /* ── active nav link ────────────────────────────────── */
  const navAnchors = Array.from(document.querySelectorAll('.nav-links a[href^="#"]'));
  const trackedSections = ["features", "deck", "shots", "demo", "plugins", "changelog", "install"]
    .map((id) => document.getElementById(id))
    .filter(Boolean);

  if ("IntersectionObserver" in window) {
    const navObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const hash = `#${entry.target.id}`;
          navAnchors.forEach((anchor) => {
            anchor.classList.toggle("active", anchor.getAttribute("href") === hash);
          });
        });
      },
      { rootMargin: "-40% 0px -55% 0px", threshold: 0 }
    );
    trackedSections.forEach((section) => navObserver.observe(section));
  }

  /* ── pointer spotlight + hero tilt ──────────────────── */
  const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;

  if (finePointer) {
    document.querySelectorAll(".feature, .platform-card, .step, .review").forEach((card) => {
      card.addEventListener("pointermove", (event) => {
        const rect = card.getBoundingClientRect();
        card.style.setProperty("--mx", `${event.clientX - rect.left}px`);
        card.style.setProperty("--my", `${event.clientY - rect.top}px`);
      });
    });

    const appFrame = document.querySelector(".app-frame");
    const heroVisual = document.querySelector(".hero-visual");
    if (appFrame && heroVisual && !reduceMotion) {
      heroVisual.addEventListener("pointermove", (event) => {
        const rect = heroVisual.getBoundingClientRect();
        const x = (event.clientX - rect.left) / rect.width - 0.5;
        const y = (event.clientY - rect.top) / rect.height - 0.5;
        appFrame.style.setProperty("--ry", `${-3 + x * 4.5}deg`);
        appFrame.style.setProperty("--rx", `${1.2 - y * 3.5}deg`);
      });
      heroVisual.addEventListener("pointerleave", () => {
        appFrame.style.removeProperty("--ry");
        appFrame.style.removeProperty("--rx");
      });
    }
  }

  /* ── recommend the visitor's platform ───────────────── */
  const isMobile = /android|iphone|ipad|ipod|mobile/i.test(navigator.userAgent);
  if (!isMobile) {
    const recommendedOS = detectOS();
    document.querySelector(`[data-os-tab="${recommendedOS}"]`)?.classList.add("recommended");
    const recommendedCard = document.querySelector(
      `.platform-card [data-download="${recommendedOS}"]`
    )?.closest(".platform-card");
    recommendedCard?.classList.add("recommended");
  }

  /* ── copy plugin code ───────────────────────────────── */
  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      const target = document.getElementById(button.dataset.copy || "");
      if (!target) return;
      const original = button.textContent;
      const english = document.documentElement.lang === "en";
      try {
        await navigator.clipboard.writeText(target.textContent || "");
        button.textContent = english ? "Copied ✓" : "Скопійовано ✓";
      } catch (_) {
        button.textContent = english ? "Press Ctrl+C" : "Натисни Ctrl+C";
      }
      setTimeout(() => {
        button.textContent = original;
      }, 1600);
    });
  });
})();
