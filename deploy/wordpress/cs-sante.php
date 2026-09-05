<?php
/*
Plugin Name: Agenda Sabauda — Boîte aux lettres de l'état du pipeline
Description: Reçoit du VPS un relevé de santé (files, crons, goulot, crédit API) et le
  garde en base, pour qu'une session Claude puisse LIRE l'état du serveur sans y avoir
  accès et sans qu'aucun secret ne soit dupliqué.

  ── POURQUOI CE FICHIER ─────────────────────────────────────────────────────
  Franck, 2026-08-17 : « j'aimerais que tu sois autonome et que tu n'aies pas
  besoin de moi. » L'inventaire de la journée montrait deux dépendances qui ne
  sont pas des décisions mais des ALLERS-RETOURS : « le crédit API est-il
  rétabli ? », « quel est l'état des files ? », « le déploiement est-il passé ? ».
  Chaque fois, il a collé une sortie de terminal. Or le pipeline SAIT tout cela ;
  il ne l'exposait à personne.

  ── POURQUOI PAR ICI, ET PAS PAR UNE ROUTE DU BACKOFFICE ────────────────────
  Une route sur le backoffice aurait demandé un jeton de plus — donc un secret de
  plus à confier, à stocker et à révoquer. Or le VPS s'authentifie DÉJÀ auprès de
  WordPress tous les jours pour publier (X-CS-Auth / Application Password), et une
  session Claude atteint DÉJÀ WordPress. Ce fichier n'ouvre donc aucun canal
  nouveau : il réutilise le seul qui existe des deux côtés. C'est le même
  raisonnement que le rapatriement des rapports Slack le matin même : ne pas
  dupliquer un secret pour résoudre un problème de transport.

  ── CE QU'IL NE DOIT JAMAIS CONTENIR ────────────────────────────────────────
  Aucun secret, aucune clé, aucune URL de webhook, aucun contenu de `.env`. Le
  relevé est composé champ par champ côté VPS (scripts/publier_sante.py) et sa
  fixture REFUSE tout ce qui ressemble à un jeton. Ce qui est stocké ici est
  lisible par tout compte capable d'éditer : c'est de l'état d'exploitation, pas
  de la configuration.

  ── HISTORIQUE COURT, VOLONTAIREMENT ────────────────────────────────────────
  Sept relevés gardés, pas plus. De quoi voir une tendance sur une semaine — « les
  150 fiches à dater d'hier sont-elles descendues ? » — sans faire grossir
  indéfiniment une option chargée à chaque requête (autoload à `false`).

Routes :
  POST /?rest_route=/cs/v1/sante   → dépose un relevé  (capacité edit_posts)
  GET  /?rest_route=/cs/v1/sante   → rend les relevés   (capacité edit_posts)

INSTALLATION : déposer dans wp-content/mu-plugins/. Rollback : supprimer — le
  script du VPS constate alors un 404 et le dit, sans rien casser.
*/

if (!defined('ABSPATH')) { exit; }

const CS_SANTE_OPTION = 'cs_sante_pipeline';
const CS_SANTE_GARDE  = 7;

function cs_sante_permission(): bool {
    return current_user_can('edit_posts');
}

function cs_sante_deposer(WP_REST_Request $req): WP_REST_Response {
    $releve = $req->get_param('releve');
    if (!is_array($releve) || !$releve) {
        return new WP_REST_Response(['erreur' => 'releve manquant ou vide'], 400);
    }
    // Le VPS date son relevé ; on ajoute NOTRE heure de réception. Les deux servent :
    // un écart entre elles révèle une horloge qui a dérivé, et c'est l'heure du serveur
    // qui décide de ce qui est « passé » (règle 5).
    $releve['recu_a'] = current_time('mysql');
    $histo = get_option(CS_SANTE_OPTION, []);
    if (!is_array($histo)) { $histo = []; }
    $histo[] = $releve;
    if (count($histo) > CS_SANTE_GARDE) {
        $histo = array_slice($histo, -CS_SANTE_GARDE);
    }
    update_option(CS_SANTE_OPTION, $histo, false);
    return new WP_REST_Response(['gardes' => count($histo)], 200);
}

function cs_sante_lire(): WP_REST_Response {
    $histo = get_option(CS_SANTE_OPTION, []);
    if (!is_array($histo)) { $histo = []; }
    return new WP_REST_Response([
        'count'   => count($histo),
        'releves' => $histo,
    ], 200);
}

add_action('rest_api_init', function (): void {
    register_rest_route('cs/v1', '/sante', [
        [
            'methods'             => 'POST',
            'callback'            => 'cs_sante_deposer',
            'permission_callback' => 'cs_sante_permission',
            'args'                => ['releve' => ['required' => true]],
        ],
        [
            'methods'             => 'GET',
            'callback'            => 'cs_sante_lire',
            'permission_callback' => 'cs_sante_permission',
        ],
    ]);
});
