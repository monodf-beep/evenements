#!/usr/bin/env python3
"""Fixture de deploy/wordpress/cs-etiquette-langue.php.

Le 22/09 au soir, 22 fiches italiennes des Journées du patrimoine portaient le terme 900
(langue FRANÇAISE pour Polylang) au lieu du 902 italien : en ligne, étiquetées, et
invisibles de la page dédiée et de la strate, qui interrogent en `lang=it`.

Cas joués, sur le VRAI fichier PHP :
  1. fiche it + terme fr traduit      => remplacé par sa traduction italienne ;
  2. fiche it + terme it              => intact (contre-épreuve : pas de réécriture gratuite) ;
  3. fiche fr + terme fr              => intact ;
  4. fiche it + terme fr SANS traduction => gardé (on ne retire jamais une étiquette) ;
  5. autre route que cs/v1/event      => rien ne bouge ;
  6. TÉMOIN ROUGE : le même cas 1 sans le mu-plugin chargé doit laisser le 900 — sinon
     le harnais corrige tout seul et le test ne prouve rien.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHP_FILE = ROOT / "deploy" / "wordpress" / "cs-etiquette-langue.php"
echecs = 0


def echec(msg):
    global echecs
    echecs += 1
    print("ECHEC : " + msg)


HARNESS = r"""<?php
define('ABSPATH', 1);
$cas = json_decode(file_get_contents($argv[1]), true);
$GLOBALS['t'] = $cas['termes'];          // id => array(langue, traductions)
$GLOBALS['post'] = $cas['post'];         // array(id, langue, tags)
$GLOBALS['filtres'] = array();

function add_filter($h, $cb, $p = 10, $n = 1) { $GLOBALS['filtres'][] = $cb; }
function get_post_type($id) { return 'tribe_events'; }
function pll_get_post_language($id) { return $GLOBALS['post']['langue']; }
function pll_get_term_language($tid) { return isset($GLOBALS['t'][$tid]) ? $GLOBALS['t'][$tid][0] : false; }
function pll_get_term($tid, $l) { $tr = isset($GLOBALS['t'][$tid]) ? $GLOBALS['t'][$tid][1] : array(); return isset($tr[$l]) ? $tr[$l] : false; }
function wp_get_object_terms($id, $tax, $a) { return $GLOBALS['post']['tags']; }
function wp_set_object_terms($id, $terms, $tax, $append) { $GLOBALS['post']['tags'] = array_values($terms); return $terms; }
class WP_REST_Response { private $d; function __construct($d) { $this->d = $d; } function get_data() { return $this->d; } }
class Req { private $r; function __construct($r) { $this->r = $r; } function get_route() { return $this->r; } }

if ($cas['charger']) { require __DIR__ . '/cs-etiquette-langue.php'; }
$resp = new WP_REST_Response(array('id' => $GLOBALS['post']['id']));
foreach ($GLOBALS['filtres'] as $cb) { $resp = $cb($resp, null, new Req($cas['route'])); }
echo json_encode($GLOBALS['post']['tags']);
"""

# Les termes réels du site : 898 fr (seul), 900 fr <-> 902 it, et 950 fr sans traduction.
TERMES = {
    "898": ["fr", {"fr": 898}],
    "900": ["fr", {"fr": 900, "it": 902}],
    "902": ["it", {"it": 902, "fr": 900}],
    "950": ["fr", {"fr": 950}],
}


def jouer(tmp, langue, tags, route="/cs/v1/event", charger=True):
    cas = {"termes": TERMES, "post": {"id": 11013, "langue": langue, "tags": tags},
           "route": route, "charger": charger}
    f = tmp / "cas.json"
    f.write_text(json.dumps(cas), encoding="utf-8")
    r = subprocess.run([shutil.which("php"), str(tmp / "harness.php"), str(f)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        echec("harnais PHP : " + (r.stderr or r.stdout)[:400])
        return None
    return json.loads(r.stdout)


def main():
    if not shutil.which("php"):
        print("php absent : fixture NON jouée (ce n'est pas un succès).")
        return 1
    tmp = Path(tempfile.mkdtemp())
    shutil.copy(PHP_FILE, tmp / "cs-etiquette-langue.php")
    (tmp / "harness.php").write_text(HARNESS, encoding="utf-8")

    cas = [
        ("fiche it + terme fr traduit => 902", "it", [900], "/cs/v1/event", True, [902]),
        ("contre-épreuve : fiche it + terme it => intact", "it", [902], "/cs/v1/event", True, [902]),
        ("fiche fr + terme fr => intact", "fr", [898], "/cs/v1/event", True, [898]),
        ("fiche it + terme fr sans traduction => gardé", "it", [950, 900], "/cs/v1/event", True, [950, 902]),
        ("les deux termes d'une paire => un seul, sans doublon", "it", [900, 902], "/cs/v1/event", True, [902]),
        ("autre route => rien ne bouge", "it", [900], "/cs/v1/autre", True, [900]),
        ("TÉMOIN ROUGE : sans le mu-plugin, le 900 reste", "it", [900], "/cs/v1/event", False, [900]),
    ]
    for nom, langue, tags, route, charger, attendu in cas:
        obtenu = jouer(tmp, langue, tags, route, charger)
        if obtenu is None:
            continue
        if obtenu != attendu:
            echec("%s : attendu %s, obtenu %s" % (nom, attendu, obtenu))
        else:
            print("  ok  %s" % nom)
    shutil.rmtree(tmp, ignore_errors=True)
    print(("%d echec(s)" % echecs) if echecs else "tout est vert")
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
