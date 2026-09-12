<?php
/*
Plugin Name: Agenda Sabauda — Notifications Slack côté WordPress
Description: Point d'appel UNIQUE pour tout ce que WordPress poste sur Slack :
  formulaires publics (« Proposer un événement » #24, « Annoncer » #28,
  « Newsletter » #52), audits quotidiens (#130 doctrine, #135 et #136
  garde-fous, #138 fraîcheur des guides) et cs-completude.php.

  ── POURQUOI CE FICHIER A CHANGÉ LE 2026-08-17 ──────────────────────────────
  Franck : « j'ai trop de messages dans slack. les messages ne doivent arriver
  uniquement dans la chaîne #agendasabauda et non pas dans formulaire. »

  Deux défauts, et le premier était l'INVERSE de ce que la version précédente
  croyait faire. Elle réservait volontairement son webhook aux formulaires
  publics — « une soumission de spam ou un essai ne doit jamais polluer le
  canal opérationnel du pipeline » — et c'était juste. Mais six autres
  appelants OPÉRATIONNELS (les quatre audits quotidiens et cs-completude) ont
  ensuite réutilisé cette même fonction, faute d'une autre : le canal réservé
  au bruit du public est devenu celui où atterrissaient les seuls messages qui
  demandaient une décision. Le 2026-08-17, #formulaire contenait cinq rapports
  d'audit et un refus de publication (fiche #7686, source officielle
  manquante) ; personne ne lit ce canal.

  Second défaut, celui du NOMBRE : quatre audits × un message chacun, plus les
  formulaires, tous les jours. Les remettre tels quels dans #agendasabauda
  aurait aggravé le problème dans le canal que Franck lit vraiment — il y
  reçoit déjà les deux récapitulatifs du pipeline. C'est exactement la faute
  corrigée le 2026-08-13 côté VPS (« il m'en faut un ou deux, mais c'est
  tout »), et la réponse est la même : une BOÎTE DU JOUR, vidée en un seul
  message. Ce fichier est donc le pendant WordPress de utils/slack.py.

  ── CE QUI EN DÉCOULE ───────────────────────────────────────────────────────
  • un seul canal, et SANS nouveau secret. Franck, le 2026-08-17 : « Mais tu
    publies déjà dans ce canal. Pourquoi je devrais te donner de nouveau le
    webhook ? » Il a raison : le webhook de #agendasabauda vit dans le `.env`
    du VPS, que le pipeline utilise chaque jour. Le dupliquer dans la base
    WordPress ferait deux copies d'un même secret à révoquer, pour un
    problème qui n'est QUE d'acheminement. WordPress ne poste donc plus rien
    de lui-même : il TIENT ses rapports dans la boîte, et le récapitulatif de
    11h45 du VPS vient les chercher (route cs/v1/slack-boite ci-dessous, même
    authentification X-CS-Auth que la publication quotidienne). Les rapports
    WordPress arrivent ainsi DANS le message du pipeline — un canal, un
    message, aucun secret déplacé ;
  • l'option `cs_slack_webhook_url` reste lue si elle est renseignée un jour,
    et `cs_slack_webhook_url_formulaires` sert de repli — mais uniquement
    quand PERSONNE n'est venu vider la boîte depuis 26 h (voir plus bas) ;
  • un seul message par jour : cs_slack_notify() RANGE, un cron quotidien
    vide la boîte. `$urgent = true` court-circuite (rien ne s'en sert
    aujourd'hui : c'est la porte de sortie si un contrôle futur ne peut pas
    attendre) ;
  • les sept appelants existants n'ont PAS été touchés :
    cs_slack_notify_form() reste leur point d'entrée, avec la même signature
    et le même contrat de retour. Un correctif qui aurait demandé d'éditer
    quatre snippets en base + un mu-plugin, c'est quatre occasions de casser
    le site pour un problème d'acheminement.

  LA BOÎTE N'EST PAS UNE POUBELLE, ET C'EST LE POINT DÉLICAT. Elle attend
  désormais quelqu'un qui vient d'ailleurs : si le VPS s'arrête, si le cron de
  11h45 disparaît, si les identifiants WordPress sont révoqués, alors plus
  personne ne la vide et les rapports dorment — un refus de publication resté
  invisible est exactement ce qu'on corrige aujourd'hui, à l'envers.

  D'où le rouvreur, et il est explicite (règle 3 de CLAUDE.md : tout état qui
  met quelque chose de côté doit avoir quelqu'un qui l'en sorte, et « un humain
  qui tape une commande » n'est pas une réponse) : passé 26 h SANS aucun
  passage du pipeline, WordPress reprend la parole tout seul sur son propre
  webhook — le canal des formulaires si c'est le seul configuré. Un message
  mal rangé se voit ; une boîte silencieuse, non. Le cron quotidien de 11h40
  n'existe que pour ça, et il se TAIT tant que le pipeline fait son travail
  (option `cs_slack_dernier_drain`).

  JAMAIS BLOQUANT : une soumission de formulaire ne doit jamais échouer parce
  que Slack est injoignable ou mal configuré. Toute erreur part dans le
  journal PHP et la fonction rend false.

Configuration : options WordPress `cs_slack_webhook_url` (canal
  #agendasabauda) et, historique, `cs_slack_webhook_url_formulaires`. Jamais
  d'URL en dur dans le code — c'est un secret révocable.

INSTALLATION : déposer dans wp-content/mu-plugins/ (voir
  docs/DEPLOIEMENT_WORDPRESS.md). Rollback : restaurer la version précédente
  depuis git, ou supprimer le fichier — les appelants dégradent proprement.
*/

