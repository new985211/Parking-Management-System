/**
 * Parking LPR System — Client Library v2
 * Toast, Confirm, AJAX, Keyboard, Theme, Menu, Active Nav
 */
(function () {
  "use strict";

  // ============================================================
  // 1. Toast Notification System
  // ============================================================
  const TOAST_CONTAINER = document.createElement("div");
  TOAST_CONTAINER.className = "toast-container";
  TOAST_CONTAINER.setAttribute("aria-live", "polite");
  TOAST_CONTAINER.setAttribute("aria-atomic", "false");
  document.body.appendChild(TOAST_CONTAINER);

  const ICONS = {
    success: "✅", error: "❌", warning: "⚠️", info: "ℹ️",
  };

  window.showToast = function (message, type, title, duration) {
    type = type || "info";
    title = title || "";
    duration = duration || 4000;
    message = message || "";

    var toast = document.createElement("div");
    toast.className = "toast toast-" + type;
    toast.setAttribute("role", "alert");

    var iconSpan = document.createElement("span");
    iconSpan.className = "toast-icon";
    iconSpan.textContent = ICONS[type] || ICONS.info;
    toast.appendChild(iconSpan);

    var body = document.createElement("div");
    body.className = "toast-body";
    if (title) {
      var t = document.createElement("div");
      t.className = "toast-title";
      t.textContent = title;
      body.appendChild(t);
    }
    var m = document.createElement("div");
    m.textContent = message;
    body.appendChild(m);
    toast.appendChild(body);

    var closeBtn = document.createElement("button");
    closeBtn.className = "toast-close";
    closeBtn.setAttribute("aria-label", "关闭通知");
    closeBtn.innerHTML = "✕";
    closeBtn.onclick = function () { dismissToast(toast); };
    toast.appendChild(closeBtn);

    TOAST_CONTAINER.appendChild(toast);

    var timer = setTimeout(function () { dismissToast(toast); }, duration);
    toast._timer = timer;

    // Pause timer on hover
    toast.addEventListener("mouseenter", function () { clearTimeout(toast._timer); });
    toast.addEventListener("mouseleave", function () {
      toast._timer = setTimeout(function () { dismissToast(toast); }, 2000);
    });

    return toast;
  };

  function dismissToast(toast) {
    if (toast._dismissing) return;
    toast._dismissing = true;
    clearTimeout(toast._timer);
    toast.classList.add("toast-exit");
    toast.addEventListener("animationend", function () {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    });
  }

  // ============================================================
  // 2. Confirm Dialog
  // ============================================================
  window.showConfirm = function (title, message, confirmText, cancelText, danger) {
    return new Promise(function (resolve) {
      var overlay = document.createElement("div");
      overlay.className = "dialog-overlay";
      overlay.setAttribute("role", "dialog");
      overlay.setAttribute("aria-modal", "true");
      overlay.setAttribute("aria-labelledby", "dialog-title");

      var dialog = document.createElement("div");
      dialog.className = "dialog";

      var h = document.createElement("div");
      h.className = "dialog-title";
      h.id = "dialog-title";
      h.textContent = title || "确认操作";
      dialog.appendChild(h);

      var b = document.createElement("div");
      b.className = "dialog-body";
      b.textContent = message || "确定要执行此操作吗？";
      dialog.appendChild(b);

      var actions = document.createElement("div");
      actions.className = "dialog-actions";

      var cancel = document.createElement("button");
      cancel.className = "btn btn-secondary";
      cancel.textContent = cancelText || "取消";
      cancel.onclick = function () { close(false); };
      actions.appendChild(cancel);

      var confirm = document.createElement("button");
      confirm.className = "btn " + (danger ? "btn-danger" : "btn-primary");
      confirm.textContent = confirmText || "确定";
      confirm.onclick = function () { close(true); };
      actions.appendChild(confirm);

      dialog.appendChild(actions);
      overlay.appendChild(dialog);
      document.body.appendChild(overlay);

      // Focus trap
      confirm.focus();
      overlay.addEventListener("keydown", function (e) {
        if (e.key === "Escape") { close(false); e.preventDefault(); }
      });

      function close(result) {
        overlay.removeEventListener("keydown", function () {});
        overlay.addEventListener("animationend", function () {
          if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
        });
        overlay.style.opacity = "0";
        resolve(result);
      }

      overlay.addEventListener("click", function (e) {
        if (e.target === overlay) close(false);
      });
    });
  };

  // ============================================================
  // 3. Loading Button State
  // ============================================================
  window.setBtnLoading = function (btn, loading) {
    if (loading) {
      btn.classList.add("is-loading");
      btn.disabled = true;
      btn.setAttribute("aria-busy", "true");
    } else {
      btn.classList.remove("is-loading");
      btn.disabled = false;
      btn.removeAttribute("aria-busy");
    }
  };

  // ============================================================
  // 4. AJAX Helpers
  // ============================================================
  window.apiPost = function (url, data) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }).then(function (r) { return r.json(); });
  };

  window.apiGet = function (url) {
    return fetch(url).then(function (r) { return r.json(); });
  };

  // ============================================================
  // 5. Dashboard AJAX Refresh (no full page reload)
  // ============================================================
  var refreshInterval = null;

  function refreshDashboard() {
    fetch("/api/stats")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.success) return;
        var els = {
          todayIn: document.getElementById("stat-today-in"),
          todayOut: document.getElementById("stat-today-out"),
          current: document.getElementById("stat-current"),
          revenue: document.getElementById("stat-revenue"),
          reviewBadge: document.getElementById("review-badge"),
        };
        if (els.todayIn) els.todayIn.textContent = data.today_in;
        if (els.todayOut) els.todayOut.textContent = data.today_out;
        if (els.current) els.current.textContent = data.today_in - data.today_out;
        if (els.revenue) els.revenue.textContent = "¥" + data.today_revenue.toFixed(2);
        if (els.reviewBadge) {
          if (data.pending_review > 0) {
            els.reviewBadge.textContent = data.pending_review;
            els.reviewBadge.style.display = "inline-flex";
          } else {
            els.reviewBadge.style.display = "none";
          }
        }
      })
      .catch(function () {});

    // Also refresh recent records via dedicated API
    fetch("/api/recent")
      .then(function (r) { return r.json(); })
      .then(function (resp) {
        if (!resp.success || !resp.records) return;
        var list = document.getElementById("record-list");
        if (!list) return;
        list.innerHTML = resp.records.map(function (r) {
          return '<article class="record-item" tabindex="0">' +
            '<div class="record-left">' +
            '<span class="plate plate-clickable" title="点击复制车牌号" role="button" tabindex="0">' + r.plate_number + '</span>' +
            '<span class="tag tag-' + r.event_type + '">' + (r.event_type === "enter" ? "入场" : "出场") + '</span>' +
            (r.need_review ? '<span class="tag tag-review">待审核</span>' : '') +
            '</div>' +
            '<div class="record-right">' +
            (r.fee > 0 ? '<span class="tag-fee">¥' + r.fee.toFixed(2) + '</span>' : '') +
            '<time class="text-muted" style="font-size:var(--text-xs);" datetime="' + r.created_at + '">' + r.created_at + '</time>' +
            '</div></article>';
        }).join("");
      })
      .catch(function () {});
  }

  function startAutoRefresh() {
    if (refreshInterval) return;
    refreshInterval = setInterval(refreshDashboard, 30000);
  }

  function stopAutoRefresh() {
    if (refreshInterval) { clearInterval(refreshInterval); refreshInterval = null; }
  }

  // Pause refresh when page is hidden
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) stopAutoRefresh();
    else startAutoRefresh();
  });

  // Start if on dashboard
  if (window.location.pathname === "/") {
    startAutoRefresh();
  }

  // ============================================================
  // 6. Copy Plate to Clipboard
  // ============================================================
  window.copyPlate = function (el) {
    var text = el.textContent.trim();
    if (!text) return;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () {
        el.classList.add("copied");
        showToast("已复制: " + text, "success", "📋 复制成功", 1500);
        setTimeout(function () { el.classList.remove("copied"); }, 800);
      }).catch(function () {
        showToast("复制失败，请手动复制", "warning");
      });
    } else {
      // Fallback for older browsers
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); showToast("已复制: " + text, "success", "📋 复制成功", 1500); }
      catch (e) { showToast("复制失败", "warning"); }
      document.body.removeChild(ta);
    }
  };

  // ============================================================
  // 6b. Undo-capable Action
  // ============================================================
  window.doWithUndo = function (action, undoFn, message) {
    action().then(function (result) {
      if (!result || result.error) {
        showToast(result ? result.error : "操作失败", "error");
        return;
      }
      var toast = showToast(
        '<span class="toast-undo">' + (message || "操作完成") +
        ' <button class="undo-btn" aria-label="撤销">↩ 撤销</button></span>',
        "success", "", 6000
      );

      // Bind undo to the toast button
      setTimeout(function () {
        var undoBtn = toast.querySelector(".undo-btn");
        if (undoBtn) {
          undoBtn.onclick = function () {
            undoFn().then(function () {
              showToast("已撤销", "info");
            }).catch(function () {
              showToast("撤销失败", "error");
            });
            dismissToast(toast);
          };
        }
      }, 50);
    });
  };

  // ============================================================
  // 6c. Table Sorting
  // ============================================================
  function initTableSort() {
    document.querySelectorAll(".data-table th[aria-sort]").forEach(function (th) {
      th.addEventListener("click", function () {
        var table = th.closest("table");
        var tbody = table.querySelector("tbody");
        if (!tbody) return;
        var colIndex = Array.from(th.parentNode.children).indexOf(th);
        var currentSort = th.getAttribute("aria-sort");
        var ascending = currentSort !== "ascending";

        // Reset all headers
        table.querySelectorAll("th[aria-sort]").forEach(function (h) {
          h.setAttribute("aria-sort", "none");
        });
        th.setAttribute("aria-sort", ascending ? "ascending" : "descending");

        var rows = Array.from(tbody.querySelectorAll("tr"));
        rows.sort(function (a, b) {
          var aVal = (a.cells[colIndex] || {}).textContent || "";
          var bVal = (b.cells[colIndex] || {}).textContent || "";
          // Numeric detection
          var aNum = parseFloat(aVal.replace(/[¥,]/g, ""));
          var bNum = parseFloat(bVal.replace(/[¥,]/g, ""));
          if (!isNaN(aNum) && !isNaN(bNum)) {
            return ascending ? aNum - bNum : bNum - aNum;
          }
          return ascending ? aVal.localeCompare(bVal, "zh") : bVal.localeCompare(aVal, "zh");
        });
        rows.forEach(function (row) { tbody.appendChild(row); });
      });
    });
  }

  // ============================================================
  // 6d. Keyboard: / to focus search
  // ============================================================
  function initSearchShortcut() {
    document.addEventListener("keydown", function (e) {
      if (e.key === "/" && !e.ctrlKey && !e.metaKey) {
        var tag = document.activeElement ? document.activeElement.tagName : "";
        if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
        var searchInput = document.getElementById("search-plate") || document.querySelector("input[name='plate']");
        if (searchInput) { searchInput.focus(); e.preventDefault(); }
      }
    });
  }

  // ============================================================
  // 6e. Auto Color Scheme Detection
  // ============================================================
  function initPrefersColorScheme() {
    var mq = window.matchMedia("(prefers-color-scheme: dark)");
    function handleChange(e) {
      // Only auto-switch if user hasn't manually toggled
      var manual = localStorage.getItem("parking-theme-manual");
      if (manual) return;
      if (e.matches) {
        document.documentElement.setAttribute("data-theme", "dark");
      } else {
        document.documentElement.removeAttribute("data-theme");
      }
    }
    mq.addEventListener("change", handleChange);
    // Set initial if no manual preference stored
    if (!localStorage.getItem("parking-theme-manual")) {
      if (mql.matches) document.documentElement.setAttribute("data-theme", "dark");
    }
  }

  // ============================================================
  // 6. Hamburger Menu
  // ============================================================
  function initMenu() {
    var hamburger = document.querySelector(".hamburger");
    var nav = document.querySelector(".nav");
    if (!hamburger || !nav) return;

    hamburger.addEventListener("click", function () {
      var isOpen = nav.classList.toggle("open");
      hamburger.setAttribute("aria-expanded", String(isOpen));
    });

    // Close on outside click
    document.addEventListener("click", function (e) {
      if (!hamburger.contains(e.target) && !nav.contains(e.target)) {
        nav.classList.remove("open");
        hamburger.setAttribute("aria-expanded", "false");
      }
    });

    // Close on Escape
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && nav.classList.contains("open")) {
        nav.classList.remove("open");
        hamburger.setAttribute("aria-expanded", "false");
        hamburger.focus();
      }
    });
  }

  // ============================================================
  // 7. Active Nav Tracking
  // ============================================================
  function markActiveNav() {
    var path = window.location.pathname;
    var links = document.querySelectorAll(".nav-link");
    links.forEach(function (link) {
      link.classList.remove("active");
      link.removeAttribute("aria-current");
      if (link.getAttribute("href") === path) {
        link.classList.add("active");
        link.setAttribute("aria-current", "page");
      }
    });
  }

  // ============================================================
  // 8. Theme Toggle (Dark/Light)
  // ============================================================
  function initTheme() {
    var toggle = document.querySelector(".theme-toggle");
    if (!toggle) return;

    // Load saved theme
    var saved = localStorage.getItem("parking-theme");
    if (saved === "dark") {
      document.documentElement.setAttribute("data-theme", "dark");
      toggle.textContent = "☀️";
      toggle.setAttribute("aria-label", "切换到浅色模式");
    }

    toggle.addEventListener("click", function () {
      var isDark = document.documentElement.getAttribute("data-theme") === "dark";
      if (isDark) {
        document.documentElement.removeAttribute("data-theme");
        localStorage.setItem("parking-theme", "light"); localStorage.setItem("parking-theme-manual", "1");
        toggle.textContent = "🌙";
        toggle.setAttribute("aria-label", "切换到深色模式");
      } else {
        document.documentElement.setAttribute("data-theme", "dark");
        localStorage.setItem("parking-theme", "dark"); localStorage.setItem("parking-theme-manual", "1");
        toggle.textContent = "☀️";
        toggle.setAttribute("aria-label", "切换到浅色模式");
      }
    });
  }

  // ============================================================
  // 9. Keyboard Shortcuts
  // ============================================================
  function initKeyboard() {
    document.addEventListener("keydown", function (e) {
      // Don't intercept when typing in inputs
      var tag = document.activeElement ? document.activeElement.tagName : "";
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      switch (e.key) {
        case "g": case "G":
          if (e.ctrlKey || e.metaKey) { e.preventDefault(); } // browser shortcut
          break;
        case "d": case "D":
          // Alt+D → Dashboard
          if (e.altKey) { window.location.href = "/"; e.preventDefault(); }
          break;
        case "r": case "R":
          // Alt+R → Records
          if (e.altKey) { window.location.href = "/records"; e.preventDefault(); }
          break;
        case "v": case "V":
          // Alt+V → Vehicles
          if (e.altKey) { window.location.href = "/vehicles"; e.preventDefault(); }
          break;
        case "?":
          // ? → show shortcuts help
          if (!e.ctrlKey && !e.metaKey && !e.altKey) {
            showKeyboardHelp();
            e.preventDefault();
          }
          break;
      }
    });
  }

  function showKeyboardHelp() {
    showToast(
      "Alt+D: 面板 | Alt+R: 记录 | Alt+V: 车辆 | Esc: 关闭菜单 | ?: 帮助",
      "info", "⌨️ 键盘快捷键", 6000
    );
  }

  // ============================================================
  // 10. Init on DOM Ready
  // ============================================================
  function init() {
    initMenu();
    markActiveNav();
    initTheme();
    initKeyboard();
    initTableSort();
    initSearchShortcut();
    initPrefersColorScheme();
    initBottomNav();
    initPlateClickable();
    checkLoginStatus();
    updateReviewBadge();
  }

  // ---- Bottom Nav Active State ----
  function initBottomNav() {
    var path = window.location.pathname;
    document.querySelectorAll(".bottom-nav a").forEach(function (link) {
      if (link.getAttribute("href") === path) {
        link.classList.add("active");
        link.setAttribute("aria-current", "page");
      }
    });
  }

  // ---- Make plates click-to-copy ----
  function initPlateClickable() {
    document.querySelectorAll(".plate, .td-plate").forEach(function (el) {
      el.classList.add("plate-clickable");
      el.setAttribute("title", "点击复制车牌号");
      el.setAttribute("role", "button");
      el.setAttribute("tabindex", "0");
      el.addEventListener("click", function () { window.copyPlate(el); });
      el.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          window.copyPlate(el);
        }
      });
    });
  }

  function checkLoginStatus() {
    var statusEl = document.getElementById("login-status");
    if (!statusEl) return;
    fetch("/api/stats")
      .then(function () {
        statusEl.innerHTML =
          '<button class="btn-icon" onclick="window.showToast(\'已登录\',\'success\')" aria-label="已登录">👤</button>';
      })
      .catch(function () {
        statusEl.innerHTML =
          '<a href="/login" class="nav-link" style="margin:0;">🔐 登录</a>';
      });
  }

  function updateReviewBadge() {
    fetch("/api/stats")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var badge = document.getElementById("review-badge");
        if (badge && data.success && data.pending_review > 0) {
          badge.textContent = data.pending_review;
          badge.style.display = "inline-flex";
        }
      })
      .catch(function () {});
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
