document.addEventListener("DOMContentLoaded", function () {
  const photoInput = document.querySelector("input[name='photo']");
  const preview = document.getElementById("photo-preview");

  if (photoInput) {
    photoInput.addEventListener("change", function () {
      const file = this.files[0];
      preview.src = file ? URL.createObjectURL(file) : preview.dataset.default;
    });
  }
});
