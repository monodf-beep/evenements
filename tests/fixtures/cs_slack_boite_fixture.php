<?php
/*
Fixture de `deploy/wordpress/cs-slack-formulaires.php` — la boîte du jour côté
WordPress, SANS WordPress : les quelques fonctions utilisées sont bouchonnées
ici, ce qui permet d'éprouver la logique en dehors du site de production.

CE QU'ELLE PROTÈGE, ET POURQUOI ELLE EXISTE. La première version de la route
bornait la purge par un HORODATAGE (`jusqu_a`) : le pipeline annonçait « j'ai
lu jusqu'à telle seconde », WordPress retirait tout ce qui était à cette
seconde ou avant. L'épreuve du 2026-08-17 l'a démolie du premier coup — un
rapport écrit APRÈS la lecture, mais dans la même seconde que le dernier
message lu, était effacé sans avoir jamais été envoyé. Les horodatages
WordPress sont à la seconde, et quatre audits déclenchés par le même passage de
cron naissent régulièrement dans la même seconde : le défaut était donc
exactement celui que la borne prétendait empêcher.

D'où le cas n°3 ci-dessous, écrit dans la même seconde que les autres, et qui
doit PASSER. CLAUDE.md le demande explicitement pour tout portillon : une
fixture qui ne contient que des cas confirmant le design ne prouve rien.

Lancer : php tests/fixtures/cs_slack_boite_fixture.php
   (ou, avec le reste : .venv/bin/python -m tests.test_slack_boite_wordpress)
*/

define('ABSPATH', __DIR__);
define('HOUR_IN_SECONDS', 3600);

$GLOBALS['options'] = [];
$GLOBALS['postes']  = [];   // ce qui serait parti sur Slack
$GLOBALS['uuid']    = 0;

function get_option($nom, $defaut = false) {
    return array_key_exists($nom, $GLOBALS['options']) ? $GLOBALS['options'][$nom] : $defaut;
}
function update_option($nom, $valeur, $autoload = null): bool {
    $GLOBALS['options'][$nom] = $valeur;
    return true;
}
function wp_generate_uuid4(): string { return 'uuid-' . (++$GLOBALS['uuid']); }
function wp_date($format, $ts = null) { return date($format, $ts ?? time()); }
function wp_timezone() { return new DateTimeZone('Europe/Paris'); }
function wp_json_encode($v) { return json_encode($v); }
function wp_remote_post($url, $args = []) { $GLOBALS['postes'][] = $args['body'] ?? ''; return ['response' => ['code' => 200]]; }
function is_wp_error($x): bool { return false; }
function wp_remote_retrieve_response_code($r) { return $r['response']['code']; }
function wp_remote_retrieve_body($r) { return ''; }
function add_action($hook, $cb, $prio = 10, $args = 1) { return true; }
function register_rest_route($ns, $route, $args) { return true; }
function wp_next_scheduled($hook) { return false; }
function wp_schedule_event($ts, $rec, $hook) { return true; }
function current_user_can($cap): bool { return true; }
function wp_list_pluck($liste, $champ) { return array_map(static fn($l) => $l[$champ], $liste); }

class WP_REST_Response {
    public function __construct(private $data, private int $status = 200) {}
    public function get_data() { return $this->data; }
    public function get_status(): int { return $this->status; }
}
class WP_REST_Request {
    private array $params = [];
    public function set_param($k, $v): void { $this->params[$k] = $v; }
    public function get_param($k) { return $this->params[$k] ?? null; }
}

// CS_SLACK_FICHIER permet la CONTRE-ÉPREUVE : on rejoue la même fixture sur une
// version délibérément fautive (la borne d'horodatage d'origine), et elle DOIT
// échouer. Sans ce volet, une fixture qui ne casse jamais passerait au vert sur
// un code faux — la faute de méthode que CLAUDE.md relève trois fois.
require getenv('CS_SLACK_FICHIER') ?: __DIR__ . '/../../deploy/wordpress/cs-slack-formulaires.php';

$echecs = 0;
function verifier(string $libelle, bool $ok, string $detail = ''): void {
    global $echecs;
    if ($ok) { echo "OK    $libelle\n"; return; }
    $echecs++;
    echo "ÉCHEC $libelle" . ($detail ? " — $detail" : '') . "\n";
}

