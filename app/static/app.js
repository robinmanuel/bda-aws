// =============================================================================
// Personal Diary — Client Photo Preview & Form Helpers
// =============================================================================

// Polaroid Photo Preview
function previewMemory(input) {
  const file = input.files[0];
  const placeholder = document.getElementById("photoPlaceholder");
  const preview = document.getElementById("polaroidPreview");
  const img = document.getElementById("imagePreview");

  if (file) {
    const reader = new FileReader();
    reader.onload = function(e) {
      img.src = e.target.result;
      preview.style.display = "inline-block";
      placeholder.style.display = "none";
    };
    reader.readAsDataURL(file);
  }
}

function removeMemoryPhoto() {
  const input = document.getElementById("image");
  const placeholder = document.getElementById("photoPlaceholder");
  const preview = document.getElementById("polaroidPreview");
  const img = document.getElementById("imagePreview");

  input.value = "";
  img.src = "";
  preview.style.display = "none";
  placeholder.style.display = "flex";
}
