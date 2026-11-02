document.addEventListener("DOMContentLoaded", function () {
  var alvo = document.querySelector(".page-body");
  if (!alvo || typeof renderMathInElement !== "function") {
    return;
  }
  renderMathInElement(alvo, {
    delimiters: [
      { left: "$$", right: "$$", display: true },
      { left: "\\(", right: "\\)", display: false },
    ],
    throwOnError: false,
  });
});
