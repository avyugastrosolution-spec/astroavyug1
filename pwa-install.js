(function () {
  'use strict';
  var deferredPrompt = null;
  var isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
  if (isStandalone) return;

  var button = document.createElement('button');
  button.type = 'button';
  button.textContent = 'Install App';
  button.setAttribute('aria-label', 'Install Astro Avyug App');
  button.style.cssText = 'display:block;position:fixed;right:16px;bottom:16px;z-index:99999;border:0;border-radius:999px;padding:12px 18px;font:600 14px/1.2 system-ui,-apple-system,Segoe UI,sans-serif;background:#111;color:#fff;box-shadow:0 6px 24px rgba(0,0,0,.25);cursor:pointer;';

  document.addEventListener('DOMContentLoaded', function () {
    document.body.appendChild(button);
  });

  window.addEventListener('beforeinstallprompt', function (event) {
    event.preventDefault();
    deferredPrompt = event;
  });

  button.addEventListener('click', async function () {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      try { await deferredPrompt.userChoice; } catch (_) {}
      deferredPrompt = null;
      return;
    }

    var isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
    if (isIOS) {
      alert('Astro Avyug install karne ke liye Safari ke Share (↑) button par tap karke “Add to Home Screen” select karein.');
    } else {
      alert('Agar Install prompt abhi nahi aa raha hai, browser ke menu (⋮) me “Install app” ya “Add to Home screen” select karein.');
    }
  });

  window.addEventListener('appinstalled', function () {
    deferredPrompt = null;
    button.remove();
  });

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(function () {});
    });
  }
})();
