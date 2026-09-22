#!/usr/bin/env python3
"""Fixture : le gabarit « moment fort » (deploy/wordpress/cs-moment-fort.php).

POURQUOI CETTE FIXTURE EXISTE. La strate est un GABARIT : on y posera Noël, Pâques,
les festivals d'été sans rouvrir le code. Ce qui se règle sans relecture doit donc se
vérifier tout seul, sinon la première configuration fausse partira en production.

Sept volets, et chacun porte sa CONTRE-ÉPREUVE — un test qui ne cherche qu'à se
donner raison ne prouve rien (CLAUDE.md, règle 3) :

  1. CONTRASTES. Toute paire fond / couleur de la palette doit passer AA (4,5:1).
     Contre-épreuve : le rouge de la charte sur le bleu sabauda (3,3:1, mesuré) doit
     être REFUSÉ par le même calcul. Sans ça, un calcul cassé passerait au vert.
  2. UNE SEULE STRATE. Un lecteur de Savoie, avec deux voisins en fête le même
     week-end, doit voir UNE bande, pas deux. Contre-épreuve : la même page pour un
     lecteur du Piémont doit rendre l'autre mise, pas celle des voisins.
  3. LE SEUIL. Sous le seuil, rien — et le commentaire doit DIRE le nombre trouvé.
     Contre-épreuve, choisie juste au-dessus de la frontière : exactement le seuil
     doit PASSER.
  4. LE JOUR VIDE, ET LUI SEUL. Un jour déclaré sans aucune fiche disparaît ; un jour
     qui n'en a qu'UNE reste. Le seuil était à deux, et Franck l'a vu en ligne le
     22/09 : « où est le dimanche ? » — il n'avait qu'une fiche, il disparaissait,
     pendant que le bloc de dates annonçait « 26 & 27 sept. » juste à côté.
  5. LE SURTITRE ne se coupe pas au trait d'union d'un mot composé. Contre-épreuve :
     un surtitre sans trait sort intact.
  6. LA BANDE CONTENUE : plus de 100vw, et le clip de la home maintenu (il couvre
     aussi deux barres du thème). Contre-épreuve : l'ancien CSS est refusé.
  7. LA PURGE : une fiche d'événement qui change vide exactement les clés que les
     lecteurs écrivent. Contre-épreuve : une page, une autre taxonomie, ou une requête
     pas encore terminée ne vident rien.

Lancer : .venv/bin/python -m tests.test_moment_fort
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHP_FILE = ROOT / "deploy" / "wordpress" / "cs-moment-fort.php"

echecs = 0


def echec(message):
    global echecs
    echecs += 1
    print("ECHEC : " + message)


# ---------------------------------------------------------------- 1. contrastes
def _luminance(hexa):
    hexa = hexa.lstrip("#")
    canaux = [int(hexa[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canaux]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contraste(a, b):
    l1, l2 = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def palettes_du_php():
    """Relit la palette DANS le fichier livré, pas une copie.

    Une palette recopiée dans le test se désynchronise le jour où quelqu'un ajoute
    une couleur — et le test continuerait de passer sur l'ancienne.
    """
    texte = PHP_FILE.read_text(encoding="utf-8")
    debut = texte.index("function cs_mf_palette(")
    fin = texte.index("return isset($p[$nom])", debut)
    bloc = texte[debut:fin]
    out = {}
    for nom, corps in re.findall(r"'(\w+)'\s*=>\s*array\((.*?)\),\s*\n", bloc, re.S):
        champs = dict(re.findall(r"'(\w+)'\s*=>\s*'(#[0-9A-Fa-f]{6})'", corps))
        if champs:
            out[nom] = champs
    return out


def test_contrastes():
    palettes = palettes_du_php()
    if len(palettes) < 2:
        echec("palette illisible dans le PHP : %d entrée(s) trouvée(s)" % len(palettes))
        return
    for nom, c in sorted(palettes.items()):
        fond = c.get("fond")
        if not fond:
            echec("palette « %s » sans fond" % nom)
            continue
        for champ in ("texte", "accent", "attenue", "discret"):
            if champ not in c:
                echec("palette « %s » : champ %s absent" % (nom, champ))
                continue
            r = contraste(c[champ], fond)
            if r < 4.5:
                echec("palette « %s » : %s (%s) sur %s = %.2f:1, sous AA"
                      % (nom, champ, c[champ], fond, r))
            else:
                print("  ok  %-6s %-8s %s sur %s = %.2f:1" % (nom, champ, c[champ], fond, r))

    # CONTRE-ÉPREUVE : une paire qu'on SAIT mauvaise doit être refusée par le même calcul.
    # Le rouge de la charte sur le bleu sabauda, mesuré le 22/09 : 3,3:1.
    mauvais = contraste("#DC5D45", "#18365E")
    if mauvais >= 4.5:
        echec("contre-épreuve : #DC5D45 sur #18365E donne %.2f:1, le calcul ne sait pas refuser"
              % mauvais)
    else:
        print("  ok  contre-épreuve : #DC5D45 sur #18365E = %.2f:1, refusé" % mauvais)


# ------------------------------------------------------------------- 2/3/4. rendu
HARNESS = r"""<?php
define('ABSPATH', 1);
define('HOUR_IN_SECONDS', 3600);
define('MINUTE_IN_SECONDS', 60);

