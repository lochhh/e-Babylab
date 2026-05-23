export function setResolution() {
    const wInput = document.querySelector("input[name='resolution_w']");
    const hInput = document.querySelector("input[name='resolution_h']");
    if (wInput) wInput.value = window.screen.width;
    if (hInput) hInput.value = window.screen.height;
}

setResolution();
