/**
 * CS - Lien Instagram, demande Franck 2026-07-23, restreint 2026-07-24.
 * Seul Savoie FR a un compte reel. Decision explicite : PAS de repli vers ce
 * compte quand on visite un autre territoire ou la version IT -- ca laisserait
 * croire a un compte propre a ce territoire alors qu'il n'existe pas. Le bouton
 * Instagram ne s'affiche donc QUE quand le territoire actif est Savoie ET la
 * langue est FR ; sinon il est retire entierement (pas de lien mort visible).
 * Il suffira de completer $map ci-dessous quand les autres comptes existeront
 * pour qu'ils s'affichent aussi, chacun dans son propre territoire/langue.
 */
if (!function_exists('cs_instagram_territoire_map')) {
    function cs_instagram_territoire_map() {
        return array(
            'savoie'  => array('url' => 'https://www.instagram.com/agendasabauda.savoie/', 'label' => 'Savoie'),
            'piemont' => array('url' => '', 'label' => 'Piémont'), // a completer
            'vda'     => array('url' => '', 'label' => "Vallée d'Aoste"), // a completer
            'nice'    => array('url' => '', 'label' => 'Nice'), // a completer
        );
    }
}

if (!function_exists('cs_instagram_account')) {
    /** Renvoie le compte Instagram pour un territoire+langue precis, ou null si
     * aucun compte reel ne correspond (pas de repli implicite -- decision
     * explicite du 2026-07-24). $lang_override permet de forcer la langue
     * (utile sur une fiche evenement, dont la langue est celle du post, pas
     * forcement celle du visiteur courant). */
    function cs_instagram_account($canon_override = null, $lang_override = null) {
        $map = cs_instagram_territoire_map();
        $canon = $canon_override ?: (function_exists('cs_territoire_actif') ? cs_territoire_actif() : null);
        $lang = $lang_override ?: (function_exists('pll_current_language') ? pll_current_language() : 'fr');
        if ($canon === 'savoie' && $lang === 'fr' && !empty($map['savoie']['url'])) {
            return $map['savoie'];
        }
        if ($canon && !empty($map[$canon]['url'])) {
            return $map[$canon];
        }
        return null;
    }
}

/** Retrouve la cle canonique (savoie|piemont|vda|nice) du territoire d'UN
 * evenement precis, via sa taxonomie (pas le cookie/GET site-wide) -- utilise
 * sur les fiches evenement, ou le territoire pertinent est celui de la fiche. */
if (!function_exists('cs_instagram_canon_for_event')) {
    function cs_instagram_canon_for_event($event_id) {
        if (!function_exists('cs_terr_canon_data')) { return null; }
        $terms = get_the_terms($event_id, 'territoire');
        if (!$terms || is_wp_error($terms)) { return null; }
        $term_ids = wp_list_pluck($terms, 'term_id');
        foreach (cs_terr_canon_data() as $key => $d) {
            if (in_array((int) $d['fr_term'], $term_ids, true) || in_array((int) $d['it_term'], $term_ids, true)) {
                return $key;
            }
        }
        return null;
    }
}

add_filter('the_content', function ($content) {
    $home_ids = function_exists('cs_agenda_home_page_ids') ? cs_agenda_home_page_ids() : array(928);
    if (!is_page($home_ids)) {
        return $content;
    }
    $acc = cs_instagram_account();
    // 2026-09-29 : aucun compte italien n'existe. cs_instagram_account() rend pourtant
    // le compte Savoie sur la home IT quand le territoire actif est « savoie » (second
    // test de la fonction), et le remplacement ci-dessous, écrit pour le libellé
    // français, ne trouve rien : le bouton restait en href="#". Hors FR, on retire.
    if ($acc && function_exists('pll_current_language') && pll_current_language() !== 'fr') {
        $acc = null;
    }

    if (!$acc) {
        // Pas de compte pour ce territoire/langue -> retire le bouton entierement
        // (pas de lien mort, pas de repli trompeur vers un autre compte).
        $content = preg_replace(
            // « Seguici su » : sur la home IT (1717), le gabarit n°71 a DÉJÀ traduit le
            // libellé (the_content, priorité 1) quand ce filtre passe (priorité 30).
            // Chercher le seul texte français laissait le bouton mort en ligne
            // (constaté le 2026-09-28).
            '/<a href="#"[^>]*>(?:(?!<\/a>).)*?(?:Suivez-nous sur|Seguici su) Instagram(?:(?!<\/a>).)*?<\/a>\s*/s',
            '', $content
        );
        $content = preg_replace(
            '/<a href="#"[^>]*>(?:(?!<\/a>).)*?>Instagram<(?:(?!<\/a>).)*?<\/a>\s*/s',
            '', $content
        );
        return $content;
    }

    $url = esc_url($acc['url']);
    $mobile_label = 'Suivre Agenda Sabauda ' . $acc['label'] . ' sur Instagram';
    $desktop_label = 'Instagram · ' . $acc['label'];

    // remplace les 2 placeholders href="#" juste avant les libelles Instagram
    // (mobile "Suivez-nous sur Instagram" + desktop "Instagram"), sans toucher
    // au lien Facebook voisin (meme motif href="#", non concerne ici).
    $content = preg_replace(
        '/<a href="#"((?:(?!<\/a>).)*?)Suivez-nous sur Instagram/s',
        '<a href="' . $url . '" target="_blank" rel="noopener"$1' . esc_html($mobile_label),
        $content
    );
    $content = preg_replace(
        '/<a href="#"((?:(?!<\/a>).)*?)>Instagram</s',
        '<a href="' . $url . '" target="_blank" rel="noopener"$1>' . esc_html($desktop_label) . '<',
        $content
    );
    return $content;
}, 30);