if (!defined('ABSPATH')) { exit; }

const CS_SLACK_BOITE_OPTION = 'cs_slack_boite_du_jour';
const CS_SLACK_VIDAGE_HOOK  = 'cs_slack_vidage_event';

/** Horodatage du dernier passage du pipeline VPS sur cs/v1/slack-boite.
 *  C'est lui qui décide si WordPress doit se taire ou reprendre la parole. */
const CS_SLACK_DRAIN_OPTION = 'cs_slack_dernier_drain';

/** Heure locale du vidage : juste avant le récapitulatif de 11h45 du pipeline,
 *  pour que la matinée arrive d'un bloc plutôt qu'en deux fois. */
const CS_SLACK_VIDAGE_HEURE = '11:40';

/** Garde-fous d'une boîte que PERSONNE n'aurait vidée (voir l'en-tête). */
const CS_SLACK_BOITE_AGE_MAX = 26 * HOUR_IN_SECONDS;
const CS_SLACK_BOITE_MAX     = 20;

/**
 * Le pipeline VPS est-il venu chercher les rapports récemment ?
 *
 * Tant que la réponse est oui, WordPress se tait : les rapports arrivent dans
 * le récapitulatif de 11h45, sur #agendasabauda, sans qu'aucun webhook Slack
 * n'ait été recopié dans cette base. Si la réponse devient non — VPS arrêté,
 * cron supprimé, mot de passe d'application révoqué — WordPress reprend la
 * parole de lui-même : c'est le rouvreur de la règle 3, et il ne dépend de
 * personne.
 */
function cs_slack_pipeline_actif(): bool {
    $dernier = (int) get_option(CS_SLACK_DRAIN_OPTION, 0);
    return $dernier > 0 && (time() - $dernier) < CS_SLACK_BOITE_AGE_MAX;
}

/**
 * L'URL du webhook, et le nom de l'option qui l'a fournie (pour le journal).
 *
 * @return array{0: string, 1: string}
 */
function cs_slack_webhook(): array {
    $url = trim((string) get_option('cs_slack_webhook_url', ''));
    if ($url !== '') {
        return [$url, 'cs_slack_webhook_url'];
    }
    // Repli historique : le canal des formulaires. Mal rangé, mais pas perdu.
    $url = trim((string) get_option('cs_slack_webhook_url_formulaires', ''));
    return [$url, 'cs_slack_webhook_url_formulaires'];
}

/**
 * Poste MAINTENANT sur Slack. Renvoie true si le message est parti.
 * N'émet jamais d'exception.
 */
