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
  const originalPlaceholder = new Map();
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
    document.querySelectorAll("[data-en-placeholder]").forEach((node) => {
      if (!originalPlaceholder.has(node)) {
        originalPlaceholder.set(node, node.getAttribute("placeholder") || "");
      }
      node.setAttribute(
        "placeholder",
        isEn ? node.dataset.enPlaceholder : originalPlaceholder.get(node)
      );
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

  /* ── download links + counter + release metadata ───── */
  const downloadNodes = Array.from(
    document.querySelectorAll(".js-download[data-download]")
  );
  const countNodes = [
    document.getElementById("downloadCount"),
    document.getElementById("footerDownloads"),
  ].filter(Boolean);
  const releaseVersionNodes = Array.from(
    document.querySelectorAll("[data-release-version]")
  );
  const releaseDateNodes = Array.from(
    document.querySelectorAll("[data-release-date]")
  );
  const releaseSumsNodes = Array.from(
    document.querySelectorAll("[data-release-sums]")
  );
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

  function formatReleaseDate(iso) {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "";
    return new Intl.DateTimeFormat("uk-UA", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    })
      .format(date)
      .replace(/\//g, ".");
  }

  function setReleaseMeta(version, publishedAt, sumsUrl) {
    const cleanVersion = String(version || "").replace(/^v/i, "");
    if (cleanVersion) {
      releaseVersionNodes.forEach((node) => {
        node.textContent = cleanVersion;
      });
    }
    if (publishedAt) {
      const text = formatReleaseDate(publishedAt);
      const iso = String(publishedAt).slice(0, 10);
      releaseDateNodes.forEach((node) => {
        if (!text) return;
        node.textContent = text;
        if (node.tagName === "TIME") node.dateTime = iso;
      });
    }
    if (sumsUrl) {
      releaseSumsNodes.forEach((node) => {
        node.href = sumsUrl;
      });
    }
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

      const latest =
        releases.find((release) => !release.prerelease && !release.draft) ||
        releases[0];
      if (latest) {
        const sumsAsset = (latest.assets || []).find((asset) =>
          /^sha256sums\.txt$/i.test(asset.name || "")
        );
        setReleaseMeta(
          latest.tag_name,
          latest.published_at || latest.created_at,
          sumsAsset?.browser_download_url
        );
      }

      let total = 0;
      const found = {};
      const ordered = [
        latest,
        ...releases.filter((release) => release !== latest),
      ].filter(Boolean);

      ordered.forEach((release) => {
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

  /* ── real reviews via public GitHub issues ─────────── */
  const reviewForm = document.getElementById("reviewForm");
  if (reviewForm) {
    const reviewList = document.getElementById("reviewList");
    const reviewAverage = document.getElementById("reviewAverage");
    const reviewAverageStars = document.getElementById("reviewAverageStars");
    const reviewSummary = document.getElementById("reviewSummary");
    const reviewCount = document.getElementById("reviewCount");
    const reviewName = document.getElementById("reviewName");
    const reviewText = document.getElementById("reviewText");
    const reviewCounter = document.getElementById("reviewCounter");
    const reviewStars = Array.from(document.querySelectorAll(".review-star"));
    const reviewRatingLabel = document.getElementById("reviewRatingLabel");
    const reviewError = document.getElementById("reviewError");
    const reviewStatus = document.getElementById("reviewStatus");
    const reviewAll = document.getElementById("reviewAll");
    const REVIEW_MARKER = "<!-- jarvis-review -->";
    const REVIEW_CACHE_KEY = "jarvis-reviews-v1";
    const REVIEW_CACHE_TTL = 10 * 60 * 1000;
    let selectedRating = 0;
    let allReviews = [];

    const isEnglish = () => document.documentElement.lang === "en";
    const t = (uk, en) => (isEnglish() ? en : uk);

    if (reviewAll) {
      reviewAll.href = `https://github.com/${repoSlug}/issues?q=${encodeURIComponent(
        "is:issue jarvis-review"
      )}`;
    }

    function reviewWord(count) {
      if (isEnglish()) return count === 1 ? "review" : "reviews";
      const mod10 = count % 10;
      const mod100 = count % 100;
      if (mod10 === 1 && mod100 !== 11) return "відгук";
      if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
        return "відгуки";
      }
      return "відгуків";
    }

    function formatReviewDate(iso) {
      if (!iso) return "";
      const date = new Date(iso);
      if (Number.isNaN(date.getTime())) return "";
      return new Intl.DateTimeFormat(isEnglish() ? "en-GB" : "uk-UA", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }).format(date);
    }

    function parseReview(issue) {
      const body = String(issue.body || "");
      if (!body.includes(REVIEW_MARKER)) return null;
      const ratingMatch = body.match(
        /(?:Оцінка|Rating)[^\d\n]{0,12}([1-5])\s*\/\s*5/i
      );
      const textMatch = body.match(
        /(?:Відгук|Review)\s*:?\s*\**\s*([\s\S]+)/i
      );
      if (!ratingMatch || !textMatch) return null;
      const nickMatch = body.match(
        /(?:Нік|Nickname)\s*:?\s*\**\s*([^\r\n]{1,40})/i
      );
      let text = textMatch[1]
        .replace(/<!--[\s\S]*?-->/g, "")
        .replace(/\n---[\s\S]*$/, "")
        .trim();
      if (!text) return null;
      if (text.length > 5000) text = text.slice(0, 5000);
      return {
        rating: Number(ratingMatch[1]),
        nick: (
          (nickMatch ? nickMatch[1] : "") ||
          issue.user?.login ||
          t("Користувач", "User")
        ).trim(),
        text,
        url: issue.html_url || "",
        avatar: issue.user?.avatar_url || "",
        login: issue.user?.login || "",
        created: issue.created_at || "",
      };
    }

    function reviewEmpty(icon, title, detail, retry) {
      const box = document.createElement("div");
      box.className = "review-empty";
      const mark = document.createElement("span");
      mark.className = "review-empty-icon";
      mark.textContent = icon;
      const strong = document.createElement("strong");
      strong.textContent = title;
      const span = document.createElement("span");
      span.textContent = detail;
      box.append(mark, strong, span);
      if (retry) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "btn btn-ghost btn-small";
        button.textContent = t("Спробувати ще", "Try again");
        button.addEventListener("click", () => fetchReviews(true));
        box.append(button);
      }
      return box;
    }

    function reviewCard(review) {
      const article = document.createElement("article");
      article.className = "review-card";

      const head = document.createElement("div");
      head.className = "review-card-head";

      const avatar = document.createElement("span");
      avatar.className = "review-avatar";
      if (review.avatar) {
        const image = document.createElement("img");
        image.src = review.avatar;
        image.alt = "";
        image.loading = "lazy";
        image.referrerPolicy = "no-referrer";
        avatar.append(image);
      } else {
        avatar.textContent = (review.nick || "J").slice(0, 1).toUpperCase();
      }

      const who = document.createElement("div");
      who.className = "review-who";
      const strong = document.createElement("strong");
      strong.textContent = review.nick;
      const meta = document.createElement("span");
      meta.textContent = [
        formatReviewDate(review.created),
        review.login ? `@${review.login}` : "",
      ]
        .filter(Boolean)
        .join(" · ");
      who.append(strong, meta);

      const stars = document.createElement("span");
      stars.className = "review-card-stars";
      stars.textContent = "★".repeat(review.rating) + "☆".repeat(5 - review.rating);
      stars.setAttribute("aria-label", `${review.rating} / 5`);

      head.append(avatar, who, stars);

      const text = document.createElement("p");
      text.textContent = review.text;

      const link = document.createElement("a");
      link.className = "review-card-link";
      link.href = review.url;
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = `${t("Відкрити на GitHub", "Open on GitHub")} ↗`;

      article.append(head, text, link);
      return article;
    }

    function renderReviews(reviews) {
      allReviews = Array.isArray(reviews) ? reviews : [];
      const count = allReviews.length;
      if (reviewCount) reviewCount.textContent = String(count);

      if (!count) {
        if (reviewAverage) reviewAverage.textContent = "—";
        if (reviewAverageStars) reviewAverageStars.textContent = "☆☆☆☆☆";
        if (reviewSummary) {
          reviewSummary.textContent = t("Ще немає відгуків", "No reviews yet");
        }
        reviewList.replaceChildren(
          reviewEmpty(
            "★",
            t("Поки що порожньо", "Nothing here yet"),
            t(
              "Стань першим, хто залишить чесний відгук.",
              "Be the first to leave an honest review."
            )
          )
        );
        return;
      }

      const average =
        allReviews.reduce((sum, review) => sum + review.rating, 0) / count;
      if (reviewAverage) reviewAverage.textContent = average.toFixed(1);
      const rounded = Math.round(average);
      if (reviewAverageStars) {
        reviewAverageStars.textContent =
          "★".repeat(rounded) + "☆".repeat(5 - rounded);
      }
      if (reviewSummary) {
        reviewSummary.textContent = `${count} ${reviewWord(count)} · ${t(
          "середня оцінка",
          "average rating"
        )}`;
      }

      const fragment = document.createDocumentFragment();
      allReviews.slice(0, 12).forEach((review) => {
        fragment.append(reviewCard(review));
      });
      reviewList.replaceChildren(fragment);
    }

    function readReviewCache() {
      try {
        const raw = sessionStorage.getItem(REVIEW_CACHE_KEY);
        if (!raw) return null;
        const data = JSON.parse(raw);
        if (!data || Date.now() - Number(data.ts || 0) > REVIEW_CACHE_TTL) {
          return null;
        }
        return Array.isArray(data.reviews) ? data.reviews : null;
      } catch (_) {
        return null;
      }
    }

    function writeReviewCache(reviews) {
      try {
        sessionStorage.setItem(
          REVIEW_CACHE_KEY,
          JSON.stringify({ ts: Date.now(), reviews })
        );
      } catch (_) {
        /* private mode */
      }
    }

    async function fetchReviews(force = false) {
      if (!force) {
        const cached = readReviewCache();
        if (cached) {
          renderReviews(cached);
          return;
        }
      }
      if (reviewList) {
        reviewList.replaceChildren(
          reviewEmpty(
            "…",
            t("Завантажую відгуки…", "Loading reviews…"),
            t("Це займе секунду.", "This takes a second.")
          )
        );
      }
      try {
        const response = await fetch(
          `https://api.github.com/repos/${repoSlug}/issues?state=all&sort=created&direction=desc&per_page=100`,
          { headers: { Accept: "application/vnd.github+json" } }
        );
        if (!response.ok) throw new Error(`GitHub API ${response.status}`);
        const issues = await response.json();
        if (!Array.isArray(issues)) throw new Error("Unexpected response");
        const reviews = issues
          .filter((issue) => !issue.pull_request)
          .map(parseReview)
          .filter(Boolean);
        writeReviewCache(reviews);
        renderReviews(reviews);
      } catch (error) {
        console.warn("Reviews lookup failed:", error);
        if (reviewAverage) reviewAverage.textContent = "—";
        if (reviewAverageStars) reviewAverageStars.textContent = "☆☆☆☆☆";
        if (reviewSummary) {
          reviewSummary.textContent = t("Не вдалося завантажити", "Could not load");
        }
        if (reviewList) {
          reviewList.replaceChildren(
            reviewEmpty(
              "!",
              t("GitHub не відповів", "GitHub did not respond"),
              t(
                "Можливо, вичерпано ліміт запитів. Відкрий список напряму.",
                "The API rate limit may be exhausted. Open the list directly."
              ),
              true
            )
          );
        }
      }
    }

    function paintStars(value) {
      reviewStars.forEach((button, index) => {
        button.classList.toggle("on", index < value);
      });
    }

    function updateRatingLabel() {
      if (!reviewRatingLabel) return;
      const labelsUk = ["Обери оцінку", "Погано", "Так собі", "Нормально", "Добре", "Супер"];
      const labelsEn = ["Pick a rating", "Bad", "Meh", "Okay", "Good", "Great"];
      const labels = isEnglish() ? labelsEn : labelsUk;
      reviewRatingLabel.textContent = labels[selectedRating] || labels[0];
    }

    function setRating(value) {
      selectedRating = value;
      reviewStars.forEach((button, index) => {
        button.classList.toggle("on", index < value);
        button.setAttribute("aria-checked", String(index === value - 1));
      });
      updateRatingLabel();
      clearReviewError();
    }

    function clearReviewError() {
      if (!reviewError) return;
      reviewError.hidden = true;
      reviewError.textContent = "";
    }

    function showReviewError(message, field) {
      if (reviewError) {
        reviewError.textContent = message;
        reviewError.hidden = false;
      }
      if (field) field.focus();
      if (reviewStatus) {
        reviewStatus.textContent = "";
        reviewStatus.className = "review-status";
      }
    }

    reviewStars.forEach((button) => {
      const value = Number(button.dataset.star || 0);
      button.addEventListener("click", () => setRating(value));
      button.addEventListener("mouseenter", () => paintStars(value));
      button.addEventListener("focus", () => paintStars(value));
      button.addEventListener("mouseleave", () => paintStars(selectedRating));
      button.addEventListener("blur", () => paintStars(selectedRating));
    });

    reviewText?.addEventListener("input", () => {
      const length = reviewText.value.length;
      if (reviewCounter) {
        reviewCounter.textContent = `${length} / 5000`;
        reviewCounter.classList.toggle("near", length > 4500);
      }
      clearReviewError();
    });

    reviewName?.addEventListener("input", clearReviewError);

    reviewForm.addEventListener("submit", (event) => {
      event.preventDefault();
      clearReviewError();
      if (reviewStatus) {
        reviewStatus.textContent = "";
        reviewStatus.className = "review-status";
      }
      const nick = (reviewName?.value || "").trim().replace(/\s+/g, " ");
      const text = (reviewText?.value || "").trim();

      if (nick.length < 2) {
        showReviewError(
          t("Вкажи нік (мінімум 2 символи).", "Enter a nickname (at least 2 characters)."),
          reviewName
        );
        return;
      }
      if (nick.length > 40) {
        showReviewError(
          t("Нік має бути до 40 символів.", "The nickname must be 40 characters or less."),
          reviewName
        );
        return;
      }
      if (!selectedRating) {
        showReviewError(
          t("Обери оцінку від 1 до 5.", "Pick a rating from 1 to 5.")
        );
        return;
      }
      if (text.length < 10) {
        showReviewError(
          t("Відгук має містити хоча б 10 символів.", "The review must be at least 10 characters."),
          reviewText
        );
        return;
      }
      if (text.length > 5000) {
        showReviewError(
          t("Відгук має бути до 5000 символів.", "The review must be 5000 characters or less."),
          reviewText
        );
        return;
      }

      const title = `[${t("Відгук", "Review")}] ${nick} — ${selectedRating}/5`;
      const body = [
        REVIEW_MARKER,
        `**${t("Оцінка", "Rating")}:** ${selectedRating}/5`,
        `**${t("Нік", "Nickname")}:** ${nick}`,
        "",
        `**${t("Відгук", "Review")}:**`,
        text,
        "",
        "---",
        `_${t(
          "Опубліковано з сайту J.A.R.V.I.S.",
          "Posted from the J.A.R.V.I.S. website"
        )}_`,
      ].join("\n");
      const url = `https://github.com/${repoSlug}/issues/new?title=${encodeURIComponent(
        title
      )}&body=${encodeURIComponent(body)}&labels=review`;

      const popup = window.open(url, "_blank", "noopener");
      if (!popup) {
        if (reviewStatus) {
          reviewStatus.className = "review-status error";
          reviewStatus.append(
            document.createTextNode(
              t("Браузер заблокував вікно. ", "The browser blocked the popup. ")
            )
          );
          const link = document.createElement("a");
          link.href = url;
          link.target = "_blank";
          link.rel = "noopener";
          link.textContent = t("Відкрити GitHub вручну", "Open GitHub manually");
          reviewStatus.append(link);
        }
        return;
      }

      if (reviewStatus) {
        reviewStatus.className = "review-status ok";
        reviewStatus.textContent = t(
          "Готово: у GitHub натисни «Submit new issue», щоб опублікувати відгук.",
          "Done: click «Submit new issue» on GitHub to publish your review."
        );
      }
    });

    document.querySelectorAll("[data-lang]").forEach((button) => {
      button.addEventListener("click", () => {
        setTimeout(() => {
          renderReviews(allReviews);
          updateRatingLabel();
        }, 0);
      });
    });

    fetchReviews();
  }

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

  /* ── 3D logo intro ──────────────────────────────────── */
  const logoIntro = document.getElementById("logoIntro");
  const logoVideo = document.getElementById("logoIntroVideo");
  const logoSkip = document.getElementById("logoIntroSkip");
  const logoSeenKey = "jarvis-logo-intro-seen";
  let logoCloseTimer = null;
  let logoEndTimer = null;

  function closeLogoIntro() {
    if (!logoIntro || logoIntro.hidden) return;
    logoIntro.classList.remove("open");
    document.body.classList.remove("intro-open");
    if (logoEndTimer) {
      clearTimeout(logoEndTimer);
      logoEndTimer = null;
    }
    logoCloseTimer = setTimeout(() => {
      logoIntro.hidden = true;
      if (logoVideo) {
        logoVideo.pause();
        logoVideo.currentTime = 0;
      }
    }, reduceMotion ? 0 : 420);
  }

  function showLogoIntro(force = false) {
    if (!logoIntro || !logoVideo || reduceMotion) return;
    if (!force) {
      try {
        if (sessionStorage.getItem(logoSeenKey)) return;
      } catch (_) {
        /* private mode */
      }
    }
    if (logoCloseTimer) {
      clearTimeout(logoCloseTimer);
      logoCloseTimer = null;
    }
    if (logoEndTimer) {
      clearTimeout(logoEndTimer);
      logoEndTimer = null;
    }
    logoIntro.hidden = false;
    document.body.classList.add("intro-open");
    requestAnimationFrame(() => logoIntro.classList.add("open"));
    try {
      logoVideo.currentTime = 0;
      const playback = logoVideo.play();
      if (playback && typeof playback.catch === "function") {
        playback.catch(() => closeLogoIntro());
      }
    } catch (_) {
      closeLogoIntro();
    }
    try {
      sessionStorage.setItem(logoSeenKey, "1");
    } catch (_) {
      /* private mode */
    }
    logoSkip?.focus({ preventScroll: true });
  }

  logoVideo?.addEventListener("ended", () => {
    logoEndTimer = setTimeout(closeLogoIntro, 650);
  });
  logoSkip?.addEventListener("click", closeLogoIntro);
  logoIntro?.addEventListener("click", (event) => {
    if (event.target === logoIntro) closeLogoIntro();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && logoIntro && !logoIntro.hidden) closeLogoIntro();
  });
  document.querySelectorAll(".js-brand").forEach((link) => {
    link.addEventListener("click", () => showLogoIntro(true));
  });

  if (!reduceMotion && window.scrollY < 8 && !window.location.hash) {
    showLogoIntro(false);
  }

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
  const trackedSections = ["features", "deck", "shots", "demo", "plugins", "reviews", "changelog", "install", "verify"]
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
    document.querySelectorAll(".feature, .platform-card, .step, .review, .review-card, .verify-card").forEach((card) => {
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