$GLOBALS['cs_test_fiches'] = json_decode(file_get_contents($argv[1]), true);
$GLOBALS['cs_test_lang']   = $argv[2];
$GLOBALS['cs_test_terr']   = $argv[3];
$GLOBALS['cs_test_pages']  = isset($argv[4]) ? $argv[4] : 'toutes';

function current_time($f) { return $f === 'Y-m-d' ? '2026-09-24' : '2026-09-24 10:00:00'; }
function esc_html($s) { return htmlspecialchars($s, ENT_QUOTES); }
function esc_attr($s) { return htmlspecialchars($s, ENT_QUOTES); }
function esc_url($s)  { return $s; }
function get_transient($k) { return false; }
function set_transient($k, $v, $t) { return true; }
function wp_reset_postdata() {}
function add_filter($a, $b, $c = 10) {}
function add_action($a, $b, $c = 10, $d = 1) {}
function is_admin() { return false; }
function is_page($x) { return true; }
function pll_current_language() { return $GLOBALS['cs_test_lang']; }
function cs_territoire_actif() { return $GLOBALS['cs_test_terr']; }
function home_url($p = '/') { return 'https://agendasabauda.eu' . $p; }
// Les pages existantes sont passées en 4e argument : « toutes » ou une liste d'URL.
function url_to_postid($url) {
    $p = $GLOBALS['cs_test_pages'];
    if ($p === 'toutes') { return 1; }
    return in_array($url, explode('|', $p), true) ? 1 : 0;
}
function get_post_status($id) { return 'publish'; }

class WP_Query {
    public $posts = array();
    public function __construct($args) {
        $terme = $args['tax_query'][0]['terms'];
        foreach ($GLOBALS['cs_test_fiches'] as $i => $f) {
            if ($f['terr'] !== $terme) { continue; }
            $d = $f['debut'];
            if ($d < $args['meta_query']['debut']['value'][0]) { continue; }
            if ($d > $args['meta_query']['debut']['value'][1]) { continue; }
            $o = new stdClass(); $o->ID = $i; $this->posts[] = $o;
        }
    }
}
function get_post_meta($id, $cle, $u = false) {
    $f = $GLOBALS['cs_test_fiches'][$id];
    if ($cle === '_EventStartDate') { return $f['debut']; }
    if ($cle === 'as_lieu')  { return $f['lieu']; }
    if ($cle === 'as_ville') { return $f['ville']; }
    return '';
}
function get_the_title($p) { return $GLOBALS['cs_test_fiches'][$p->ID]['titre']; }
function get_permalink($p) { return 'https://agendasabauda.eu/evenement/' . $p->ID . '/'; }

require __DIR__ . '/cs-moment-fort.php';