function cs_slack_post(string $texte): bool {
    list($url, $origine) = cs_slack_webhook();
    if ($url === '') {
        error_log('[cs-slack] aucun webhook configure (ni cs_slack_webhook_url ni '
            . 'cs_slack_webhook_url_formulaires), notification ignoree : '
            . mb_substr($texte, 0, 80));
        return false;
    }
    if ($origine !== 'cs_slack_webhook_url') {
        error_log('[cs-slack] cs_slack_webhook_url vide — repli sur le canal des '
            . 'formulaires. Renseigner l option pour poster dans #agendasabauda.');
    }
    $reponse = wp_remote_post($url, [
        'timeout' => 8,
        'headers' => ['Content-Type' => 'application/json'],
        'body'    => wp_json_encode(['text' => $texte]),
    ]);
    if (is_wp_error($reponse)) {
        error_log('[cs-slack] envoi impossible : ' . $reponse->get_error_message());
        return false;
    }
    $code = (int) wp_remote_retrieve_response_code($reponse);
    if ($code >= 300) {
        error_log('[cs-slack] Slack a repondu ' . $code . ' : '
            . wp_remote_retrieve_body($reponse));
        return false;
    }
    return true;
}

/**
 * Range un message dans la boîte du jour. Renvoie true : le message est PRIS
 * EN CHARGE, pas encore affiché. Si le rangement échoue, on poste tout de
 * suite plutôt que de perdre le message — la boîte ne doit jamais avaler.
 */
function cs_slack_ranger(string $texte): bool {
    $boite = get_option(CS_SLACK_BOITE_OPTION, []);
    if (!is_array($boite)) { $boite = []; }
    // `id` et pas seulement `at` : voir cs_slack_boite_purger(). Deux rapports
    // peuvent naître dans la même seconde, et un horodatage ne les distingue
    // alors plus — la fixture du 2026-08-17 l'a montré en effaçant un message
    // jamais lu.
    $boite[] = ['id' => wp_generate_uuid4(), 'at' => time(), 'texte' => $texte];
    $ok = update_option(CS_SLACK_BOITE_OPTION, $boite, false);
    if (!$ok && get_option(CS_SLACK_BOITE_OPTION, null) === null) {
        error_log('[cs-slack] boite du jour non enregistree — envoi immediat');
        return cs_slack_post($texte);
    }
    // La boîte se vide d'elle-même si PERSONNE ne l'a vidée — ni le pipeline
    // (route cs/v1/slack-boite), ni le cron quotidien.
    $plus_ancien = (int) ($boite[0]['at'] ?? time());
    if (!cs_slack_pipeline_actif()
        && (count($boite) > CS_SLACK_BOITE_MAX
            || (time() - $plus_ancien) > CS_SLACK_BOITE_AGE_MAX)) {
        error_log('[cs-slack] boite du jour abandonnee ('
            . count($boite) . ' message(s), le plus ancien de '
            . round((time() - $plus_ancien) / HOUR_IN_SECONDS) . ' h, aucun passage '
            . 'du pipeline) — vidage force');
        cs_slack_vider_boite(true);
    }
    return true;
}

/**
 * Poste EN UN SEUL MESSAGE tout ce que la boîte contient, et la vide.
 *
 * La boîte est retirée AVANT l'envoi : un audit qui écrirait pendant le vidage
 * alimente une boîte neuve au lieu de voir sa ligne disparaître. Si l'envoi
 * échoue, le contenu est remis en place — le prochain vidage réessaiera.
 *
 * @return array{0: int, 1: bool} (nombre de messages regroupés, envoyé ou non)
 */
