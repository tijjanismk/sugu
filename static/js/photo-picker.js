/* Sélecteur de photos du dépôt d'annonce (design/components/PhotoPicker, ticket #7).
 *
 * Amélioration progressive : sans ce script, le champ fichier classique envoie les photos telles
 * quelles. Avec lui : aperçus, retrait, badge « Couverture » sur la première, six photos au plus,
 * et réduction dans le navigateur (≈ 1 600 px, JPEG) avant l'envoi, pour un envoi environ dix fois
 * plus léger en 3G. Le serveur revérifie et réencode tout : ce script n'est jamais une sécurité.
 */
(function () {
  "use strict";

  var MAX_PHOTOS = 6; // peut être réduit par data-max-photos (photos déjà en ligne)
  var MAX_SIDE = 1600;
  var JPEG_QUALITY = 0.85;

  var form = document.querySelector("[data-listing-form]");
  if (!form || !window.DataTransfer || !window.createImageBitmap) return;
  if (form.dataset.maxPhotos) MAX_PHOTOS = parseInt(form.dataset.maxPhotos, 10) || MAX_PHOTOS;

  var input = form.querySelector("[data-photo-input]");
  var grid = form.querySelector("[data-photo-grid]");
  var addButton = form.querySelector("[data-photo-add]");
  var tileTemplate = form.querySelector("[data-photo-tile]");
  var status = form.querySelector("[data-photo-status]");
  var submit = form.querySelector("[data-submit]");
  if (!input || !grid || !addButton || !tileTemplate) return;

  var files = [];
  var previews = [];
  var preparing = 0;

  grid.classList.remove("hidden");
  input.classList.add("sr-only");
  input.tabIndex = -1;

  function setStatus(text) {
    status.textContent = text;
    status.classList.toggle("hidden", !text);
  }

  function syncInput() {
    var transfer = new DataTransfer();
    files.forEach(function (file) { transfer.items.add(file); });
    input.files = transfer.files;
  }

  function render() {
    previews.forEach(URL.revokeObjectURL);
    previews = [];
    grid.querySelectorAll(".sg-photo").forEach(function (tile) { tile.remove(); });
    files.forEach(function (file, index) {
      var tile = tileTemplate.content.firstElementChild.cloneNode(true);
      var url = URL.createObjectURL(file);
      previews.push(url);
      tile.querySelector("img").src = url;
      if (index === 0) {
        var cover = document.createElement("span");
        cover.className = "sg-photo__cover";
        cover.textContent = "Couverture";
        tile.appendChild(cover);
      }
      tile.querySelector("button").addEventListener("click", function () {
        files.splice(index, 1);
        render();
        syncInput();
      });
      grid.insertBefore(tile, addButton);
    });
    addButton.hidden = files.length >= MAX_PHOTOS;
  }

  function shrink(file) {
    if (!/^image\//.test(file.type)) return Promise.resolve(file);
    return createImageBitmap(file, { imageOrientation: "from-image" }).then(function (bitmap) {
      var scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
      var canvas = document.createElement("canvas");
      canvas.width = Math.round(bitmap.width * scale);
      canvas.height = Math.round(bitmap.height * scale);
      canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
      if (bitmap.close) bitmap.close();
      return new Promise(function (resolve) {
        canvas.toBlob(function (blob) {
          // Garde l'original si la réduction n'allège rien (petite photo déjà compressée).
          if (!blob || blob.size >= file.size) return resolve(file);
          var name = file.name.replace(/\.[^.]+$/, "") + ".jpg";
          resolve(new File([blob], name, { type: "image/jpeg", lastModified: Date.now() }));
        }, "image/jpeg", JPEG_QUALITY);
      });
    }).catch(function () {
      return file; // format inconnu du navigateur : le serveur tranchera
    });
  }

  addButton.addEventListener("click", function () { input.click(); });

  input.addEventListener("change", function () {
    var chosen = Array.prototype.slice.call(input.files, 0, MAX_PHOTOS - files.length);
    if (!chosen.length) { syncInput(); return; }
    preparing += chosen.length;
    setStatus("Préparation des photos…");
    Promise.all(chosen.map(shrink)).then(function (ready) {
      files = files.concat(ready).slice(0, MAX_PHOTOS);
      preparing -= chosen.length;
      if (!preparing) setStatus("");
      render();
      syncInput();
    });
  });

  form.addEventListener("submit", function (event) {
    if (preparing) {
      event.preventDefault();
      setStatus("Patientez : les photos sont en cours de préparation.");
      return;
    }
    if (submit) {
      submit.setAttribute("aria-disabled", "true");
      submit.innerHTML = '<span class="sg-spinner" aria-hidden="true"></span>Publication…';
    }
  });
})();
