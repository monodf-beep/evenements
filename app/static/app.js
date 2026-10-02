/* Agenda Sabauda — enrichissements progressifs (le back-office marche SANS JS ;
   ces deux ajouts fluidifient seulement).
   1) Triage sans rechargement : les mini-formulaires .stpick partent en fetch,
      la ligne se met à jour sur place — le tri « à la chaîne » devient continu.
   2) Fin de tâche : quand une tâche du pipeline tourne, on interroge /api/status
      et on ne recharge la page QU'UNE fois, quand tout est fini (remplace le
      meta-refresh de 5 s qui cassait focus et saisie). */
(function () {
  "use strict";

  /* ---- 1. Triage AJAX des pastilles de statut ---- */
  document.addEventListener("submit", function (ev) {
    var form = ev.target;
    if (!form.matches(".stpick form")) return;
    ev.preventDefault();
    var pick = form.closest(".stpick");
    var btn = form.querySelector("button.st");
    if (!pick || !btn) { form.submit(); return; }
    pick.style.opacity = ".45";
    fetch(form.action, {
      method: "POST",
      headers: { "X-Requested-With": "fetch" },
      body: new FormData(form),
      redirect: "manual",           /* on ne suit pas le redirect : maj locale */
    }).then(function (r) {
      if (r.type !== "opaqueredirect" && !r.ok) throw new Error(r.status);
      /* Bascule visuelle : l'ancienne pastille active devient cliquable,
         celle cliquée devient active. Les classes st-<statut> existent déjà. */
      var newStatus = form.action.split("/").pop();
      pick.querySelectorAll(".st").forEach(function (el) {
        var f = el.closest("form");
        var status = f ? f.action.split("/").pop() : null;
        if (el.tagName === "SPAN") {
          /* ancienne active → redevient bouton (au prochain rendu serveur) ;
             ici on la grise simplement */
          el.className = "st st-off";
        }
        if (status === newStatus) el.className = "st st-" + newStatus;
      });
      pick.style.opacity = "1";
    }).catch(function () {
      /* réseau KO → comportement no-JS normal */
      pick.style.opacity = "1";
      form.submit();
    });
  });

  /* ---- 1bis. Tiroir de navigation mobile (hamburger) ---- */
  var toggle = document.querySelector(".nav-toggle");
  if (toggle) {
    var openNav = function (open) {
      document.body.classList.toggle("nav-open", open);
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    };
    toggle.addEventListener("click", function () {
      openNav(!document.body.classList.contains("nav-open"));
    });
    /* Ferme : clic sur le voile, sur un lien du menu, ou touche Échap. */
    document.addEventListener("click", function (ev) {
      if (ev.target.closest("[data-nav-close]")) openNav(false);
      else if (ev.target.closest(".sidebar .nav a")) openNav(false);
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") openNav(false);
    });
  }

  /* ---- 2. Polling de fin de tâche (dashboard) ---- */
  var flag = document.querySelector("[data-any-running='1']");
  if (flag) {
    var timer = setInterval(function () {
      fetch("/api/status", { headers: { "X-Requested-With": "fetch" } })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d.running) { clearInterval(timer); location.reload(); }
        })
        .catch(function () { /* silencieux : on retentera au tick suivant */ });
    }, 5000);
  }
})();

/* ── SECTIONS REPLIABLES, AVEC MÉMOIRE ──────────────────────────────────────────────
   Franck, 2026-08-11 : « il faut refaire un peu ce back-office qui soit un peu pliable,
   parce qu'il y a trop aussi en hauteur d'écran. Il y a trois scrolls, il y a trop de
   choses. »

   Le problème n'est pas la quantité d'information — chaque bloc a sa raison d'être — c'est
   qu'ils sont tous DÉPLIÉS en même temps. Et un repli sans mémoire est pire que pas de
   repli : on referme, on change de page, tout se rouvre, et on renonce.

   Donc : tout <details data-pli="…"> retient son état, par identifiant, dans le
   navigateur. Ce qu'on a fermé reste fermé demain matin.

   Ce qui NE se replie jamais, et c'est délibéré : les alertes et la prochaine action. Un
   avertissement qu'on peut ranger d'un clic finit toujours rangé. */