function cs_slack_vider_boite(bool $force = false): array {
    $boite = get_option(CS_SLACK_BOITE_OPTION, []);
    if (!is_array($boite) || !$boite) {
        return [0, false];
    }
    // Le pipeline vient les chercher : WordPress ne double pas le message.
    if (!$force && cs_slack_pipeline_actif()) {
        return [count($boite), false];
    }
    update_option(CS_SLACK_BOITE_OPTION, [], false);

    $morceaux = [];
    foreach ($boite as $ligne) {
        $heure = wp_date('H:i', (int) ($ligne['at'] ?? time()));
        $morceaux[] = '───── ' . $heure . chr(10) . (string) ($ligne['texte'] ?? '');
    }
    // Le nombre est TOUJOURS affiché : sans lui, un récapitulatif de quatre
    // audits et un récapitulatif d'un seul ont exactement la même tête, et on
    // ne sait pas si la journée a été calme ou si les crons se sont arrêtés.
    $corps = ':classical_building: *WordPress — ' . count($boite) . ' rapport(s)*'
        . chr(10) . chr(10) . implode(chr(10) . chr(10), $morceaux);
    // Slack coupe à 40 000 caractères : on tronque nous-mêmes et on le dit.
    if (mb_strlen($corps) > 38000) {
        $corps = mb_substr($corps, 0, 38000)
            . chr(10) . chr(10) . '… (tronque — voir les options cs_* en base)';
    }

    $ok = cs_slack_post($corps);
    if (!$ok) {
        $actuelle = get_option(CS_SLACK_BOITE_OPTION, []);
        if (!is_array($actuelle)) { $actuelle = []; }
        update_option(CS_SLACK_BOITE_OPTION, array_merge($boite, $actuelle), false);
    }
    return [count($boite), $ok];
}

/**
 * LE point d'entrée. Range le message dans la boîte du jour (un message Slack
 * par jour) ; `$urgent = true` poste immédiatement.
 */
function cs_slack_notify(string $texte, bool $urgent = false): bool {
    if ($urgent) {
        return cs_slack_post($texte);
    }
    return cs_slack_ranger($texte);
}

/**
 * Nom historique, conservé tel quel : les sept appelants (Code Snippets #24,
 * #28, #52, #130, #135, #136, #138 et cs-completude.php) l'utilisent, et un
 * problème d'ACHEMINEMENT ne justifie pas de rouvrir sept fichiers.
 * Même signature, même contrat de retour qu'avant le 2026-08-17.
 */
function cs_slack_notify_form(string $texte): bool {
    return cs_slack_notify($texte);
}

/* ══ LA ROUTE QUE LE PIPELINE VIENT INTERROGER ═══════════════════════════════
 *
 * GET    /?rest_route=/cs/v1/slack-boite         → ce qui attend
 * DELETE /?rest_route=/cs/v1/slack-boite&ids=…   → retire ce qui est parti
 *
 * `ids` est la liste (séparée par des virgules) des rapports que l'appelant a
 * réellement pris en charge, et elle est obligatoire : on ne retire QUE ceux-là.
 *
 * CE FUT D'ABORD UNE BORNE D'HORODATAGE (`jusqu_a`), et la fixture du
 * 2026-08-17 l'a démolie à la première épreuve : un rapport écrit APRÈS le GET
 * mais dans la MÊME SECONDE que le dernier message lu tombait sous la borne
 * (`at <= jusqu_a`) et disparaissait sans avoir jamais été envoyé. Les
 * horodatages WordPress sont à la seconde ; quatre audits déclenchés par le
 * même passage de cron naissent régulièrement dans la même seconde. Le défaut
 * était donc exactement celui que la borne prétendait empêcher — un rapport
 * perdu en silence. D'où un identifiant par message, qui ne dépend d'aucune
 * horloge.
 *
 * Le GET vaut PREUVE DE VIE, pas seulement le DELETE : les jours où la boîte
 * est vide, le pipeline n'a rien à supprimer, et sans cette marque WordPress
 * le croirait mort au bout de 26 h et reprendrait la parole dans le mauvais
 * canal — précisément le défaut du jour.
 *
 * Authentification : celle qui sert déjà à la publication quotidienne
 * (cs-rest-auth.php, en-tête X-CS-Auth, ou Application Password). La capacité
 * exigée est `edit_posts` : ces rapports nomment des fiches non publiées.
 */
function cs_slack_boite_permission(): bool {
    return current_user_can('edit_posts');
}

