// Le moteur de Yoast, hors navigateur.
//
// Yoast calcule ses notes SEO et lisibilité en JavaScript, dans l'éditeur, et nulle part
// ailleurs (constaté le 16/09/2026 : 678 fiches publiées sur 694 sans aucune note, tout
// ce que le pipeline publie par API). Le paquet npm `yoastseo` EST ce code, publié en
// open source par Yoast : même moteur, mêmes assesseurs, mêmes seuils — donc mêmes notes,
// à une réserve près, la largeur du titre en pixels, que le navigateur mesure et qu'on
// estime ici (PX_PAR_CAR). Témoin : tests/fixtures/yoast_temoin_7490.json, une fiche
// notée par l'éditeur (67 / 90) que ce script doit reproduire à l'identique.
//
// Entrée : JSON sur stdin, tableau de fiches telles que cs/v1/yoast-papers les sert
//   {id, content, keyword, title, description, slug, permalink, locale, post_title, date}
// Sortie : JSON sur stdout, [{id, seo, lisibilite, seo_detail, lis_detail}]
//
// Aucun réseau, aucune écriture : la lecture et l'écriture WordPress sont dans
// scripts/yoast_scores.py. Lancer à la main :
//   echo '[…]' | node scripts/yoast_score.js
"use strict";
const { Paper, SeoAssessor, ContentAssessor } = require("yoastseo");
const RESEARCHERS = {
  fr: require("yoastseo/build/languageProcessing/languages/fr/Researcher").default,
  it: require("yoastseo/build/languageProcessing/languages/it/Researcher").default,
  en: require("yoastseo/build/languageProcessing/languages/en/Researcher").default,
};
// Largeur du titre : le navigateur la mesure dans la police de l'aperçu ; ici on
// l'estime. Le seuil de Yoast est 600 px, soit ~64 caractères à 9,3 px.
const PX_PAR_CAR = parseFloat(process.env.PX_PAR_CAR || "9.3");

function scorer(e) {
  const lang = String(e.locale || "fr_FR").slice(0, 2);
  const R = RESEARCHERS[lang] || RESEARCHERS.fr;
  const title = e.title || "";
  const paper = new Paper(e.content || "", {
    keyword: e.keyword || "",
    title,
    titleWidth: Math.round(title.length * PX_PAR_CAR),
    description: e.description || "",
    slug: e.slug || "",
    permalink: e.permalink || "",
    locale: e.locale || "fr_FR",
    date: e.date || "",
    textTitle: e.post_title || "",
  });
  const researcher = new R(paper);
  const seo = new SeoAssessor(researcher, {});
  seo.assess(paper);
  const lis = new ContentAssessor(researcher, {});
  lis.assess(paper);
  return {
    id: e.id,
    seo: seo.calculateOverallScore(),
    lisibilite: lis.calculateOverallScore(),
    seo_detail: seo.getValidResults().map(r => ({ id: r.getIdentifier(), score: r.getScore() })),
    lis_detail: lis.getValidResults().map(r => ({ id: r.getIdentifier(), score: r.getScore() })),
  };
}

let buf = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", d => { buf += d; });
process.stdin.on("end", () => {
  const entree = JSON.parse(buf || "[]");
  process.stdout.write(JSON.stringify(entree.map(scorer)));
});
