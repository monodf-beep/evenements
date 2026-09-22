#!/usr/bin/env python3
"""Fixture : le raccourci `[cs_moment_liste]` (deploy/wordpress/cs-liste-moment.php).

POURQUOI. C'est le corps de la page dédiée d'un moment fort, et cette page est VIDE
onze mois sur douze — la liste ne montre que ce qui est à venir. C'est donc dans ces
mois-là qu'elle sera le plus souvent relue, par Google comme par un lecteur qui suit
un lien. Une page qui se contente de ne rien afficher est une page morte ; celle-ci
doit dire ce qui se passe.

Trois volets, chacun avec sa contre-épreuve :

  1. LA SAISON. Des fiches à venir => la liste s'affiche, groupée par jour. Hors
     saison => la phrase déclarée, PAS une page blanche, et un commentaire qui dit
     d'où vient le zéro.
  2. LA BORNE. Elle porte sur la date de FIN, pas de début : une exposition commencée
     en mai et ouverte aujourd'hui compte (règle 5 du CLAUDE.md). Contre-épreuve :
     une fiche terminée hier ne compte pas.
  3. LES DEUX CAUSES D'UNE LISTE VIDE. Avant l'édition, la page ne doit PAS dire
     qu'elle est passée. Constaté en ligne le 22/09 : elle annonçait « l'édition 2026
     s'est tenue les 26 et 27 septembre » quatre jours avant l'événement.
  4. LE COMPTEUR. Il annonce les fiches DE L'AGENDA encore à venir, et son libellé
     est fourni par la page — deux compteurs qui portent le même nom se contrediront
     un jour (règle 6).

Lancer : .venv/bin/python -m tests.test_liste_moment
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHP_FILE = ROOT / "deploy" / "wordpress" / "cs-liste-moment.php"

echecs = 0


def echec(m):
    global echecs
    echecs += 1
    print("ECHEC : " + m)


HARNESS = r"""<?php
define('ABSPATH', 1);
define('MINUTE_IN_SECONDS', 60);
define('HOUR_IN_SECONDS', 3600);

$GLOBALS['cs_f'] = json_decode(file_get_contents($argv[1]), true);
$GLOBALS['cs_lang'] = $argv[2];
$GLOBALS['cs_sc'] = array();

function current_time($f) { return $f === 'Y-m-d' ? '2026-09-24' : '2026-09-24 10:00:00'; }
function esc_html($s) { return htmlspecialchars($s, ENT_QUOTES); }
function esc_url($s) { return $s; }
function get_transient($k) { return false; }
function set_transient($k, $v, $t) { return true; }
function wp_reset_postdata() {}
function shortcode_atts($pairs, $atts, $sc = '') { return array_merge($pairs, (array) $atts); }
function add_shortcode($tag, $cb) { $GLOBALS['cs_sc'][$tag] = $cb; }
function pll_current_language() { return $GLOBALS['cs_lang']; }
function get_the_post_thumbnail_url($p, $t) { return 'https://exemple.test/i.webp'; }

class WP_Query {
    public $posts = array();
    public function __construct($args) {
        // `terms` est une LISTE de slugs depuis le 22/09 (Polylang suffixe le terme
        // italien) : le harnais doit la lire comme telle, sinon il teste autre chose
        // que ce que le site exécute.
        $etiq = (array) $args['tax_query'][0]['terms'];
        $borne = $args['meta_query']['fin']['value'];
        foreach ($GLOBALS['cs_f'] as $i => $f) {
            if (!in_array($f['etiq'], $etiq, true)) { continue; }
            if ($f['lang'] !== $GLOBALS['cs_lang']) { continue; }
            if ($f['fin'] < $borne) { continue; }
            $o = new stdClass(); $o->ID = $i; $this->posts[] = $o;
        }
        usort($this->posts, function ($a, $b) {
            return strcmp($GLOBALS['cs_f'][$a->ID]['fin'], $GLOBALS['cs_f'][$b->ID]['fin']);
        });
    }
}
function get_post_meta($id, $cle, $u = false) {
    $f = $GLOBALS['cs_f'][$id];
    if ($cle === '_EventStartDate') { return $f['debut']; }
    if ($cle === '_EventEndDate')   { return $f['fin']; }
    if ($cle === 'as_lieu')  { return $f['lieu']; }
    if ($cle === 'as_ville') { return $f['ville']; }
    if ($cle === 'as_gratuit') { return !empty($f['gratuit']); }
    return '';
}
function get_the_title($p) { return $GLOBALS['cs_f'][$p->ID]['titre']; }
function get_permalink($p) { return 'https://agendasabauda.eu/evenement/' . $p->ID . '/'; }

