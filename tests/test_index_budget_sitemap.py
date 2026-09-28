#!/usr/bin/env python3
"""Fixture de deploy/wordpress/cs-index-budget.php : le SITEMAP et la balise robots posent
la même question avec la même fonction.

Mesuré le 2026-09-28 : les 102 vues « période » retravaillées (texte à elles, exception du
21/09) servaient une balise robots « index » mais étaient ABSENTES du sitemap — le filtre
du sitemap appelait encore cs_ib_est_vue_periode, sans l'exception.

Cas joués sur le VRAI fichier :
  - vue période AVEC texte (≥ 400 caractères)  → reste dans le sitemap, et indexable ;
  - vue période SANS texte (raccourci seul)    → sort du sitemap, et noindex ;
  - hub à la racine                            → jamais touché (contre-épreuve).
Témoin rouge : la version d'avant exclut la vue période avec texte.
"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHP_FILE = ROOT / "deploy" / "wordpress" / "cs-index-budget.php"
echecs = 0

HARNESS = r"""<?php
define('ABSPATH', 1); define('HOUR_IN_SECONDS', 3600);
$GLOBALS['p'] = json_decode(file_get_contents($argv[1]), true);
$GLOBALS['f'] = array();
function add_filter($h, $cb, $pr = 10, $n = 1) { $GLOBALS['f'][$h][] = $cb; }
function add_action($h, $cb, $pr = 10, $n = 1) {}
function is_admin() { return false; }
function get_transient($k) { return false; }
function set_transient($k, $v, $t) { return true; }
function current_time($f) { return '2026-09-28 10:00:00'; }
function get_post_meta($id, $k, $s = false) { return isset($GLOBALS['p'][$id]['meta'][$k]) ? $GLOBALS['p'][$id]['meta'][$k] : ''; }
function wp_get_post_parent_id($id) { return $GLOBALS['p'][$id]['parent']; }
function get_post_field($f, $id) { return $f === 'post_name' ? $GLOBALS['p'][$id]['slug'] : $GLOBALS['p'][$id]['contenu']; }
function get_post_type($id) { return 'page'; }
function wp_strip_all_tags($s) { return strip_tags($s); }
function get_queried_object_id() { return 0; }
class DB { public $posts = 'wp_posts'; public $postmeta = 'wp_postmeta';
  function get_col($sql) { return strpos($sql, "'page'") !== false ? array_map('intval', array_keys($GLOBALS['p'])) : array(); }
  function get_var($sql) { return 0; } function prepare($q) { return $q; } }
$GLOBALS['wpdb'] = new DB();
require __DIR__ . '/cs-index-budget.php';
$exclus = $GLOBALS['f']['wpseo_exclude_from_sitemap_by_post_ids'][0](array());
$idx = array(); foreach (array_keys($GLOBALS['p']) as $id) { $idx[$id] = cs_ib_hors_index((int) $id); }
echo json_encode(array('exclus' => array_values($exclus), 'hors_index' => $idx));
"""

TEXTE = "Que faire ce week-end à Turin : " + "des concerts, des expositions et des marchés. " * 12
PAGES = {
    "10": {"slug": "ce-week-end", "parent": 8016, "meta": {"cs_hub_quand": "weekend"},
           "contenu": "<p>" + TEXTE + "</p>[cs_hub_liste]"},
    "11": {"slug": "ce-week-end", "parent": 8020, "meta": {"cs_hub_quand": "weekend"},
           "contenu": "<!--more-->[cs_hub_liste]"},
    "12": {"slug": "que-faire-a-turin", "parent": 0, "meta": {"cs_hub_quand": "hub"},
           "contenu": "[cs_hub_liste]"},
}


def jouer(php_file):
    tmp = Path(tempfile.mkdtemp())
    shutil.copy(php_file, tmp / "cs-index-budget.php")
    (tmp / "h.php").write_text(HARNESS, encoding="utf-8")
    (tmp / "p.json").write_text(json.dumps(PAGES), encoding="utf-8")
    r = subprocess.run([shutil.which("php"), str(tmp / "h.php"), str(tmp / "p.json")], capture_output=True, text=True)
    shutil.rmtree(tmp, ignore_errors=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr or r.stdout)
    return json.loads(r.stdout)


def verifie(cond, ok, ko):
    global echecs
    print(("  ok  " + ok) if cond else ("ÉCHEC " + ko))
    echecs += 0 if cond else 1


def main(php_file=PHP_FILE):
    if not shutil.which("php"):
        print("php absent : fixture NON jouée (ce n'est pas un succès).")
        return 1
    r = jouer(php_file)
    ex, hi = r["exclus"], {int(k): v for k, v in r["hors_index"].items()}
    verifie(10 not in ex and hi[10] is False,
            "vue période AVEC texte : indexable ET dans le sitemap",
            f"vue période avec texte : exclue du sitemap={10 in ex}, hors index={hi[10]}")
    verifie(11 in ex and hi[11] is True,
            "vue période SANS texte : noindex ET hors du sitemap",
            f"vue période sans texte : exclue={11 in ex}, hors index={hi[11]}")
    verifie(12 not in ex and hi[12] is False,
            "contre-épreuve : le hub n'est ni exclu ni noindex",
            f"hub touché : exclu={12 in ex}, hors index={hi[12]}")
    verifie(all((i in ex) == hi[i] for i in hi),
            "sitemap et balise robots donnent la même réponse pour chaque page",
            "le sitemap et la balise robots divergent")
    print(("%d échec(s)" % echecs) if echecs else "tout est vert")
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else PHP_FILE))
