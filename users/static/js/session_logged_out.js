document.addEventListener("DOMContentLoaded", function () {
  var seconds = 10;
  var countdownEl = document.getElementById("multiCountdown");
  var pluralEl = document.getElementById("multiPlural");

  // login URL is passed via data attribute
  var loginUrl = document.getElementById("multiLoginBtn").getAttribute("href");

  function updateCountdown() {
    countdownEl.textContent = seconds;
    pluralEl.textContent = seconds === 1 ? "" : "s";
  }
  updateCountdown();

  var timer = setInterval(function () {
    seconds -= 1;
    if (seconds <= 0) {
      clearInterval(timer);
      window.location.href = loginUrl;
    } else {
      updateCountdown();
    }
  }, 1000);

  document.getElementById("multiLoginBtn").addEventListener("click", function () {
    clearInterval(timer);
  });
});
