// Le moteur de Yoast, hors navigateur.
//
// Yoast calcule ses notes SEO et lisibilité en JavaScript, dans l'éditeur, et nulle part
// ailleurs (constaté le 16/09/2026 : 678 fiches publiées sur 694 sans aucune note, tout
// ce que le pipeline publie par API). Le paquet npm `yoastseo` EST ce code, publié en
// open source par Yoast : même moteur, mêmes assesseurs, mêmes seuils — donc mêmes notes,
// à une réserve près, la largeur du titre en pixels, que le navigateur mesure et qu'on
// estime ici (PX_PAR_CAR). Témoins : tests/fixtures/yoast_temoins.json, cinq fiches
// notées par l'éditeur (dont deux lues dans le navigateur le 16/09 : 86 / 60 et 85 / 30)
// que ce script doit reproduire à l'unité près.
//
// Entrée : JSON sur stdin, tableau de fiches telles que cs/v1/yoast-papers les sert
//   {id, content, keyword, title, description, slug, permalink, locale, post_title, date,
//    featured_html, kw_utilisee_ailleurs}
// Sortie : JSON sur stdout, [{id, seo, lisibilite, seo_detail, lis_detail}]
//
// Aucun réseau, aucune écriture : la lecture et l'écriture WordPress sont dans
// scripts/yoast_scores.py. Lancer à la main :
//   echo '[…]' | node scripts/yoast_score.js
"use strict";
const { Paper, SeoAssessor, ContentAssessor, AssessmentResult } = require("yoastseo");
// LE TOTAL N'EST PAS CELUI DE L'ASSESSEUR, C'EST CELUI DU WORKER. `calculateOverallScore`
// ne compte que les résultats « valides » (avec une note et un texte) ; l'éditeur, lui,
// passe TOUS les résultats à l'agrégateur, y compris `functionWordsInKeyphrase`, noté 0 et
// jamais affiché. Trouvé le 16/09 par l'arithmétique : 139 / (17 × 9) = 91 chez moi,
// 139 / (18 × 9) = 86 chez Yoast — la note de Franck. Un dix-huitième résultat invisible.
const SEOScoreAggregator = require("yoastseo/build/scoring/scoreAggregators/SEOScoreAggregator").default;
const RESEARCHERS = {
  fr: require("yoastseo/build/languageProcessing/languages/fr/Researcher").default,
  it: require("yoastseo/build/languageProcessing/languages/it/Researcher").default,
  en: require("yoastseo/build/languageProcessing/languages/en/Researcher").default,
};
// Largeur du titre : le navigateur la mesure dans la police de l'aperçu ; ici on
// l'estime. Le seuil de Yoast est 600 px, soit ~64 caractères à 9,3 px.
const PX_PAR_CAR = parseFloat(process.env.PX_PAR_CAR || "9.3");

// TROIS CHOSES QUE L'ÉDITEUR FAIT ET QU'UN MOTEUR NU NE FAIT PAS — trouvées le 16/09 en
// comparant, ligne par ligne, le panneau Yoast collé par Franck (8236 : 86/60, 8231 :
// 85/30) et la sortie de ce script (86/90, 81/30) :
//   1. la LOCALE d'analyse est celle du SITE (fr_FR), pas celle de l'article : l'éditeur
//      juge un texte italien avec les règles françaises — « 65 % de phrases de plus de
//      20 mots » là où l'italien tolère 25, « aucun mot de transition » parce qu'il
//      cherche les français. La route cs/v1/yoast-papers sert donc la locale du site ;
//   2. l'IMAGE MISE EN AVANT est ajoutée au texte analysé : « Images : bon travail »
//      sur un corps sans aucune balise img. La route sert son HTML, on l'ajoute ici ;
//   3. « expression clé utilisée précédemment » est une évaluation de PLUS, portée par
//      un greffon WordPress (bundledPlugins/previouslyUsedKeywords) : 9 si la clé n'est
//      utilisée nulle part ailleurs, 6 si une fois, 1 au-delà, 1 sans clé. La route sert
//      le compte, on rejoue le barème du greffon tel quel.
function evaluationCleDejaUtilisee(count, keyword) {
  return {
    isApplicable: () => true,
    getResult: () => {
      const r = new AssessmentResult();
      let score = 1;
      if (keyword) { score = count === 0 ? 9 : (count === 1 ? 6 : 1); }
      r.setScore(score);
      r.setText("Expression clé utilisée précédemment (rejoué hors navigateur).");
      return r;
    },
  };
}

function scorer(e) {
  const lang = String(e.locale || "fr_FR").slice(0, 2);
  const R = RESEARCHERS[lang] || RESEARCHERS.fr;
  const title = e.title || "";
  const contenu = (e.content || "") + (e.featured_html ? "\n" + e.featured_html : "");
  const paper = new Paper(contenu, {
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
  seo.addAssessment("usedKeywords", evaluationCleDejaUtilisee(
    Number.isInteger(e.kw_utilisee_ailleurs) ? e.kw_utilisee_ailleurs : 0, e.keyword || ""));
  seo.assess(paper);
  const lis = new ContentAssessor(researcher, {});
  lis.assess(paper);
  return {
    id: e.id,
    seo: new SEOScoreAggregator().aggregate(seo.results),
    // La lisibilité, elle, se calcule sur les résultats VALIDES seulement : passer les
    // résultats à 0 à l'agrégateur les compte comme des points rouges (8236 : 30 au lieu
    // du 60 de l'éditeur). Vérifié sur les deux notes fraîches de Franck.
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