$m = cs_moment_fort_actif();
echo cs_mf_html($m, $GLOBALS['cs_test_lang'], $GLOBALS['cs_test_terr']);
"""


def rendre(fiches, lang, terr, tmp, pages="toutes"):
    import json
    f_json = tmp / "fiches.json"
    f_json.write_text(json.dumps(fiches), encoding="utf-8")
    r = subprocess.run([shutil.which("php"), str(tmp / "harness.php"), str(f_json), lang, terr, pages],
                       capture_output=True, text=True)
    if r.returncode != 0:
        echec("le harnais PHP a échoué : " + (r.stderr or "")[:400])
        return ""
    return r.stdout


def fiche(terr, debut, lieu, ville, titre):
    return dict(terr=terr, debut=debut, lieu=lieu, ville=ville, titre=titre)


def test_rendu():
    php = shutil.which("php")
    if not php:
        print("php absent : les volets 2 à 4 ne sont PAS joués (ce n'est pas un succès).")
        return

    tmp = Path(tempfile.mkdtemp())
    shutil.copy(PHP_FILE, tmp / "cs-moment-fort.php")
    (tmp / "harness.php").write_text(HARNESS, encoding="utf-8")

    # Un jeu qui ressemble à la production : deux jours en Piémont, deux lieux par jour.
    jeu = [
        fiche("piemont", "2026-09-26 20:00:00", "Musei Reali", "Turin", "Ouverture en soiree"),
        fiche("piemont", "2026-09-26 20:00:00", "Palazzo Carignano", "Turin", "Les Appartements"),
        fiche("piemont", "2026-09-26 18:00:00", "Villa della Regina", "Turin", "Aperitivo in Vigna"),
        fiche("piemont", "2026-09-27 10:00:00", "Libarna", "Serravalle", "La ville romaine"),
        fiche("piemont", "2026-09-27 10:00:00", "Discoteca Olivetti", "Ivree", "La musique de l usine"),
        fiche("vallee-d-aoste", "2026-09-21 10:00:00", "Chateau de Fenis", "Fenis", "Visite guidee"),
        fiche("vallee-d-aoste", "2026-09-24 10:00:00", "Aosta", "Aoste", "Plaisirs de Culture"),
        fiche("vallee-d-aoste", "2026-09-26 10:00:00", "Bard", "Bard", "Le fort ouvre"),
    ]

    # --- 2. UNE SEULE STRATE -------------------------------------------------
    html_savoie = rendre(jeu, "fr", "savoie", tmp)
    n = html_savoie.count('<section class="cs-mf')
    if n != 1:
        echec("lecteur de Savoie : %d strate(s) rendue(s), il en faut exactement 1" % n)
    elif "cs-mf--voisins" not in html_savoie:
        echec("lecteur de Savoie : la mise « voisins » attendue n'est pas rendue")
    else:
        print("  ok  Savoie : une seule strate, mise « voisins »")
    # `esc_html` échappe l'apostrophe en `&#039;` (ENT_QUOTES, comme WordPress) : on
    # compare donc à la forme ÉCHAPPÉE, sinon le test échoue sur sa propre chaîne.
    for attendu in ("Piémont", "Vallée d&#039;Aoste"):
        if attendu not in html_savoie:
            echec("lecteur de Savoie : le volet « %s » manque" % attendu)

    # CONTRE-ÉPREUVE : le même moment, pour un lecteur du Piémont, doit changer de mise.
    html_piemont = rendre(jeu, "fr", "piemont", tmp)
    if "cs-mf--programme" not in html_piemont:
        echec("lecteur du Piémont : la mise « programme » attendue n'est pas rendue")
    elif "cs-mf--voisins" in html_piemont:
        echec("lecteur du Piémont : la mise « voisins » ne devrait pas apparaître")
    else:
        print("  ok  Piémont : mise « programme », pas « voisins »")
    if html_piemont.count('<section class="cs-mf') != 1:
        echec("lecteur du Piémont : il faut exactement une strate")

    # --- 3. LE SEUIL ---------------------------------------------------------
    maigre = [f for f in jeu if f["terr"] == "piemont"][:2] + [f for f in jeu if f["terr"] != "piemont"]
    html_maigre = rendre(maigre, "fr", "piemont", tmp)
    if "<section" in html_maigre:
        echec("seuil : 2 fiches pour un seuil de 3, la strate ne doit pas s'afficher")
    elif "2 fiche(s) pour un seuil de 3" not in html_maigre:
        echec("seuil : le commentaire ne dit pas le nombre trouvé — un zéro doit dire d'où il vient")
    else:
        print("  ok  seuil : masquée, et le commentaire annonce « 2 fiche(s) pour un seuil de 3 »")

    # CONTRE-ÉPREUVE, juste au-dessus de la frontière : EXACTEMENT le seuil doit passer.
    pile = [f for f in jeu if f["terr"] == "piemont"][:3] + [f for f in jeu if f["terr"] != "piemont"]
    html_pile = rendre(pile, "fr", "piemont", tmp)
    if "<section" not in html_pile:
        echec("seuil : 3 fiches pour un seuil de 3 DOIT passer, la frontière est inclusive")
    else:
        print("  ok  contre-épreuve du seuil : 3 fiches pour un seuil de 3, la strate s'affiche")

    # --- 4. LE JOUR VIDE, ET LUI SEUL ----------------------------------------
    # Samedi garni, dimanche à UNE seule ligne : le dimanche doit rester. C'est le
    # défaut que Franck a vu en ligne, la bande promettait deux jours et n'en montrait
    # qu'un.
    boiteux = [f for f in jeu if f["terr"] == "piemont" and f["debut"].startswith("2026-09-26")]
    boiteux += [f for f in jeu if f["terr"] == "piemont" and f["debut"].startswith("2026-09-27")][:1]
    boiteux += [f for f in jeu if f["terr"] != "piemont"]
    html_boiteux = rendre(boiteux, "fr", "piemont", tmp)
    if "Dimanche 27" not in html_boiteux:
        echec("jour à une seule fiche : le dimanche DOIT rester, la bande annonce deux jours")
    elif "Samedi 26" not in html_boiteux:
        echec("jour à une seule fiche : le samedi doit rester aussi")
    else:
        print("  ok  un jour à une seule fiche reste affiché")

    # LE PLAFOND NE DOIT PAS AFFAMER UN JOUR. Douze fiches le samedi, une le dimanche :
    # si la requête est bornée trop bas et triée par date, le dimanche ne parvient
    # jamais au découpage. C'est ce qui s'est produit en ligne le 22/09.
    gros = []
    for i in range(12):
        gros.append(fiche("piemont", "2026-09-26 20:00:00", "Lieu %d" % i, "Turin", "Samedi %d" % i))
    gros.append(fiche("piemont", "2026-09-27 10:00:00", "Margaria", "Racconigi", "Le dimanche"))
    gros += [f for f in jeu if f["terr"] != "piemont"]
    html_gros = rendre(gros, "fr", "piemont", tmp)
    if "Dimanche 27" not in html_gros:
        echec("plafond : douze fiches le samedi ne doivent pas faire disparaître le dimanche")
    else:
        print("  ok  plafond : le dimanche survit à douze fiches le samedi")

    # CONTRE-ÉPREUVE : un jour déclaré SANS aucune fiche, lui, disparaît. Sans ce
    # volet, supprimer le filtre entièrement passerait au vert.
    sansdim = [f for f in jeu if f["terr"] == "piemont" and f["debut"].startswith("2026-09-26")]
    sansdim += [f for f in jeu if f["terr"] != "piemont"]
    html_sansdim = rendre(sansdim, "fr", "piemont", tmp)
    if "Dimanche 27" in html_sansdim:
        echec("jour vide : un jour sans aucune fiche ne doit pas être affiché")
    else:
        print("  ok  contre-épreuve : un jour sans aucune fiche disparaît")
    for mot in ("pas encore", "incomplet", "arrive"):
        if mot in html_boiteux.lower():
            echec("la strate parle de notre propre retard (« %s »)" % mot)

    # --- 5. LA PAGE DE DESTINATION -------------------------------------------
    # Une strate qui envoie sur un 404 est pire que pas de strate. Tant que la page
    # dédiée n'est pas publiée, la bande se tait ; le jour où elle l'est, la bande
    # s'allume sans que personne touche au code.
    html_sans_page = rendre(jeu, "fr", "piemont", tmp, pages="aucune")
    if "<section" in html_sans_page:
        echec("page absente : la strate ne doit pas s'afficher vers un 404")
    elif "n'existe pas encore" not in html_sans_page:
        echec("page absente : le commentaire doit dire pourquoi la strate se tait")
    else:
        print("  ok  page de destination absente : strate masquée, et le commentaire le dit")

    # CONTRE-ÉPREUVE : la MÊME page, déclarée existante, doit faire apparaître la strate.
    # Sans ce volet, un `url_to_postid` cassé masquerait tout en silence et le test
    # passerait au vert.
    url_piemont = "https://agendasabauda.eu/journees-europeennes-du-patrimoine-piemont/"
    html_avec_page = rendre(jeu, "fr", "piemont", tmp, pages=url_piemont)
    if "<section" not in html_avec_page:
        echec("contre-épreuve : la page existe, la strate DOIT s'afficher")
    else:
        print("  ok  contre-épreuve : la page existe, la strate s'affiche")

    # Et côté voisins : un seul volet joignable => une seule colonne, pas de lien mort.
    html_un_voisin = rendre(jeu, "fr", "savoie", tmp, pages=url_piemont)
    if "Vallée d&#039;Aoste" in html_un_voisin:
        echec("voisins : un volet dont la page n'existe pas ne doit pas être montré")
    elif "Piémont" not in html_un_voisin:
        echec("voisins : le volet joignable doit rester")
    else:
        print("  ok  voisins : seul le volet dont la page existe est montré")

    shutil.rmtree(tmp, ignore_errors=True)


def test_territoire_canonique():
    """Le territoire actif est une CLÉ CANONIQUE, pas un slug de langue.

    Trois cas mesurés en ligne le 22/09 : fr/piemont donnait la bonne mise, it/piemonte
    et fr/vallee-d-aoste tombaient en « voisins ». La fixture d'alors ne jouait que le
    premier — celui qui marche PAR COÏNCIDENCE, la clé canonique du Piémont s'écrivant
    comme son slug français. Elle se donnait raison sur le seul cas où la confusion ne
    se voit pas. Les trois sont joués ici, plus une contre-épreuve.
    """
    php = shutil.which("php")
    if not php:
        print("php absent : le volet « territoire canonique » n'est PAS joué (ce n'est pas un succès).")
        return

    tmp = Path(tempfile.mkdtemp())
    shutil.copy(PHP_FILE, tmp / "cs-moment-fort.php")
    (tmp / "harness.php").write_text(HARNESS, encoding="utf-8")

    # Les fiches portent le slug du TERME de taxonomie, qui change de langue.
    jeu_it = [
        fiche("piemonte", "2026-09-26 20:00:00", "Musei Reali", "Torino", "Apertura serale"),
        fiche("piemonte", "2026-09-26 20:00:00", "Palazzo Carignano", "Torino", "Gli Appartamenti"),
        fiche("piemonte", "2026-09-27 10:00:00", "Libarna", "Serravalle", "La citta romana"),
        fiche("piemonte", "2026-09-27 10:00:00", "Discoteca Olivetti", "Ivrea", "La musica della fabbrica"),
    ]
    html_it = rendre(jeu_it, "it", "piemont", tmp)
    if "cs-mf--programme" not in html_it:
        echec("it/piemont : la clé canonique doit donner la mise programme, pas « voisins »")
    elif "Domenica 27" not in html_it:
        echec("it/piemont : la colonne du dimanche doit être là")
    else:
        print("  ok  it + clé canonique « piemont » : mise programme, deux jours")

    jeu_vda = [
        fiche("vallee-d-aoste", "2026-09-20 10:00:00", "Chateau de Fenis", "Fenis", "Visite guidee"),
        fiche("vallee-d-aoste", "2026-09-21 10:00:00", "Chateau de Sarre", "Sarre", "Les appartements"),
        fiche("vallee-d-aoste", "2026-09-24 14:00:00", "Chateau d Issogne", "Issogne", "La cour interieure"),
    ]
    html_vda = rendre(jeu_vda, "fr", "vda", tmp)
    if "cs-mf--programme" not in html_vda:
        echec("fr/vda : la clé canonique doit donner la mise programme, pas « voisins »")
    elif "cs-mf__jour--seul" not in html_vda:
        echec("fr/vda : neuf jours sans découpage => une liste unique")
    else:
        print("  ok  fr + clé canonique « vda » : mise programme, liste unique")

    # CONTRE-ÉPREUVE : un territoire SANS volet doit toujours tomber en « voisins ».
    # Sans elle, un comparateur qui accepterait tout passerait au vert ci-dessus.
    html_nice = rendre(jeu_it, "fr", "nice", tmp)
    if "cs-mf--voisins" not in html_nice:
        echec("contre-épreuve : « nice » n'a pas de volet, la mise doit être « voisins »")
    else:
        print("  ok  contre-épreuve : « nice » sans volet => mise voisins")

    shutil.rmtree(tmp, ignore_errors=True)


def test_surtitre_insecable():
    """Le surtitre ne se coupe pas sur le trait d'union d'un mot composé.

    Vu sur la maquette de la bande contenue (22/09) : « LE RENDEZ-VOUS DU WEEK-END »
    tombait en « WEEK- / END » dans la colonne étroite. Le mot composé est enveloppé
    d'un `white-space:nowrap`. Contre-épreuve : le surtitre italien, qui n'a pas de
    trait, doit sortir INTACT — une fonction qui envelopperait chaque mot passerait
    sinon au vert, et la phrase ne pourrait plus se couper du tout.
    """
    php = shutil.which("php")
    if not php:
        print("php absent : le volet « surtitre » n'est PAS joué (ce n'est pas un succès).")
        return
    tmp = Path(tempfile.mkdtemp())
    shutil.copy(PHP_FILE, tmp / "cs-moment-fort.php")
    (tmp / "harness.php").write_text(HARNESS, encoding="utf-8")
    jeu = [fiche("piemont", "2026-09-26 20:00:00", "Lieu %d" % i, "Turin", "Titre %d" % i) for i in range(3)]
    jeu_it = [fiche("piemonte", "2026-09-26 20:00:00", "Lieu %d" % i, "Torino", "Titolo %d" % i) for i in range(3)]

    html = rendre(jeu, "fr", "piemont", tmp)
    k = re.search(r'<span class="cs-mf__kicker">(.*?)</span>(?=<h2)', html, re.S)
    attendu = ('Le <span class="cs-mf__insecable">rendez-vous</span> du '
               '<span class="cs-mf__insecable">week-end</span>')
    if not k:
        echec("surtitre : introuvable dans le rendu fr")
    elif k.group(1) != attendu:
        echec("surtitre fr : %r, attendu %r" % (k.group(1), attendu))
    else:
        print("  ok  surtitre fr : « rendez-vous » et « week-end » ne se coupent pas")
    if ".cs-mf__insecable{white-space:nowrap}" not in PHP_FILE.read_text(encoding="utf-8"):
        echec("surtitre : la règle CSS .cs-mf__insecable{white-space:nowrap} manque")

    # CONTRE-ÉPREUVE : sans trait d'union, rien n'est enveloppé.
    html_it = rendre(jeu_it, "it", "piemont", tmp)
    k = re.search(r'<span class="cs-mf__kicker">(.*?)</span>(?=<h2)', html_it, re.S)
    if not k:
        echec("surtitre : introuvable dans le rendu it")
    elif k.group(1) != "L&#039;appuntamento del fine settimana":
        echec("surtitre it : %r, il devait sortir intact" % k.group(1))
    else:
        print("  ok  contre-épreuve : surtitre it sans trait d'union, sorti intact")
    shutil.rmtree(tmp, ignore_errors=True)


def test_bande_contenue():
    """La bande tient dans la colonne : plus de `100vw` — mais le clip de la home reste.

    Demande de Franck du 22/09 (gouttières libres pour de la publicité). Ce volet ne
    remplace pas la capture — il empêche seulement le retour silencieux de la pleine
    largeur. Contre-épreuve : le même contrôle, appliqué à l'ANCIEN CSS, doit le refuser.

    LE CLIP EST EXIGÉ, pas seulement toléré. On a failli le retirer avec le 100vw, sur la
    foi du commentaire qui l'attribuait à la bande. Mesuré le 22/09 au soir : sans lui,
    la home défile de 8 px à 1280, bande ou pas — deux barres du thème sont en 100vw.
    """
    texte = PHP_FILE.read_text(encoding="utf-8")
    debut = texte.index("return '<style id=\"cs-moment-fort\">")
    css = texte[debut:texte.index("</style>';", debut)]
    # Les commentaires CSS racontent l'histoire du 100vw : on ne contrôle que les règles.
    regles = re.sub(r"/\*.*?\*/", "", css, flags=re.S)

    def refuse(r):
        return [m for m in ("100vw", "calc(50% - 50vw)") if m in r]

    trouves = refuse(regles)
    if trouves:
        echec("bande contenue : le CSS porte encore %s" % ", ".join(trouves))
    else:
        print("  ok  bande contenue : ni 100vw, ni marge négative")
    if ".as-home-root{overflow-x:clip}" not in regles:
        echec("clip retiré : la home défilerait de 8 px (barres du thème en 100vw)")
    else:
        print("  ok  le clip de la home est toujours là (il couvre aussi les barres du thème)")
    ancien = ".cs-mf{position:relative;width:100vw;margin-left:calc(50% - 50vw)}"
    if len(refuse(ancien)) != 2:
        echec("contre-épreuve : le contrôle ne reconnaît pas l'ancien CSS pleine largeur")
    else:
        print("  ok  contre-épreuve : l'ancien CSS pleine largeur est bien refusé")


PURGE_HARNESS = r"""<?php
define('ABSPATH', 1);
define('HOUR_IN_SECONDS', 3600);
define('MINUTE_IN_SECONDS', 60);

