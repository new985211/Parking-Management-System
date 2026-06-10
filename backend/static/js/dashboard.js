/**
 * Dashboard real-time refresh and common utilities.
 */

// Auto-refresh every 30 seconds on dashboard pages
(function () {
  // Check login status
  checkLoginStatus();

  // Count pending reviews for badge
  updateReviewBadge();

  // Only auto-refresh on dashboard
  if (window.location.pathname === "/") {
    setInterval(function () {
      fetch("/api/stats")
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.success) {
            // Update stat numbers without full page reload
            // For simplicity, reload the page
            location.reload();
          }
        })
        .catch(function () {});
    }, 30000);
  }
})();

function checkLoginStatus() {
  var el = document.getElementById("login-status");
  if (!el) return;
  fetch("/api/stats")
    .then(function () { el.textContent = ""; })
    .catch(function () {
      el.innerHTML = '<a href="/login" style="color:#fff;font-size:13px;">登录</a>';
    });
}

function updateReviewBadge() {
  fetch("/api/stats")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.success && data.pending_review > 0) {
        var badge = document.getElementById("review-badge");
        if (badge) {
          badge.textContent = data.pending_review;
          badge.style.display = "inline";
        }
      }
    })
    .catch(function () {});
}
