# Prompt Claude dans Chrome — activer Polylang FR/IT (snippet autonome)

Contexte : site WordPress **agendasabauda.eu**, plugin **Code Snippets** installé,
plugin **Polylang** actif avec les langues **Français** et **Italien**. On ajoute UN
NOUVEAU snippet autonome (on ne touche à AUCUN snippet existant, surtout pas
« cs-publish »/l'endpoint cs/v1/event).

## Objectif

Ajouter un snippet PHP qui (1) pose la langue Polylang de chaque événement publié par
le back-office et (2) expose une route REST `cs/v1/link-translations` pour lier les
fiches FR↔IT.

## Étapes

1. Aller dans **wp-admin → Snippets (Code Snippets) → Add New**.
2. Titre du snippet : `Agenda Sabauda — Polylang FR/IT`.
3. Type : **PHP snippet** / « Functions ». Coller EXACTEMENT le code ci-dessous dans la
   zone de code (c'est du PHP SANS la balise `<?php`).
4. Portée : **Run everywhere**.
5. **Save Changes and Activate**.
6. Vérifier qu'aucune erreur PHP ne s'affiche (le snippet reste « Active », pas d'écran
   d'erreur). Si Code Snippets signale une erreur, DÉSACTIVER et me prévenir sans rien
   forcer.

## Vérification

Après activation, ouvrir dans le navigateur :
`https://agendasabauda.eu/wp-json/cs/v1` — la route `/cs/v1/link-translations` doit
apparaître dans la liste des routes (ou au moins ne pas renvoyer 404 sur un POST). Une
requête GET sur la route renverra une erreur « méthode non autorisée » : c'est NORMAL
(la route n'accepte que POST) et prouve qu'elle existe.

## Code à coller (SANS `<?php`)

```php
if (!defined('ABSPATH')) { exit; }

/**
 * (1) LANGUE AU PUSH — s'accroche à la réponse de cs/v1/event et pose la langue
 * Polylang du post créé/mis à jour, d'après le champ « language » du corps JSON.
 */
add_filter('rest_request_after_callbacks', function ($response, $handler, $request) {
    if ($request->get_route() !== '/cs/v1/event') { return $response; }
    if (!function_exists('pll_set_post_language')) { return $response; }
    $data = ($response instanceof WP_REST_Response) ? $response->get_data() : null;
    $pid  = (is_array($data) && !empty($data['id'])) ? (int) $data['id'] : 0;
    $body = $request->get_json_params();
    $lang = (is_array($body) && !empty($body['language']))
        ? sanitize_key((string) $body['language']) : '';
    if ($pid && $lang && get_post_type($pid) === 'tribe_events') {
        pll_set_post_language($pid, $lang);
    }
    return $response;
}, 20, 3);

/**
 * (2) LIAGE DES TRADUCTIONS — route dédiée.
 */
add_action('rest_api_init', function () {
    register_rest_route('cs/v1', '/link-translations', array(
        'methods'             => 'POST',
        'callback'            => 'cs_link_translations',
        'permission_callback' => function () { return current_user_can('edit_posts'); },
    ));
});

function cs_link_translations(WP_REST_Request $req) {
    if (!function_exists('pll_save_post_translations') || !function_exists('pll_set_post_language')) {
        return new WP_Error('no_polylang', 'Polylang inactif.', array('status' => 500));
    }
    $b = $req->get_json_params();
    $links = (is_array($b) && isset($b['translations']) && is_array($b['translations']))
        ? $b['translations'] : array();
    $clean = array();
    foreach ($links as $lang => $pid) {
        $lang = sanitize_key((string) $lang);
        $pid  = (int) $pid;
        if ($lang && $pid && get_post_type($pid) === 'tribe_events') {
            pll_set_post_language($pid, $lang);
            $clean[$lang] = $pid;
        }
    }
    if (count($clean) < 2) {
        return new WP_Error('need_two', 'Au moins deux langues valides requises.',
            array('status' => 400));
    }
    pll_save_post_translations($clean);
    return new WP_REST_Response(array('linked' => $clean), 200);
}
```

## Ce qu'il ne faut PAS faire

- Ne PAS modifier ni supprimer le snippet « cs-publish » (endpoint cs/v1/event) ni
  aucun autre snippet.
- Ne PAS créer/renommer de langues dans Polylang (FR + IT existent déjà).
- Ne PAS toucher aux réglages Polylang, aux permaliens, ni aux pages.
- En cas d'erreur PHP à l'activation : désactiver le snippet et me prévenir (ne rien
  forcer, ne pas bricoler le code).
