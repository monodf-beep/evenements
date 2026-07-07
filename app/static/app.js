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