$GLOBALS['h'] = array();          // crochets enregistrés
$GLOBALS['ecrites'] = array();    // clés que les LECTEURS écrivent
$GLOBALS['purgees'] = array();    // clés que la purge vide
$GLOBALS['types'] = array(10 => 'tribe_events', 20 => 'page', 30 => 'post');

function add_action($tag, $cb, $prio = 10, $n = 1) { $GLOBALS['h'][$tag][] = array($cb, $n); }
function add_filter($tag, $cb, $prio = 10, $n = 1) {}
function add_shortcode($tag, $cb) {}
function do_action($tag) {
    $args = array_slice(func_get_args(), 1);
    if (empty($GLOBALS['h'][$tag])) { return; }
    foreach ($GLOBALS['h'][$tag] as $c) { call_user_func_array($c[0], array_slice($args, 0, $c[1])); }
}
function get_post_type($p) { $id = is_object($p) ? $p->ID : (int) $p; return isset($GLOBALS['types'][$id]) ? $GLOBALS['types'][$id] : false; }
function delete_transient($k) { $GLOBALS['purgees'][] = $k; return true; }
function get_transient($k) { return false; }
function set_transient($k, $v, $t) { $GLOBALS['ecrites'][] = $k; return true; }
function current_time($f) { return $f === 'Y-m-d' ? '2026-09-24' : '2026-09-24 10:00:00'; }
function esc_html($s) { return htmlspecialchars($s, ENT_QUOTES); }
function wp_reset_postdata() {}
class WP_Query { public $posts = array(); public function __construct($a) {} }
function post($id) { $o = new stdClass(); $o->ID = $id; $o->post_type = $GLOBALS['types'][$id]; return $o; }
function sortie() {
    echo json_encode(array('ecrites' => array_values(array_unique($GLOBALS['ecrites'])),
                           'purgees' => $GLOBALS['purgees']));
}

