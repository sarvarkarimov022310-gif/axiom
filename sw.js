// Axiom AI: internetsiz ishlash uchun xizmat oqimi (service worker).
// Ilova fayllari va Pyodide (Python) fayllari birinchi yuklashdan keyin qurilmada saqlanadi.
const KESH = "axiom-v1";
const ASOSIY = ["./", "./index.html", "./worker.js", "./axiom_core.py", "./manifest.webmanifest",
                "./icon-192.png", "./icon-512.png", "./apple-touch-icon.png", "./favicon.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(KESH).then((c) => c.addAll(ASOSIY)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((kalitlar) => Promise.all(kalitlar.filter((k) => k !== KESH && k.startsWith("axiom-")).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function saqla(r, resp) {
  if (resp && (resp.ok || resp.type === "opaque")) {
    const nusxa = resp.clone();
    caches.open(KESH).then((c) => c.put(r, nusxa)).catch(() => {});
  }
}

// Ilovaning o'z fayllari: avval tarmoq (yangilanish bo'lsa olinadi), 4 soniyada javob bo'lmasa yoki internet yo'q bo'lsa keshdan
function tarmoqdanKeyinKesh(r) {
  return new Promise((resolve) => {
    let tugadi = false;
    const keshdan = () => caches.match(r, { ignoreSearch: true }).then((m) => m || (r.mode === "navigate" ? caches.match("./index.html") : null));
    const taymer = setTimeout(() => {
      keshdan().then((m) => { if (m && !tugadi) { tugadi = true; resolve(m); } });
    }, 4000);
    fetch(r).then((resp) => {
      clearTimeout(taymer);
      if (!tugadi) { tugadi = true; saqla(r, resp); resolve(resp); }
    }).catch(() => {
      clearTimeout(taymer);
      keshdan().then((m) => { if (!tugadi) { tugadi = true; resolve(m || new Response("Oflayn", { status: 503 })); } });
    });
  });
}

// Pyodide fayllari (katta, o'zgarmaydi): avval keshdan
function keshdanKeyinTarmoq(r) {
  return caches.match(r).then((m) => m || fetch(r).then((resp) => { saqla(r, resp); return resp; }));
}

self.addEventListener("fetch", (e) => {
  const r = e.request;
  if (r.method !== "GET") return;
  const u = new URL(r.url);
  if (u.origin === self.location.origin) e.respondWith(tarmoqdanKeyinKesh(r));
  else if (u.hostname === "cdn.jsdelivr.net") e.respondWith(keshdanKeyinTarmoq(r));
});
