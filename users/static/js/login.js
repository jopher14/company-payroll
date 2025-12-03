document.addEventListener("DOMContentLoaded", () => {
    const passwordField = document.getElementById("password");
    const icon = document.getElementById("togglePasswordIcon");
    const toggleButton = document.querySelector(".toggle-password");

    toggleButton.addEventListener("click", () => {
        if (passwordField.type === "password") {
            passwordField.type = "text";
            icon.classList.replace("bi-eye", "bi-eye-slash");
        } else {
            passwordField.type = "password";
            icon.classList.replace("bi-eye-slash", "bi-eye");
        }
    });
});
