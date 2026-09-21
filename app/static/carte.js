/* ═══ LA CARTE DES AUTOMATISATIONS — dessin, navigation, panneau ═══════════════
   Trois choses seulement :
     1. tracer les liens entre les nœuds (le gabarit pose les nœuds, pas les courbes) ;
     2. déplacer et zoomer la scène ;
     3. ouvrir la fiche d'un nœud dans le panneau de droite.

   POURQUOI LES NŒUDS SONT DU HTML ET PAS DU SVG. Un <button> HTML est focusable au
   clavier, lisible par un lecteur d'écran et sait retourner à la ligne tout seul ; un
   <text> SVG ne fait aucun des trois. Les courbes, elles, restent en SVG — sous les
   nœuds, sans capter le clic. La page fonctionne donc sans ce fichier : les nœuds sont
   empilés et tous cliquables (classe `sans-js`, retirée ci-dessous).            */
(function () {
  "use strict";
  const racine = document.getElementById("carte");
  if (!racine) return;
  racine.classList.remove("sans-js");

  const NOEUDS = JSON.parse(document.getElementById("carte-donnees").textContent);
  const LIENS = JSON.parse(document.getElementById("carte-liens").textContent);
  const parId = Object.fromEntries(NOEUDS.map((n) => [n.id, n]));

  /* ─────────────────────────────────────────────────────── les courbes ── */
  /* TROIS ACHEMINEMENTS, et le choix dépend de la POSITION RELATIVE des deux nœuds.
     La première version n'en avait qu'un — sortie à droite, entrée à gauche — et elle
     traçait un trait vertical À TRAVERS les nœuds dès que deux étapes se suivaient dans
     la même colonne, ce qui est le cas de toute la chaîne du matin. Un lien qu'on ne
     peut pas suivre des yeux ne documente rien.
       · en dessous  → sortie par le BAS, entrée par le HAUT ;
       · à droite    → sortie à droite, entrée à gauche (le cas n8n classique) ;
       · en arrière  → boucle par le dessous, en contournant.                        */
  function geometrie(a, b) {
    const aL = a.offsetLeft, aT = a.offsetTop, aW = a.offsetWidth, aH = a.offsetHeight;
    const bL = b.offsetLeft, bT = b.offsetTop, bW = b.offsetWidth, bH = b.offsetHeight;
    const acx = aL + aW / 2, bcx = bL + bW / 2;
    const acy = aT + aH / 2, bcy = bT + bH / 2;
    // « L'un sous l'autre » : leurs emprises horizontales se chevauchent nettement.
    const chevauche = Math.abs(acx - bcx) < (aW + bW) / 2 - 24;

    if (chevauche && bT > aT) {
      const sy = aT + aH, ey = bT, d = Math.max(22, (ey - sy) / 2);
      return { d: `M${acx},${sy} C${acx},${sy + d} ${bcx},${ey - d} ${bcx},${ey}`,
               lx: (acx + bcx) / 2 + 8, ly: (sy + ey) / 2 };
    }
    if (chevauche) {
      // Retour vers le haut dans la même colonne : on contourne par la droite.
      const x = Math.max(aL + aW, bL + bW) + 40;
      return { d: `M${aL + aW},${acy} C${x},${acy} ${x},${bcy} ${bL + bW},${bcy}`,
               lx: x + 4, ly: (acy + bcy) / 2 };
    }
    if (bL >= aL + aW - 8) {
      const ax = aL + aW, bx = bL, d = Math.max(34, (bx - ax) / 2);
      return { d: `M${ax},${acy} C${ax + d},${acy} ${bx - d},${bcy} ${bx},${bcy}`,
               lx: (ax + bx) / 2, ly: (acy + bcy) / 2 - 8 };
    }
    // En arrière : par le dessous des deux, pour ne passer sous aucun nœud.
    const sy = aT + aH, ey = bT + bH, creux = Math.max(sy, ey) + 48;
    return { d: `M${acx},${sy} C${acx},${creux} ${bcx},${creux} ${bcx},${ey}`,
             lx: (acx + bcx) / 2, ly: creux - 6 };
  }

  function tracer(scene) {
    const svg = scene.querySelector("svg");
    if (!svg) return;
    svg.innerHTML =
      '<defs><marker id="fl" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7"' +
      ' markerHeight="7" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="currentColor"/>' +
      "</marker></defs>";
    const ns = "http://www.w3.org/2000/svg";
    LIENS.forEach((l) => {
      const a = scene.querySelector('[data-id="' + l.de + '"]');
      const b = scene.querySelector('[data-id="' + l.vers + '"]');
      if (!a || !b) return;
      const g = geometrie(a, b);
      const p = document.createElementNS(ns, "path");
      p.setAttribute("d", g.d);
      p.setAttribute("class", "lien lien--" + (l.type || "flux"));
      p.setAttribute("marker-end", "url(#fl)");
      p.dataset.de = l.de;
      p.dataset.vers = l.vers;
      svg.appendChild(p);
      if (l.label) {
        const t = document.createElementNS(ns, "text");
        t.setAttribute("x", g.lx); t.setAttribute("y", g.ly);
        t.setAttribute("text-anchor", "middle");
        t.setAttribute("class", "lien-txt");
        t.textContent = l.label;
        svg.appendChild(t);
      }
    });
  }

  /* ──────────────────────────────────────────────── déplacer et zoomer ── */
  const vues = new Map(); // hôte → {x, y, k}

  function appliquer(hote) {
    const v = vues.get(hote);
    const scene = hote.querySelector(".scene");
    scene.style.transform = `translate(${v.x}px, ${v.y}px) scale(${v.k})`;
    const etiquette = hote.querySelector(".scene-zoom");
    if (etiquette) etiquette.textContent = Math.round(v.k * 100) + " %";
  }

  function ajuster(hote) {
    const L = parseFloat(hote.dataset.largeur) || 900;
    const H = parseFloat(hote.dataset.hauteur) || 500;
    const k = Math.min(1, (hote.clientWidth - 24) / L, (hote.clientHeight - 24) / H);
    vues.set(hote, { x: 12, y: 12, k: Math.max(0.62, k) });
    appliquer(hote);
  }

  function brancherScene(hote) {
    vues.set(hote, { x: 12, y: 12, k: 1 });
    tracer(hote.querySelector(".scene"));
    ajuster(hote);

    let attrape = null;
    hote.addEventListener("pointerdown", (e) => {
      if (e.target.closest(".nd") || e.target.closest(".scene-outils")) return;
      const v = vues.get(hote);
      attrape = { px: e.clientX, py: e.clientY, x: v.x, y: v.y };
      hote.classList.add("attrape");
      hote.setPointerCapture(e.pointerId);
    });
    hote.addEventListener("pointermove", (e) => {
      if (!attrape) return;
      const v = vues.get(hote);
      v.x = attrape.x + (e.clientX - attrape.px);
      v.y = attrape.y + (e.clientY - attrape.py);
      appliquer(hote);
    });
    const lacher = () => { attrape = null; hote.classList.remove("attrape"); };
    hote.addEventListener("pointerup", lacher);
    hote.addEventListener("pointercancel", lacher);

    hote.addEventListener("wheel", (e) => {
      e.preventDefault();
      const v = vues.get(hote);
      const r = hote.getBoundingClientRect();
      const cx = e.clientX - r.left, cy = e.clientY - r.top;
      const k2 = Math.min(1.8, Math.max(0.3, v.k * (e.deltaY < 0 ? 1.12 : 1 / 1.12)));
      // Zoomer AUTOUR DU CURSEUR : sans cette correction, la scène fuit sous la souris
      // et on perd le nœud qu'on visait.
      v.x = cx - ((cx - v.x) / v.k) * k2;
      v.y = cy - ((cy - v.y) / v.k) * k2;
      v.k = k2;
      appliquer(hote);
    }, { passive: false });

    hote.querySelectorAll("[data-zoom]").forEach((b) => {
      b.addEventListener("click", () => {
        const sens = parseInt(b.dataset.zoom, 10);
        if (sens === 0) return ajuster(hote);
        const v = vues.get(hote);
        v.k = Math.min(1.8, Math.max(0.3, v.k * (sens > 0 ? 1.15 : 1 / 1.15)));
        appliquer(hote);
      });
    });

    // Au clavier, la tabulation passe de nœud en nœud : on ramène dans le cadre celui
    // qui prend le focus, sinon on navigue à l'aveugle hors de l'écran.
    hote.querySelectorAll(".nd").forEach((n) => {
      n.addEventListener("focus", () => {
        const v = vues.get(hote);
        const gx = n.offsetLeft * v.k + v.x, gy = n.offsetTop * v.k + v.y;
        if (gx < 0 || gy < 0 || gx + n.offsetWidth * v.k > hote.clientWidth ||
            gy + n.offsetHeight * v.k > hote.clientHeight) {
          v.x = hote.clientWidth / 2 - (n.offsetLeft + n.offsetWidth / 2) * v.k;
          v.y = hote.clientHeight / 2 - (n.offsetTop + n.offsetHeight / 2) * v.k;
          appliquer(hote);
        }
      });
    });
  }

  /* ─────────────────────────────────────────────────────── les onglets ── */
  const tabs = [...racine.querySelectorAll('[role="tab"]')];
  const panneaux = [...racine.querySelectorAll('[role="tabpanel"]')];
  const branchees = new WeakSet();

  function montrer(id) {
    tabs.forEach((t) => t.setAttribute("aria-selected", String(t.dataset.flux === id)));
    panneaux.forEach((p) => { p.hidden = p.dataset.flux !== id && p.id !== "flux-" + id; });
    const actif = document.getElementById("flux-" + id);
    if (!actif) return;
    actif.querySelectorAll(".scene-hote").forEach((h) => {
      // Une scène cachée a toutes ses tailles à zéro : on ne peut ni tracer ni ajuster
      // avant qu'elle soit visible. D'où ce branchement à la PREMIÈRE ouverture.
      if (!branchees.has(h)) { branchees.add(h); brancherScene(h); } else { ajuster(h); }
    });
    try { history.replaceState(null, "", "#" + id); } catch (_) {}
  }
  tabs.forEach((t) => t.addEventListener("click", () => montrer(t.dataset.flux)));
  tabs.forEach((t, i) => t.addEventListener("keydown", (e) => {
    const d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (!d) return;
    e.preventDefault();
    const c = tabs[(i + d + tabs.length) % tabs.length];
    c.focus(); montrer(c.dataset.flux);
  }));

  /* ───────────────────────────────────────────────────────── le panneau ── */
  const panneau = document.getElementById("panneau");
  const voile = racine.querySelector(".panneau-voile");
  const corps = document.getElementById("pan-corps");
  let ouvreur = null;

  /* Échappement d'abord, mise en forme ensuite — jamais l'inverse. Les fiches écrivent
     les noms de fichiers et de colonnes entre accents graves, comme dans le reste du
     dépôt ; sans cette conversion ils s'affichaient tels quels, accents compris. */
  const ech = (s) => String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

  function sec(titre, contenu) {
    return contenu ? `<div class="pan-sec"><h3>${titre}</h3>${contenu}</div>` : "";
  }
  function liste(items) {
    if (!items || !items.length) return "";
    return "<ul>" + items.map((i) => `<li>${ech(i)}</li>`).join("") + "</ul>";
  }

  const NATURE = {
    declencheur: "Déclencheur", action: "Traitement", decision: "Décision",
    agent: "Modèle IA", sortie: "Sortie", humain: "Geste humain",
    etat: "État terminal", site: "Côté site",
  };
  const ETAT_MOT = {
    ok: "a tourné", retard: "en retard", erreur: "erreurs au dernier passage",
    inconnu: "état inconnu",
  };

  function remplir(n) {
    const d = n.detail || {};
    document.getElementById("pan-ico").textContent = n.icone || "•";
    document.getElementById("pan-titre").textContent = n.label;

    const puces = [`<span class="pastille">${NATURE[n.kind] || n.kind}</span>`];
    if (n.surveille || n.etat.niveau !== "inconnu") {
      puces.push(`<span class="pastille pastille--${n.etat.niveau}">${
        ETAT_MOT[n.etat.niveau]}${n.etat.age ? " · " + ech(n.etat.age) : ""}</span>`);
    }
    if (n.kind !== "agent" && d.cout_ia && d.cout_ia !== "aucun") {
      puces.push('<span class="pastille pastille--ia">coûte des appels IA</span>');
    }
    if (n.angle_mort) {
      puces.push('<span class="pastille pastille--retard">non surveillé</span>');
    }
    if (d.irreversible) puces.push('<span class="pastille pastille--danger">irréversible</span>');
    document.getElementById("pan-puces").innerHTML = puces.join("");

    const h = [];
    if (n.resume) h.push(`<p class="pan-resume">${ech(n.resume)}</p>`);
    if (n.horaire) h.push(sec("Quand", `<p>${ech(n.horaire)}${
      n.cron ? ` <code>${ech(n.cron)}</code>` : ""}</p>`));
    h.push(sec("Ce qu'il fait", liste(d.fait)));

    const aLit = d.lit && d.lit.length, aEcrit = d.ecrit && d.ecrit.length;
    if (aLit && aEcrit) {
      h.push(sec("Ce qu'il lit et ce qu'il écrit",
        `<div class="pan-2col"><div><b class="text-sm">Lit</b>${liste(d.lit)}</div>` +
        `<div><b class="text-sm">Écrit</b>${liste(d.ecrit)}</div></div>`));
    } else if (aLit) {
      h.push(sec("Ce qu'il lit", liste(d.lit)));
    } else if (aEcrit) {
      h.push(sec("Ce qu'il écrit", liste(d.ecrit)));
    }
    h.push(sec("Règles et seuils", liste(d.regles)));

    if (d.decisions && d.decisions.length) {
      h.push(sec("Décisions", '<div class="pan-dec">' + d.decisions.map((x) =>
        `<div><b>si</b><span>${ech(x.si)}</span><b>alors</b><span>${ech(x.alors)}</span></div>`
      ).join("") + "</div>"));
    }
    if (d.terminal) {
      h.push(sec("État terminal posé",
        `<div class="pan-etat"><b>${ech(d.terminal.etat)}</b><br>` +
        `<span class="muted">Qui la rouvre : </span>${ech(d.terminal.rouvreur)}</div>`));
    }
    if (d.slack) h.push(sec("Ce qui part sur Slack", `<p>${ech(d.slack)}</p>`));
    if (d.cout_ia) h.push(sec("Coût IA", `<p>${ech(d.cout_ia)}</p>`));

    if (n.surveille || n.journal) {
      const e = n.etat;
      let t = `<div class="pan-etat">`;
      if (n.surveille) {
        t += e.vu ? `Vu pour la dernière fois <b>${ech(e.vu)}</b> (${ech(e.age)}).`
                  : "<b>Jamais vu passer.</b>";
        if (e.source) t += ` <span class="muted">Source : ${ech(e.source)}.</span>`;
        if (e.erreurs) t += ` <b style="color:var(--danger)">${e.erreurs} erreur(s) au dernier passage.</b>`;
        if (e.tolerance) t += `<br><span class="muted">Signalé en retard au-delà de ${e.tolerance} h (chien de garde de midi).</span>`;
      } else {
        t += `<span class="muted">Pas de surveillance automatique pour ce nœud` +
             `${n.journal ? " — voir son journal ci-dessous" : ""}.</span>`;
      }
      t += "</div>";
      h.push(sec("Dernier passage", t));
    }
    if (n.commande) {
      h.push(sec("La commande", `<code class="pan-cmd">${ech(n.commande)}</code>` +
        (n.journal ? `<p class="muted text-sm" style="margin-top:.3rem">Journal : <code>${ech(n.journal)}</code></p>` : "")));
    }
    if (d.notes && d.notes.length) {
      h.push(sec("À savoir", d.notes.map((x) => `<div class="pan-note">${ech(x)}</div>`).join("")));
    }
    const refs = [].concat(d.code || [], d.doc || []);
    if (refs.length) {
      h.push(sec("Où c'est écrit", '<div class="pan-liens">' +
        refs.map((f) => `<a href="https://github.com/monodf-beep/evenements/blob/claude/quirky-davinci-jvqrnw/${ech(f)}" target="_blank" rel="noopener">${ech(f)}</a>`).join("") + "</div>"));
    }
    corps.innerHTML = h.join("");
    corps.scrollTop = 0;
  }

  function ouvrir(id, depuis) {
    const n = parId[id];
    if (!n) return;
    ouvreur = depuis || null;
    remplir(n);
    panneau.classList.add("ouvert");
    voile.classList.add("ouvert");
    racine.querySelectorAll(".nd").forEach((b) =>
      b.setAttribute("aria-pressed", String(b.dataset.id === id)));
    // Mettre en avant les liens du nœud choisi : à vingt nœuds, la toile devient illisible
    // si tout reste au même niveau.
    racine.querySelectorAll("path.lien").forEach((p) =>
      p.classList.toggle("lien--attenue", p.dataset.de !== id && p.dataset.vers !== id));
    panneau.focus();
  }

  function fermer() {
    panneau.classList.remove("ouvert");
    voile.classList.remove("ouvert");
    racine.querySelectorAll(".nd").forEach((b) => b.setAttribute("aria-pressed", "false"));
    racine.querySelectorAll("path.lien").forEach((p) => p.classList.remove("lien--attenue"));
    if (ouvreur && document.contains(ouvreur)) ouvreur.focus();
    ouvreur = null;
  }

  racine.addEventListener("click", (e) => {
    const b = e.target.closest("[data-id]");
    if (b) return ouvrir(b.dataset.id, b);
    if (e.target.closest("[data-fermer]")) fermer();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && panneau.classList.contains("ouvert")) fermer();
  });

  /* Ouverture directe par l'adresse : /process#editorial */
  const dep = (location.hash || "").replace("#", "");
  montrer(tabs.some((t) => t.dataset.flux === dep) ? dep : tabs[0].dataset.flux);
  window.addEventListener("resize", () => {
    racine.querySelectorAll('[role="tabpanel"]:not([hidden]) .scene-hote')
      .forEach((h) => { if (branchees.has(h)) ajuster(h); });
  });
})();