(function () {
  var CLE = 'pli:';
  document.querySelectorAll('details[data-pli]').forEach(function (d) {
    var k = CLE + d.getAttribute('data-pli');
    var v = null;
    try { v = localStorage.getItem(k); } catch (e) { return; }
    if (v === '1') { d.open = true; } else if (v === '0') { d.open = false; }
    d.addEventListener('toggle', function () {
      try { localStorage.setItem(k, d.open ? '1' : '0'); } catch (e) {}
    });
  });

  /* ---- 3. Palette « Aller à… » (⌘K / Ctrl+K / « / ») --------------------------
     Franck, 2026-09-22 : « rends le back-office le plus simple possible ». Avec
     vingt-huit pages, la simplification qui compte n'est pas de raccourcir le menu
     mais de rendre sa longueur INDIFFÉRENTE : on tape trois lettres, on entre.

     Enrichissement pur : sans JS le menu marche comme avant, et le bouton qui ouvre
     la palette reste masqué (.js posé ici le révèle) plutôt que de promettre une
     fonction absente. La liste est rendue par le serveur depuis la MÊME carte que le
     menu (utils/menu.py) — rien n'est dupliqué, donc rien ne peut diverger. */
  document.documentElement.classList.add("js");

  var pal = document.getElementById("palette");
  if (pal) {
    var champ = document.getElementById("palette-q");
    var liste = document.getElementById("palette-liste");
    var vide = pal.querySelector(".palette-vide");
    var items = Array.prototype.slice.call(liste.querySelectorAll("li"));
    var visibles = items.slice();
    var sel = 0;
    var rendeur = null;

    var marquer = function () {
      items.forEach(function (li) {
        li.classList.remove("sel");
        li.setAttribute("aria-selected", "false");
      });
      var li = visibles[sel];
      if (!li) return;
      li.classList.add("sel");
      li.setAttribute("aria-selected", "true");
      li.scrollIntoView({ block: "nearest" });
    };

    var filtrer = function () {
      /* Sans accents et en minuscules des DEUX côtés : « completude » doit trouver
         « Complétude ». La cible est déjà aplatie côté serveur. */
      var q = champ.value.normalize("NFD").replace(/[\u0300-\u036f]/g, "")
                .toLowerCase().trim();
      var mots = q ? q.split(/\s+/) : [];
      visibles = [];
      items.forEach(function (li) {
        var cible = li.getAttribute("data-cible") || "";
        var ok = mots.every(function (m) { return cible.indexOf(m) !== -1; });
        li.hidden = !ok;
        if (ok) visibles.push(li);
      });
      vide.hidden = visibles.length > 0;
      sel = 0;
      marquer();
    };

    var ouvrir = function () {
      if (!pal.hidden) return;
      rendeur = document.activeElement;
      pal.hidden = false;
      champ.value = "";
      filtrer();
      champ.focus();
    };
    var fermer = function () {
      if (pal.hidden) return;
      pal.hidden = true;
      if (rendeur && rendeur.focus) rendeur.focus();
    };

    document.addEventListener("click", function (ev) {
      if (ev.target.closest("[data-palette-open]")) { ev.preventDefault(); ouvrir(); }
      else if (ev.target.closest("[data-palette-close]")) fermer();
    });

    document.addEventListener("keydown", function (ev) {
      var dansSaisie = /^(INPUT|TEXTAREA|SELECT)$/.test(
        (ev.target.tagName || "")) || ev.target.isContentEditable;
      if ((ev.key === "k" || ev.key === "K") && (ev.metaKey || ev.ctrlKey)) {
        ev.preventDefault(); pal.hidden ? ouvrir() : fermer(); return;
      }
      /* « / » n'ouvre que si on n'est pas déjà en train de taper quelque part —
         sinon on vole la barre oblique à la saisie d'une URL ou d'un tarif. */
      if (ev.key === "/" && pal.hidden && !dansSaisie && !ev.metaKey && !ev.ctrlKey) {
        ev.preventDefault(); ouvrir(); return;
      }
      if (pal.hidden) return;
      if (ev.key === "Escape") { ev.preventDefault(); fermer(); return; }
      if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
        ev.preventDefault();
        if (!visibles.length) return;
        sel = (sel + (ev.key === "ArrowDown" ? 1 : -1) + visibles.length) % visibles.length;
        marquer(); return;
      }
      if (ev.key === "Enter" && visibles[sel]) {
        ev.preventDefault();
        var a = visibles[sel].querySelector("a");
        if (a) window.location.href = a.getAttribute("href");
      }
    });

    champ.addEventListener("input", filtrer);
  }
})();