// ── 1. Un rapport est RANGÉ, pas posté ──────────────────────────────────────
cs_slack_notify_form('rapport A');
cs_slack_notify_form('rapport B');
verifier('deux rapports rangés dans la boîte',
    count(get_option('cs_slack_boite_du_jour', [])) === 2);
verifier('rien n’est parti sur Slack', count($GLOBALS['postes']) === 0);

// ── 2. La lecture donne un identifiant par rapport ──────────────────────────
$lu = cs_slack_boite_lire()->get_data();
verifier('la lecture rend les deux rapports', ($lu['count'] ?? 0) === 2);
$ids = wp_list_pluck($lu['messages'], 'id');
verifier('chaque rapport porte un identifiant distinct', count(array_unique($ids)) === 2);
verifier('la lecture vaut preuve de vie du pipeline', cs_slack_pipeline_actif());

// ── 3. LE CAS QUI DOIT PASSER : écrit après la lecture, MÊME SECONDE ────────
// C'est celui que la borne d'horodatage perdait. Il doit survivre à la purge.
cs_slack_notify_form('rapport C, écrit après la lecture');
$boite = get_option('cs_slack_boite_du_jour', []);
verifier('le cas limite est bien dans la même seconde (sinon il ne prouve rien)',
    (int) $boite[1]['at'] === (int) $boite[2]['at'],
    'les rapports B et C n’ont pas le même horodatage');
$req = new WP_REST_Request();
$req->set_param('ids', implode(',', $ids));
$purge = cs_slack_boite_purger($req)->get_data();
verifier('la purge retire les deux rapports lus', ($purge['supprimes'] ?? 0) === 2);
$reste = get_option('cs_slack_boite_du_jour', []);
verifier('le rapport écrit après la lecture SURVIT',
    count($reste) === 1 && $reste[0]['texte'] === 'rapport C, écrit après la lecture',
    'il reste ' . count($reste) . ' rapport(s)');

// ── 4. Une purge ne peut pas être aveugle ───────────────────────────────────
$req = new WP_REST_Request();
$req->set_param('ids', '   ');
verifier('une purge sans identifiant est refusée (400)',
    cs_slack_boite_purger($req)->get_status() === 400);
$req = new WP_REST_Request();
$req->set_param('ids', 'identifiant-inconnu');
verifier('un identifiant inconnu ne supprime rien',
    (cs_slack_boite_purger($req)->get_data()['supprimes'] ?? -1) === 0);

// ── 5. Le cron WordPress se TAIT tant que le pipeline passe ─────────────────
$GLOBALS['postes'] = [];
list($n, $envoye) = cs_slack_vider_boite();
verifier('le cron ne double pas le message du pipeline', $envoye === false);
verifier('la boîte reste intacte pour le pipeline',
    count(get_option('cs_slack_boite_du_jour', [])) === 1);
verifier('rien n’est parti sur Slack', count($GLOBALS['postes']) === 0);

// ── 6. …et il REPREND LA PAROLE si personne ne vient plus ───────────────────
// Le rouvreur de la règle 3 : sans lui, un refus de publication dormirait
// indéfiniment dans une file que plus personne ne vide.
update_option('cs_slack_dernier_drain', time() - 27 * HOUR_IN_SECONDS, false);
verifier('passé 26 h sans passage, le pipeline est considéré mort',
    !cs_slack_pipeline_actif());
$GLOBALS['options']['cs_slack_webhook_url'] = 'https://hooks.slack.com/services/T/B/x';
list($n, $envoye) = cs_slack_vider_boite();
verifier('WordPress reprend la parole tout seul', $envoye === true && $n === 1);
verifier('un seul message pour tout le contenu', count($GLOBALS['postes']) === 1);
verifier('le message dit combien de rapports il porte',
    str_contains($GLOBALS['postes'][0] ?? '', '1 rapport(s)'));
verifier('la boîte est vidée après un envoi réussi',
    count(get_option('cs_slack_boite_du_jour', [])) === 0);

echo $echecs === 0
    ? "\nSUCCÈS — 0 problème(s).\n"
    : "\n$echecs problème(s).\n";
exit($echecs === 0 ? 0 : 1);