require __DIR__ . '/cs-liste-moment.php';

$cb = $GLOBALS['cs_sc']['cs_moment_liste'];
echo $cb(json_decode($argv[3], true));
"""


def rendre(fiches, lang, atts, tmp):
    fj = tmp / "f.json"
    fj.write_text(json.dumps(fiches), encoding="utf-8")
    r = subprocess.run([shutil.which("php"), str(tmp / "h.php"), str(fj), lang,
                        json.dumps(atts)], capture_output=True, text=True)
    if r.returncode != 0:
        echec("harnais PHP : " + (r.stderr or "")[:400])
        return ""
    return r.stdout


def f(etiq, debut, fin, titre, lang="fr", ville="Turin", lieu="Musei Reali", gratuit=False):
    return dict(etiq=etiq, debut=debut + " 10:00:00", fin=fin + " 23:59:59",
                titre=titre, lang=lang, ville=ville, lieu=lieu, gratuit=gratuit)


def main():
    php = shutil.which("php")
    if not php:
        print("php absent : cette fixture n'est PAS jouée (ce n'est pas un succès).")
        return
    tmp = Path(tempfile.mkdtemp())
    shutil.copy(PHP_FILE, tmp / "cs-liste-moment.php")
    (tmp / "h.php").write_text(HARNESS, encoding="utf-8")
    E = "journees-europeennes-du-patrimoine"
    atts = {"etiquette": E, "vide": "L'édition 2026 est passée.", "total": "%d fiches à venir"}

    # --- 1. LA SAISON --------------------------------------------------------
    jeu = [
        f(E, "2026-09-26", "2026-09-26", "Musei Reali de sera"),
        f(E, "2026-09-26", "2026-09-26", "Palazzo Carignano", lieu="Palazzo Carignano"),
        f(E, "2026-09-27", "2026-09-27", "Chasse au tresor", ville="Racconigi", lieu="Castello"),
    ]
    html = rendre(jeu, "fr", atts, tmp)
    if "Samedi 26 septembre" not in html or "Dimanche 27 septembre" not in html:
        echec("saison : les deux jours doivent apparaitre en titre")
    elif html.count("cs-ml__carte") != 3:
        echec("saison : 3 cartes attendues, %d rendues" % html.count("cs-ml__carte"))
    else:
        print("  ok  saison : deux jours, trois cartes")

    # CONTRE-ÉPREUVE : hors saison, la phrase declaree et PAS une page blanche.
    vide = rendre([f(E, "2026-09-01", "2026-09-02", "Deja fini")], "fr", atts, tmp)
    if "cs-ml__carte" in vide:
        echec("hors saison : aucune carte ne doit sortir")
    elif "L&#039;édition 2026 est passée." not in vide:
        echec("hors saison : la phrase declaree doit s'afficher")
    elif "aucune fiche à venir" not in vide:
        echec("hors saison : le commentaire doit dire d'ou vient le zero")
    else:
        print("  ok  hors saison : la phrase s'affiche, et le commentaire dit d'où vient le zéro")

    # --- 2. LA BORNE PORTE SUR LA FIN ---------------------------------------
    # Une exposition commencee en mai et ouverte aujourd'hui COMPTE.
    longue = rendre([f(E, "2026-05-01", "2026-10-30", "Exposition de l ete")], "fr", atts, tmp)
    if "cs-ml__carte" not in longue:
        echec("borne : une exposition en cours doit compter — c'est la date de FIN qui décide")
    else:
        print("  ok  borne : l'exposition commencée en mai et encore ouverte compte")
    # Contre-epreuve : terminee hier, elle ne compte pas.
    hier = rendre([f(E, "2026-09-01", "2026-09-23", "Terminee hier")], "fr", atts, tmp)
    if "cs-ml__carte" in hier:
        echec("borne : une fiche terminée hier ne doit pas compter")
    else:
        print("  ok  contre-épreuve : terminée hier, elle ne compte pas")

    # --- 3. LA LANGUE ET LE COMPTEUR ----------------------------------------
    mixte = jeu + [f(E, "2026-09-26", "2026-09-26", "Musei Reali di sera", lang="it")]
    hfr = rendre(mixte, "fr", atts, tmp)
    if "3 fiches à venir" not in hfr:
        echec("compteur : il doit annoncer 3 fiches françaises, pas 4")
    else:
        print("  ok  compteur : 3 fiches françaises sur 4 fiches au total")
    hit = rendre(mixte, "it", atts, tmp)
    if hit.count("cs-ml__carte") != 1:
        echec("langue : la page italienne ne doit voir que la fiche italienne")
    elif "Sabato 26 settembre" not in hit:
        echec("langue : le jour doit être écrit en italien")
    else:
        print("  ok  langue : une seule fiche en italien, et « Sabato 26 settembre »")

    # Une étiquette absente ne doit rien rendre de visible.
    sans = rendre(jeu, "fr", {"etiquette": ""}, tmp)
    if "<div" in sans:
        echec("étiquette absente : rien de visible ne doit sortir")
    else:
        print("  ok  étiquette absente : un commentaire, rien de plus")

    # --- 3. LES DEUX CAUSES D'UNE LISTE VIDE --------------------------------
    # Le harnais est au 24 septembre ; la fenêtre déclarée est le 26-27.
    fen = dict(atts)
    fen.update({"debut": "2026-09-26", "fin": "2026-09-27",
                "avant": "Le programme arrive.", "apres": "L edition est passee."})
    av = rendre([], "fr", fen, tmp)
    if "L edition est passee." in av:
        echec("avant l'édition : la page ne doit pas dire qu'elle est passée")
    elif "Le programme arrive." not in av:
        echec("avant l'édition : la phrase « avant » doit s'afficher")
    elif "avant la fenêtre" not in av:
        echec("avant l'édition : le commentaire doit situer la date par rapport à la fenêtre")
    else:
        print("  ok  avant l'édition : « Le programme arrive. », pas « passée »")

    # CONTRE-ÉPREUVE : une fenêtre déjà close doit, elle, donner la phrase « après ».
    close = dict(fen); close.update({"debut": "2026-08-01", "fin": "2026-08-02"})
    ap = rendre([], "fr", close, tmp)
    if "L edition est passee." not in ap:
        echec("après l'édition : la phrase « après » doit s'afficher")
    elif "après la fenêtre" not in ap:
        echec("après l'édition : le commentaire doit le dire")
    else:
        print("  ok  contre-épreuve : fenêtre close, « L'édition est passée »")

    # --- 5. PLUSIEURS SLUGS POUR UNE MÊME ÉTIQUETTE --------------------------
    # Mesuré en ligne le 22/09 : Polylang a créé le terme italien avec un suffixe
    # `-it`, et la page italienne affichait ZÉRO fiche pendant que la française en
    # montrait vingt-trois. Le raccourci accepte donc une liste.
    suff = [f("giornate-europee-del-patrimonio-it", "2026-09-26", "2026-09-26",
              "Musei Reali di sera", lang="it")]
    deux = {"etiquette": "giornate-europee-del-patrimonio, giornate-europee-del-patrimonio-it",
            "vide": "", "total": "%d"}
    h2 = rendre(suff, "it", deux, tmp)
    if "cs-ml__carte" not in h2:
        echec("deux slugs : la fiche portant le slug suffixé doit être trouvée")
    else:
        print("  ok  deux slugs déclarés : la fiche au slug suffixé est trouvée")

    # CONTRE-ÉPREUVE : avec le SEUL slug non suffixé, elle ne doit PAS l'être — sans
    # ça, le volet ci-dessus passerait même si le filtre ne filtrait rien.
    un = dict(deux); un["etiquette"] = "giornate-europee-del-patrimonio"
    h3 = rendre(suff, "it", un, tmp)
    if "cs-ml__carte" in h3:
        echec("contre-épreuve : avec le seul slug non suffixé, rien ne doit sortir")
    else:
        print("  ok  contre-épreuve : un seul slug déclaré, la fiche suffixée est ignorée")

    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
    print(("%d echec(s)" % echecs) if echecs else "tout est vert")
    sys.exit(1 if echecs else 0)
