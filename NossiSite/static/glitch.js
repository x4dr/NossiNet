function randomize_glitches() {
    document.querySelectorAll('.glitch').forEach(el => {
        el.style.setProperty('--glitch-duration-1', `${(12 + Math.random() * 5).toFixed(2)}s`);
        el.style.setProperty('--glitch-duration-2', `${(5 + Math.random() * 5).toFixed(2)}s`);
        el.style.setProperty('--glitch-delay', `${(Math.random() * 10).toFixed(2)}s`);
    });
}


document.addEventListener("DOMContentLoaded", randomize_glitches);
document.addEventListener("htmx:afterSwap", randomize_glitches);
