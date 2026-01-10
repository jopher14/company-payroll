(function () {
    const inactivityModalEl = document.getElementById("inactivityModal");
    const inactivityCountdownEl = document.getElementById("inactivityCountdown");
    const stayLoggedInBtn = document.getElementById("stayLoggedInBtn");
    const autoLogoutForm = document.getElementById("autoLogoutForm");

    if (!inactivityModalEl) return;

    let inactivityTimer;
    let inactivityCountdown = 60;
    let inactivityInterval;

    const inactivityModal = new bootstrap.Modal(inactivityModalEl);

    function resetInactivityTimer() {
        clearTimeout(inactivityTimer);
        clearInterval(inactivityInterval);

        inactivityCountdown = 60;
        inactivityCountdownEl.textContent = inactivityCountdown;

        inactivityTimer = setTimeout(showInactivityWarning, 5 * 60 * 1000);
    }

    function showInactivityWarning() {
        inactivityModal.show();

        inactivityInterval = setInterval(() => {
            inactivityCountdown--;
            inactivityCountdownEl.textContent = inactivityCountdown;

            if (inactivityCountdown <= 0) {
                clearInterval(inactivityInterval);
                autoLogoutForm.submit();
            }
        }, 1000);
    }

    stayLoggedInBtn.addEventListener("click", () => {
        inactivityModal.hide();
        resetInactivityTimer();
    });

    ["click", "keydown", "mousemove"].forEach(evt =>
        document.addEventListener(evt, resetInactivityTimer)
    );

    resetInactivityTimer();
})();