function cs_slack_boite_lire(): WP_REST_Response {
    update_option(CS_SLACK_DRAIN_OPTION, time(), false);
    $boite = get_option(CS_SLACK_BOITE_OPTION, []);
    if (!is_array($boite)) { $boite = []; }
    // Rattrapage : les messages rangés avant l'ajout des identifiants n'en ont
    // pas. On leur en donne un et on l'enregistre, sinon ils ne pourraient
    // jamais être retirés et reviendraient dans chaque récapitulatif.
    $complete = false;
    foreach ($boite as $i => $ligne) {
        if (empty($ligne['id'])) {
            $boite[$i]['id'] = wp_generate_uuid4();
            $complete = true;
        }
    }
    if ($complete) {
        update_option(CS_SLACK_BOITE_OPTION, $boite, false);
    }
    $messages = [];
    foreach ($boite as $ligne) {
        $at = (int) ($ligne['at'] ?? 0);
        $messages[] = [
            'id'    => (string) $ligne['id'],
            'at'    => $at,
            'heure' => $at ? wp_date('H:i', $at) : '',
            'texte' => (string) ($ligne['texte'] ?? ''),
        ];
    }
    return new WP_REST_Response([
        'count'    => count($messages),
        'messages' => $messages,
    ], 200);
}

function cs_slack_boite_purger(WP_REST_Request $req): WP_REST_Response {
    update_option(CS_SLACK_DRAIN_OPTION, time(), false);
    $brut = $req->get_param('ids');
    $ids = is_array($brut) ? $brut : explode(',', (string) $brut);
    $ids = array_filter(array_map('trim', $ids));
    if (!$ids) {
        return new WP_REST_Response(['supprimes' => 0, 'restants' => null,
            'erreur' => 'aucun identifiant fourni'], 400);
    }
    $boite = get_option(CS_SLACK_BOITE_OPTION, []);
    if (!is_array($boite)) { $boite = []; }
    $restants = [];
    foreach ($boite as $ligne) {
        if (!in_array((string) ($ligne['id'] ?? ''), $ids, true)) { $restants[] = $ligne; }
    }
    update_option(CS_SLACK_BOITE_OPTION, $restants, false);
    return new WP_REST_Response([
        'supprimes' => count($boite) - count($restants),
        'restants'  => count($restants),
    ], 200);
}

add_action('rest_api_init', function (): void {
    register_rest_route('cs/v1', '/slack-boite', [
        [
            'methods'             => 'GET',
            'callback'            => 'cs_slack_boite_lire',
            'permission_callback' => 'cs_slack_boite_permission',
        ],
        [
            'methods'             => 'DELETE',
            'callback'            => 'cs_slack_boite_purger',
            'permission_callback' => 'cs_slack_boite_permission',
            'args'                => [
                'ids' => [
                    'required'          => true,
                    'validate_callback' => static function ($v) {
                        return is_array($v) ? (bool) $v : trim((string) $v) !== '';
                    },
                ],
            ],
        ],
    ]);
});

add_action(CS_SLACK_VIDAGE_HOOK, 'cs_slack_vider_boite');

/**
 * Programme le vidage quotidien à l'heure locale du site. Appelé à chaque
 * chargement (un mu-plugin n'a pas de hook d'activation) : wp_next_scheduled
 * rend l'opération idempotente.
 */
function cs_slack_programmer_vidage(): void {
    if (wp_next_scheduled(CS_SLACK_VIDAGE_HOOK)) {
        return;
    }
    try {
        $tz  = wp_timezone();
        $now = new DateTimeImmutable('now', $tz);
        $cible = new DateTimeImmutable(
            $now->format('Y-m-d') . ' ' . CS_SLACK_VIDAGE_HEURE, $tz);
        if ($cible <= $now) {
            $cible = $cible->modify('+1 day');
        }
        wp_schedule_event($cible->getTimestamp(), 'daily', CS_SLACK_VIDAGE_HOOK);
    } catch (Exception $e) {
        error_log('[cs-slack] vidage non programme : ' . $e->getMessage());
    }
}
add_action('init', 'cs_slack_programmer_vidage');
