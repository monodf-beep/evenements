/**
 * CS - Gabarit Accueil unifie (FR/IT).
 * La page FR (928) reste l'unique source de contenu edite ; la version IT
 * (page 1717) est derivee automatiquement a l'affichage via un dictionnaire
 * de traduction $LB (str_replace) applique sur le filtre 'the_content', pour
 * ne plus jamais diverger entre les deux langues.
 *
 * IMPORTANT : la home est rendue par le snippet 29 via un appel MANUEL
 * apply_filters('the_content', $page->post_content) hors de La Boucle
 * WordPress (template_redirect + get_header/get_footer/exit). Cela veut dire
 * in_the_loop() et is_main_query() ne sont JAMAIS vrais dans ce contexte : ne
 * pas s'appuyer dessus comme garde (bug corrige le 2026-07-23, la 1ere
 * version de ce snippet ne s'executait jamais a cause de cette garde).
 * Le filtre ci-dessous ne doit donc verifier QUE is_page(1717).
 *
 * CORRIGE le 2026-08-31 (Franck : « pourquoi j'ai du français dans les pages
 * en italien ? »). Cause reelle, verifiee cle par cle contre le contenu brut
 * de la page 928 (pas supposee) : les CLES du dictionnaire qui contiennent
 * une apostrophe attendaient l'entite HTML `&#039;` (ex. `L&#039;essentiel`),
 * alors que le contenu REEL de la page 928 stocke l'apostrophe en clair (`'`)
 * — `str_replace` ne matche jamais sur une entite qui n'existe pas dans le
 * texte source, donc CES chaines-la (et elles seules) restaient en francais
 * sur la version italienne, silencieusement, sans erreur PHP. Confirme :
 * les cles SANS apostrophe fonctionnaient toutes. 11 des 12 cles a apostrophe
 * corrigees (cote CLE seulement — la VALEUR italienne garde `&#039;`, un
 * navigateur l'affiche identiquement a une apostrophe simple). La 12e
 * (`>Vallée d&#039;Aoste</div>`) reste introuvable meme en clair : contenu de
 * la page 928 probablement modifie depuis — cle laissee en l'etat, a
 * revisiter si un `</div>` de ce type reapparait dans une future edition de
 * la page FR.
 *
 * Note structurelle, pas corrigee ici : ~14 autres cles du dictionnaire
 * (« Aux alentours », « Suivez-nous sur Facebook », les cartons d'actu datés
 * comme « Juillet 2026 : douze expositions... ») ne correspondent plus non
 * plus au contenu actuel de la page 928 — probablement du contenu retire ou
 * réécrit depuis la construction du dictionnaire, pas un bug d'encodage. Un
 * dictionnaire str_replace n'a pas de garde-fou qui signale ces divergences :
 * elles dérivent en silence a chaque edition de la page 928 tant que
 * personne ne recompare. A surveiller.
 */

