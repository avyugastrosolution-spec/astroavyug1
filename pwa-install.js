(function () {
  'use strict';

  var deferredPrompt = null;
  var isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
  var isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);

  // Register/update the service worker even when the site is already running as an installed app.
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('/sw.js', { scope: '/' })
        .then(function (registration) {
          // Ask the browser to check for a newer service worker after each page load.
          registration.update().catch(function () {});
        })
        .catch(function () {});
    });
  }

  // Installed/standalone app does not need an Install button.
  if (isStandalone) return;

  var button = document.createElement('button');
  button.type = 'button';
  button.textContent = 'Install App';
  button.setAttribute('aria-label', 'Install Astro Avyug App');
  button.style.cssText = 'display:none;position:fixed;right:16px;bottom:16px;z-index:99999;border:0;border-radius:999px;padding:12px 18px;font:600 14px/1.2 system-ui,-apple-system,Segoe UI,sans-serif;background:#111;color:#fff;box-shadow:0 6px 24px rgba(0,0,0,.25);cursor:pointer;';

  function mountButton() {
    if (!document.body.contains(button)) document.body.appendChild(button);
  }

  document.addEventListener('DOMContentLoaded', function () {
    mountButton();
    // iOS does not support beforeinstallprompt; show manual A2HS help there.
    if (isIOS) button.style.display = 'block';
  });

  window.addEventListener('beforeinstallprompt', function (event) {
    event.preventDefault();
    deferredPrompt = event;
    mountButton();
    button.style.display = 'block';
  });

  button.addEventListener('click', async function () {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      try {
        var choice = await deferredPrompt.userChoice;
        // Hide after the browser has handled the prompt. It can reappear if Chrome fires a new event later.
        if (choice && (choice.outcome === 'accepted' || choice.outcome === 'dismissed')) {
          button.style.display = 'none';
        }
      } catch (_) {}
      deferredPrompt = null;
      return;
    }

    if (isIOS) {
      alert('Astro Avyug install karne ke liye Safari ke Share (↑) button par tap karke “Add to Home Screen” select karein.');
    }
  });

  window.addEventListener('appinstalled', function () {
    deferredPrompt = null;
    button.remove();
  });
})();
