// Service worker de Sugu (ticket #14), servi par apps/core/views.py à la racine du site pour
// couvrir toutes les pages. Généré : VERSION change quand un fichier précaché change.
"use strict";

const VERSION = "{{ version }}";
const CACHE = `sugu-${VERSION}`;
const OFFLINE_URL = "{{ offline_url }}";
const PRECACHE = {{ precache_json|safe }};
// En développement, les fichiers statiques viennent toujours du réseau (CSS modifié tout de suite).
const STATIC_FROM_CACHE = {{ static_from_cache|yesno:"true,false" }};

// La page hors-ligne est indispensable ; un fichier de charte manquant ne doit pas empêcher
// l'installation (cache.addAll échouerait en entier).
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) =>
        Promise.all(
          PRECACHE.map((url) => (url === OFFLINE_URL ? cache.add(url) : cache.add(url).catch(() => {}))),
        ),
      )
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((key) => key.startsWith("sugu-") && key !== CACHE).map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Pages : toujours le réseau, jamais de cache (données personnelles). Sans réseau : la page
  // hors-ligne, servie à l'adresse demandée.
  if (request.mode === "navigate") {
    event.respondWith(fetch(request).catch(() => caches.match(OFFLINE_URL)));
    return;
  }

  // Charte précachée (noms hachés en production) : depuis le cache, sans attendre le réseau.
  if (STATIC_FROM_CACHE && PRECACHE.includes(url.pathname)) {
    event.respondWith(caches.match(request).then((cached) => cached || fetch(request)));
  }
  // Le reste (photos, requêtes htmx) : comme sans service worker.
});