if (!function_exists('cs_home_lb_map')) {
    function cs_home_lb_map() {
        return array(
            'aria-label="Agenda Sabauda, accueil"' => 'aria-label="Agenda Sabauda, home"',
            'aria-label="Frise des 4 territoires : Turin, Nice, Aoste, Chambéry"' => 'aria-label="Fascia dei 4 territori: Torino, Nizza, Aosta, Chambéry"',
            'aria-label="Ouvrir le menu"' => 'aria-label="Apri il menu"',
            'aria-label="Fermer le menu"' => 'aria-label="Chiudi il menu"',
            'aria-label="Fermer la publicité"' => 'aria-label="Chiudi la pubblicità"',
            '>Quoi faire, où manger · 4 territoires<' => '>Cosa fare, dove mangiare · 4 territori<',
            '<a href="https://agendasabauda.eu/" style="color:inherit;text-decoration:none">FR</a> <span style="color:#C9BFAD;font-weight:400">|</span> <a href="https://agendasabauda.eu/it/" style="color:#C9BFAD;text-decoration:none;font-weight:400">IT</a>' => '<a href="https://agendasabauda.eu/" style="color:#C9BFAD;text-decoration:none;font-weight:400">FR</a> <span style="color:#C9BFAD;font-weight:400">|</span> <span style="color:#C9BFAD">IT</span>',
            ">Savoie · Piémont · Vallée d'Aoste · Nice<" => '>Savoia · Piemonte · Valle d&#039;Aoste · Nizza<',
            'Vous regardez ' => 'Stai guardando ',
            '>les 4 territoires<' => '>i 4 territori<',
            '>Changer de territoire<' => '>Cambia territorio<',
            '>Changer :<' => '>Cambia:<',
            'as_territoire=savoie' => 'as_territoire=savoia',
            'as_territoire=piemont"' => 'as_territoire=piemonte"',
            'as_territoire=vallee-d-aoste' => 'as_territoire=valle-d-aosta',
            'as_territoire=comte-de-nice' => 'as_territoire=contea-di-nizza',
            '>Savoie</a>' => '>Savoia</a>',
            '>Piémont</a>' => '>Piemonte</a>',
            ">Vallée d'Aoste</a>" => '>Valle d&#039;Aosta</a>',
            '>Comté de Nice</a>' => '>Contea di Nizza</a>',
            '>Publicité<' => '>Pubblicità<',
            'placeholder="Rechercher…"' => 'placeholder="Cerca…"',
            'placeholder="Rechercher un événement, une ville…"' => 'placeholder="Cerca un evento, una città…"',
            '>Chercher<' => '>Cerca<',
            '>Ce week-end<' => '>Questo weekend<',
            '>Gastronomie<' => '>Gastronomia<',
            '>Concerts<' => '>Concerti<',
            ">Tout l'agenda<" => '>Tutti gli eventi<',
            '>Chaque vendredi matin<' => '>Ogni venerdì mattina<',
            ">L'essentiel des quatre territoires, dans votre boîte<" => '>L&#039;essenziale dei quattro territori, nella tua casella di posta<',
            '>Le week-end des 4 territoires, dans votre boîte<' => '>Il weekend dei 4 territori, nella tua casella di posta<',
            'placeholder="Votre adresse e-mail"' => 'placeholder="Il tuo indirizzo e-mail"',
            ">S'inscrire<" => '>Iscriviti<',
            ">Recevez l'essentiel des quatre territoires<" => '>Ricevi l&#039;essenziale dei quattro territori<',
            "Inscrivez-vous pour recevoir chaque semaine l'essentiel des quatre territoires." => 'Iscriviti per ricevere ogni settimana l&#039;essenziale dei quattro territori.',
            '>À la une<' => '>In primo piano<',
            'Voir tous les événements du week-end' => 'Vedi tutti gli eventi del weekend',
            '>Ça vaut le déplacement<' => '>Vale il viaggio<',
            '>Les 7 prochains jours<' => '>I prossimi 7 giorni<',
            "Voir tout l'agenda" => 'Vedi tutto il calendario',
            'https://agendasabauda.eu/tout-l-agenda/" style="display:flex;align-items:center;gap:6px' => 'https://agendasabauda.eu/it/eventi/" style="display:flex;align-items:center;gap:6px',
            '>Nouvelles expositions<' => '>Nuove mostre<',
            'Visuel · mosaïque des œuvres' => 'Immagine · mosaico delle opere',
            "Juillet 2026 : douze expositions à ne pas manquer à Turin" => 'Luglio 2026: dodici mostre da non perdere a Torino',
            "Les musées de la ville rouvrent leurs cimaises pour l&rsquo;été, entre grands noms et découvertes." => "I musei della città riaprono le sale per l'estate, tra grandi nomi e scoperte.",
            'Visuel · Savoie ce week-end' => 'Immagine · Savoia questo weekend',
            "Les douze choses à faire en Savoie ce week-end" => 'Dodici cose da fare in Savoia questo weekend',
            "Marchés nocturnes, randonnées d&rsquo;altitude et guinguettes en bord de lac composent le programme du week-end." => "Mercatini notturni, escursioni in quota e locali sul lago compongono il programma del weekend.",
            '>Aux alentours<' => '>Nei dintorni<',
            'https://agendasabauda.eu/type-de-lieu/musee/' => 'https://agendasabauda.eu/type-de-lieu/museo/',
            '>Musées<' => '>Musei<',
            'https://agendasabauda.eu/evenements/categorie/curiosites/' => 'https://agendasabauda.eu/it/evenements/categorie/curiosita/',
            '>Curiosités<' => '>Curiosità<',
            'https://agendasabauda.eu/evenements/categorie/jeune-public-famille/' => 'https://agendasabauda.eu/it/evenements/categorie/per-bambini-famiglia/',
            '>En famille<' => '>In famiglia<',
            '>Suivez-nous sur Instagram<' => '>Seguici su Instagram<',
            '>Suivez-nous sur Facebook<' => '>Seguici su Facebook<',
            '>Vallée d&#039;Aoste</div>' => '>Valle d&#039;Aosta</div>',
            'Stefano Mancuso au Forte di Bard : ce que les plantes savent faire sans cerveau' => 'Stefano Mancuso al Forte di Bard: cosa sanno fare le piante senza cervello',
            "Piémont, Vallée d'Aoste, Nice : voir dans les autres territoires" => "Piemonte, Valle d'Aosta, Nizza: guarda negli altri territori",
            '>Voir dans les autres territoires<' => '>Guarda negli altri territori<',
            '>Nouveautés sur Agenda Sabauda<' => '>Novità su Agenda Sabauda<',
            '>En évidence<' => '>In evidenza<',
            ">L'agenda à venir<" => '>L&#039;agenda in arrivo<',
            ">Tout l'agenda <span" => '>Tutti gli eventi <span',
            "liste \"L'agenda à venir\"" => 'liste "L&#039;agenda in arrivo"',
            '>Faire de la publicité sur Agenda Sabauda<' => '>Fare pubblicità su Agenda Sabauda<',
            '>Nous écrire<' => '>Contattaci<',
        );
    }
}

add_filter('the_content', function ($content) {
    if (!is_page(1717)) {
        return $content;
    }
    $fr = get_post_field('post_content', 928, 'raw');
    $lb = cs_home_lb_map();
    $lb = array_merge($lb, (array) get_option('cs_home_lb_extra', array()));
    return str_replace(array_keys($lb), array_values($lb), $fr);
}, 1);