// Même ordre de chargement que WordPress : les mu-plugins par ordre alphabétique.
require __DIR__ . '/cs-liste-moment.php';
require __DIR__ . '/cs-moment-fort.php';

// Les clés RÉELLEMENT écrites par les deux lecteurs, avec le raccourci tel qu'il est
// écrit dans les pages (et l'italien dans les DEUX ordres : la clé ne doit pas en dépendre).
foreach (cs_moments_forts() as $m) {
    foreach ($m['volets'] as $v) { foreach ($v['terr'] as $lang => $t) { cs_mf_evenements($m, $v, $lang); } }
}
cs_moment_liste_fiches('journees-europeennes-du-patrimoine', 'fr');
cs_moment_liste_fiches('giornate-europee-del-patrimonio, giornate-europee-del-patrimonio-it', 'it');
cs_moment_liste_fiches('giornate-europee-del-patrimonio-it,giornate-europee-del-patrimonio', 'it');
cs_moment_liste_fiches('giornate-europee-del-patrimonio', 'it');

switch ($argv[1]) {
    case 'enregistrement':
        // Plusieurs crochets pour une même fiche : la purge ne doit passer qu'UNE fois.
        do_action('save_post', 10, post(10), true);
        do_action('transition_post_status', 'publish', 'publish', post(10));
        do_action('set_object_terms', 10, array('x'), array(1), 'post_tag', false, array());
        break;
    case 'corbeille':   do_action('transition_post_status', 'trash', 'publish', post(10)); break;
    case 'suppression': do_action('before_delete_post', 10, post(10)); break;
    case 'etiquettes':  do_action('set_object_terms', 10, array('x'), array(1), 'post_tag', false, array()); break;
    case 'page':
        do_action('save_post', 20, post(20), true);
        do_action('transition_post_status', 'publish', 'draft', post(20));
        do_action('set_object_terms', 30, array('x'), array(1), 'post_tag', false, array());
        break;
    case 'autre_taxo':  do_action('set_object_terms', 10, array('x'), array(1), 'tribe_events_cat', false, array()); break;
    case 'sans_shutdown':
        do_action('save_post', 10, post(10), true);
        sortie();
        exit;
}
do_action('shutdown');
sortie();
"""


def test_purge():
    """Une fiche qui change vide les caches de la strate et des pages dédiées.

    Mesuré le 22/09 au soir : douze fiches du dimanche publiées, la colonne du dimanche
    est restée à une ligne jusqu'à l'expiration du cache (une heure).

    Ce qui est vérifié : les clés VIDÉES sont exactement celles que les deux lecteurs
    ÉCRIVENT — relevées en appelant les vrais lecteurs, pas recopiées — et elles sont
    aussi comparées à une liste calculée ici, indépendamment du PHP.
    Contre-épreuves : une page, un article, une autre taxonomie ne vident RIEN ; et rien
    n'est vidé avant la fin de la requête.
    """
    import hashlib
    import json
    php = shutil.which("php")
    if not php:
        print("php absent : le volet « purge » n'est PAS joué (ce n'est pas un succès).")
        return
    tmp = Path(tempfile.mkdtemp())
    shutil.copy(PHP_FILE, tmp / "cs-moment-fort.php")
    shutil.copy(ROOT / "deploy" / "wordpress" / "cs-liste-moment.php", tmp / "cs-liste-moment.php")
    (tmp / "purge.php").write_text(PURGE_HARNESS, encoding="utf-8")

    def jouer(cas):
        r = subprocess.run([php, str(tmp / "purge.php"), cas], capture_output=True, text=True)
        if r.returncode != 0 or not r.stdout.strip().startswith("{"):
            echec("harnais de purge (%s) : %s" % (cas, (r.stderr or r.stdout)[:400]))
            return None
        return json.loads(r.stdout)

    def ml(*slugs_lang):
        return "cs_ml_" + hashlib.md5("|".join(slugs_lang).encode()).hexdigest()

    # Calculées ICI, sans le PHP : le format des clés tel qu'il doit être.
    attendues = {
        "cs_mf_patrimoine_piemont_fr", "cs_mf_patrimoine_piemonte_it",
        "cs_mf_patrimoine_vallee-d-aoste_fr", "cs_mf_patrimoine_valle-d-aosta_it",
        ml("journees-europeennes-du-patrimoine", "fr"),
        ml("giornate-europee-del-patrimonio", "giornate-europee-del-patrimonio-it", "it"),
        ml("giornate-europee-del-patrimonio", "it"),
        ml("giornate-europee-del-patrimonio-it", "it"),
    }

    for cas in ("enregistrement", "corbeille", "suppression", "etiquettes"):
        r = jouer(cas)
        if r is None:
            continue
        purgees, ecrites = r["purgees"], set(r["ecrites"])
        oubliees = ecrites - set(purgees)
        if oubliees:
            echec("%s : clés écrites par les lecteurs mais PAS vidées : %s" % (cas, sorted(oubliees)))
        elif set(purgees) != attendues:
            echec("%s : clés vidées %s, attendues %s" % (cas, sorted(purgees), sorted(attendues)))
        elif len(purgees) != len(set(purgees)):
            echec("%s : la purge est passée plusieurs fois (%d suppressions pour %d clés)"
                  % (cas, len(purgees), len(set(purgees))))
        else:
            print("  ok  %-14s : %d clés vidées, dont les %d écrites par les lecteurs"
                  % (cas, len(purgees), len(ecrites)))

    # La clé de la liste italienne ne dépend pas de l'ordre des slugs dans la page :
    # les deux ordres doivent avoir écrit la MÊME clé (une seule, pas deux).
    r = jouer("enregistrement")
    if r is not None:
        trie = ml("giornate-europee-del-patrimonio", "giornate-europee-del-patrimonio-it", "it")
        inverse = ml("giornate-europee-del-patrimonio-it", "giornate-europee-del-patrimonio", "it")
        vues = [k for k in r["ecrites"] if k in (trie, inverse)]
        if vues != [trie]:
            echec("clé de liste : les deux ordres de slugs donnent %s, attendu la seule clé triée" % vues)
        else:
            print("  ok  clé de liste : les deux ordres de slugs donnent la même clé")

    # CONTRE-ÉPREUVES : rien ne doit être vidé.
    for cas, pourquoi in (("page", "une page et un article enregistrés"),
                          ("autre_taxo", "une fiche dont seule la catégorie change"),
                          ("sans_shutdown", "une fiche enregistrée, AVANT la fin de la requête")):
        r = jouer(cas)
        if r is None:
            continue
        if r["purgees"]:
            echec("contre-épreuve (%s) : %d clé(s) vidée(s), il n'en fallait aucune"
                  % (pourquoi, len(r["purgees"])))
        elif not r["ecrites"]:
            echec("contre-épreuve (%s) : les lecteurs n'ont rien écrit, le test ne prouve rien" % pourquoi)
        else:
            print("  ok  contre-épreuve : %s => rien de vidé" % pourquoi)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    print("— contrastes de la palette")
    test_contrastes()
    print("— rendu")
    test_rendu()
    print("— territoire canonique")
    test_territoire_canonique()
    print("— surtitre insécable")
    test_surtitre_insecable()
    print("— bande contenue dans la colonne")
    test_bande_contenue()
    print("— purge des caches")
    test_purge()
    print(("%d echec(s)" % echecs) if echecs else "tout est vert")
    sys.exit(1 if echecs else 0)
