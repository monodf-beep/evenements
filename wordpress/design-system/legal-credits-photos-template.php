<?php
/**
 * "Crédits photos" (page 1702) — rendu complet en PHP (template_redirect),
 * même gabarit simple qu'apropos-template.php / legal-mentions-template.php /
 * legal-confidentialite-template.php : H1 + contenu converti depuis
 * docs/legal/credits_photos.md (FR + IT, trame rédigée par Franck). Largeur
 * max 700px, typographie standard du site.
 *
 * ⚠️ CONTENU PUBLIABLE, contrairement à Mentions légales (1700) et
 * Confidentialité (1701) : le document source ne contient AUCUN placeholder
 * bloquant (pas d'identité légale, hébergeur, DPO... à fournir). Les deux
 * seuls crochets `[…]` du document source étaient :
 *   - `[JJ/MM/AAAA]` / `[GG/MM/AAAA]` — date de dernière mise à jour, remplie
 *     ci-dessous avec la date de mise en ligne (18/07/2026) ;
 *   - `[contact@culturasabauda.eu]` — l'adresse de contact réelle du site
 *     (déjà utilisée en clair partout ailleurs, ex. contact-template.php),
 *     simplement reformatée sans crochets.
 * → page publiée (post_status=publish) une fois vérifiée en live.
 *
 * Réutilise le même sous-ensemble markdown que legal-mentions-template.php /
 * legal-confidentialite-template.php (cs_legal_md_inline()/
 * cs_legal_md_to_html(), guardées par function_exists() pour rester
 * chargeables indépendamment de l'ordre des snippets — les trois copies
 * doivent rester IDENTIQUES, y compris la pré-passe de rattachement des
 * lignes de continuation indentées, sinon laquelle "gagne" au chargement
 * change le rendu). Pas de tableau markdown ici, donc pas besoin de
 * cs_legal_md_table() (spécifique à legal-confidentialite-template.php).
 *
 * Adaptation de contenu : les 2 listes à 3 niveaux de priorité (§1 FR/IT,
 * numérotées "1./2./3." dans le document source) sont converties en liste à
 * puces "- **1. …**" car le convertisseur maison ne gère que "- " (pas de
 * listes ordonnées) — le numéro de priorité est conservé dans le texte en
 * gras. L'exemple de crédit-type "[Auteur]"/"[Autore]" est reformulé sans
 * crochets ("Nom de l'auteur"/"Nome dell'autore") pour ne pas être surligné
 * comme un placeholder à remplir (c'est un exemple de format, pas un champ
 * de cette page). Backticks autour de `alt` remplacés par des guillemets
 * (le convertisseur ne gère pas le code inline).
 *
 * Header/footer de marque déjà injectés site-wide par le snippet #19
 * (site-header-footer.php) — pas recréés ici.
 */

if (!function_exists('cs_legal_md_inline')) {
    function cs_legal_md_inline($text) {
        $text = htmlspecialchars($text, ENT_QUOTES, 'UTF-8');
        // **gras**
        $text = preg_replace('/\*\*(.+?)\*\*/', '<strong>$1</strong>', $text);
        // *italique* (après le gras, pour ne pas manger les ** restants)
        $text = preg_replace('/\*(.+?)\*/', '<em>$1</em>', $text);
        // [placeholders non remplis] — surlignés pour sauter aux yeux en relecture
        $text = preg_replace(
            '/\[([^\]]+)\]/',
            '<mark style="background:#F7D9A0;color:#1D1D1B;padding:0 3px;border-radius:2px;font-style:normal">[$1]</mark>',
            $text
        );
        // URLs nues → liens cliquables
        $text = preg_replace(
            '/(https?:\/\/[^\s<]+)/',
            '<a href="$1" style="color:#18365E;text-decoration:underline">$1</a>',
            $text
        );
        return $text;
    }
}

if (!function_exists('cs_legal_md_to_html')) {
    function cs_legal_md_to_html($md) {
        $p_style = 'margin:0 0 18px;font-family:\'Nunito Sans\',sans-serif;font-size:15px;line-height:1.65;color:#1D1D1B';
        $h2_style = 'margin:36px 0 12px;font-family:\'La Semplicita\',\'Saira Condensed\',sans-serif;font-weight:600;font-size:22px;line-height:1.15;color:#1D1D1B';
        $h3_style = 'margin:24px 0 10px;font-family:\'La Semplicita\',\'Saira Condensed\',sans-serif;font-weight:600;font-size:18px;line-height:1.2;color:#1D1D1B';
        $ul_style = 'margin:0 0 18px;padding-left:20px;font-family:\'Nunito Sans\',sans-serif;font-size:15px;line-height:1.65;color:#1D1D1B';
        $li_style = 'margin:0 0 8px';

        // Pré-passe : rattache les lignes de continuation indentées (item de
        // liste qui déborde sur la ligne suivante, ex. §1/§2 FR/IT du
        // document source) à la ligne logique précédente, avant le parsing.
        // Même correctif que legal-mentions-template.php /
        // legal-confidentialite-template.php, dupliqué ici car chaque
        // snippet définit sa propre copie de la fonction (guardée par
        // function_exists) — ne pas laisser cette copie diverger des autres.
        $raw_lines = explode("\n", $md);
        $lines = [];
        foreach ($raw_lines as $raw_line) {
            if (preg_match('/^\s+\S/', $raw_line) && !empty($lines) && end($lines) !== '') {
                $lines[count($lines) - 1] .= ' ' . trim($raw_line);
            } else {
                $lines[] = rtrim($raw_line);
            }
        }

        $html = '';
        $in_list = false;
        $para_buf = [];

        $flush_para = function () use (&$para_buf, &$html, $p_style) {
            if (!empty($para_buf)) {
                $html .= '<p style="' . $p_style . '">' . cs_legal_md_inline(implode(' ', $para_buf)) . '</p>' . "\n";
                $para_buf = [];
            }
        };
        $close_list = function () use (&$in_list, &$html) {
            if ($in_list) {
                $html .= '</ul>' . "\n";
                $in_list = false;
            }
        };

        foreach ($lines as $line) {
            $line = rtrim($line);

            if ($line === '') {
                $flush_para();
                $close_list();
                continue;
            }
            if (preg_match('/^###\s+(.*)$/', $line, $m)) {
                $flush_para();
                $close_list();
                $html .= '<h3 style="' . $h3_style . '">' . cs_legal_md_inline($m[1]) . '</h3>' . "\n";
                continue;
            }
            if (preg_match('/^##\s+(.*)$/', $line, $m)) {
                $flush_para();
                $close_list();
                $html .= '<h2 style="' . $h2_style . '">' . cs_legal_md_inline($m[1]) . '</h2>' . "\n";
                continue;
            }
            if (preg_match('/^-\s+(.*)$/', $line, $m)) {
                $flush_para();
                if (!$in_list) {
                    $html .= '<ul style="' . $ul_style . '">' . "\n";
                    $in_list = true;
                }
                $html .= '<li style="' . $li_style . '">' . cs_legal_md_inline($m[1]) . '</li>' . "\n";
                continue;
            }

            // Paragraphe (y compris les lignes tout-italique type "*Dernière mise à jour...*")
            $para_buf[] = $line;
        }
        $flush_para();
        $close_list();

        return $html;
    }
}

add_action('template_redirect', function () {
    if (is_admin() || !is_page(1702)) {
        return;
    }

    // --- FR : sections 1 à 5 (le H1 "# 🇫🇷 Politique de crédits photos" du
    // document source est rendu séparément ci-dessous, pas via le convertisseur) ---
    $md_fr = <<<'MD'
*Dernière mise à jour : 18/07/2026*

Agenda Sabauda (https://agendasabauda.eu), édité par **Cultura Sabauda**, s'engage à illustrer les
événements dans le **respect du droit d'auteur** et à créditer chaque image selon son origine.
Cette page explique d'où viennent nos images, comment nous les créditons, et comment un ayant droit
peut demander un retrait.

## 1. Origine des images

Par ordre de priorité, une fiche événement est illustrée par :

- **1. Les visuels officiels de l'organisateur.** Les photographies et affiches fournies par le lieu,
  l'organisateur ou l'office de tourisme, dans le cadre d'un dossier de presse ou d'un flux
  officiel, avec les droits d'usage correspondants. C'est notre source privilégiée.
- **2. Les images libres de Wikimedia Commons.** À défaut de visuel officiel, nous pouvons utiliser
  des images sous **licence libre** (Creative Commons — CC0, CC BY, CC BY-SA…) issues de
  Wikimedia Commons, notamment pour illustrer un lieu ou un monument. Ces images sont **créditées
  avec le nom de l'auteur et la licence**, conformément aux conditions de réutilisation.
- **3. Les bannières de marque par territoire.** En dernier recours, lorsqu'aucune image officielle
  ni libre n'est disponible, la fiche affiche un **visuel de marque neutre** propre au territoire
  ou à la catégorie, produit par Agenda Sabauda. Aucun crédit tiers n'est alors nécessaire.

## 2. Ce que nous n'utilisons jamais

- **Aucune image servie par un CDN de presse ou d'agrégateur.** Nous excluons par principe les
  images provenant des serveurs d'images de médias de presse et d'agrégateurs (liste technique de
  domaines bloqués maintenue par l'éditeur). La veille presse sert à **détecter** des événements,
  jamais à en **reprendre les images**.
- Aucune image dont nous ne pouvons établir l'origine et les droits.

## 3. Notre engagement de crédit

- Toute image sous licence libre est accompagnée de son **crédit** : auteur, source et licence
  (par ex. *« Photo : Nom de l'auteur — Wikimedia Commons — CC BY-SA 4.0 »*), avec lien lorsque la
  licence l'exige.
- Les visuels officiels sont attribués à leur **source** (lieu, organisateur) quand celle-ci le
  demande ou le justifie.
- Le texte alternatif (attribut « alt ») décrit l'image de façon factuelle (nom de l'événement,
  lieu, ville).

## 4. Procédure de retrait

Vous êtes l'auteur ou le titulaire des droits d'une image, et vous estimez qu'elle est utilisée à
tort, ou vous souhaitez qu'elle soit retirée ou mieux créditée ? Écrivez-nous :

- **Adresse :** **contact@culturasabauda.eu**
- **Objet à indiquer :** « Crédits photos — demande de retrait / correction »
- **À préciser :** l'URL de la page où figure l'image, une description ou capture de l'image
  concernée, et votre qualité (auteur, ayant droit, mandataire).

Nous nous engageons à examiner votre demande **rapidement** et, en cas de doute légitime sur les
droits, à **retirer ou corriger le crédit de l'image dans un délai raisonnable**, sans que cela
préjuge d'un accord ultérieur.

## 5. Signaler une erreur de crédit

Une erreur d'attribution (mauvais auteur, licence inexacte) peut nous être signalée à la même
adresse. Nous corrigeons volontiers toute inexactitude de bonne foi.
MD;

    // --- IT : sections 1 à 5 ---
    $md_it = <<<'MD'
*Ultimo aggiornamento: 18/07/2026*

Agenda Sabauda (https://agendasabauda.eu), edito da **Cultura Sabauda**, si impegna a illustrare
gli eventi nel **rispetto del diritto d'autore** e a citare ogni immagine in base alla sua origine.
Questa pagina spiega da dove provengono le nostre immagini, come le accreditiamo e come un avente
diritto può chiederne la rimozione.

## 1. Origine delle immagini

In ordine di priorità, una scheda evento è illustrata da:

- **1. I materiali visivi ufficiali dell'organizzatore.** Le fotografie e le locandine fornite dal
  luogo, dall'organizzatore o dall'ente del turismo, nell'ambito di una cartella stampa o di un
  flusso ufficiale, con i relativi diritti d'uso. È la nostra fonte privilegiata.
- **2. Le immagini libere di Wikimedia Commons.** In mancanza di un materiale ufficiale, possiamo
  utilizzare immagini con **licenza libera** (Creative Commons — CC0, CC BY, CC BY-SA…)
  provenienti da Wikimedia Commons, in particolare per illustrare un luogo o un monumento. Queste
  immagini sono **accreditate con il nome dell'autore e la licenza**, in conformità alle
  condizioni di riutilizzo.
- **3. I banner di marca per territorio.** Come ultima risorsa, quando non è disponibile alcuna
  immagine ufficiale né libera, la scheda mostra un **materiale visivo neutro** proprio del
  territorio o della categoria, prodotto da Agenda Sabauda. In tal caso non è necessario alcun
  credito a terzi.

## 2. Ciò che non utilizziamo mai

- **Nessuna immagine servita da un CDN di stampa o di aggregatori.** Escludiamo per principio le
  immagini provenienti dai server di immagini di testate giornalistiche e aggregatori (elenco
  tecnico di domini bloccati mantenuto dall'editore). Il monitoraggio della stampa serve a
  **individuare** gli eventi, mai a **riprenderne le immagini**.
- Nessuna immagine di cui non possiamo stabilire origine e diritti.

## 3. Il nostro impegno di credito

- Ogni immagine con licenza libera è accompagnata dal suo **credito**: autore, fonte e licenza
  (ad es. *« Foto: Nome dell'autore — Wikimedia Commons — CC BY-SA 4.0 »*), con collegamento quando
  la licenza lo richiede.
- I materiali ufficiali sono attribuiti alla loro **fonte** (luogo, organizzatore) quando
  quest'ultima lo richiede o lo giustifica.
- Il testo alternativo (attributo « alt ») descrive l'immagine in modo fattuale (nome dell'evento,
  luogo, città).

## 4. Procedura di rimozione

Sei l'autore o il titolare dei diritti di un'immagine e ritieni che sia utilizzata indebitamente,
oppure desideri che venga rimossa o meglio accreditata? Scrivici:

- **Indirizzo:** **contact@culturasabauda.eu**
- **Oggetto da indicare:** « Crediti fotografici — richiesta di rimozione / correzione »
- **Da specificare:** l'URL della pagina in cui compare l'immagine, una descrizione o schermata
  dell'immagine interessata e il tuo titolo (autore, avente diritto, mandatario).

Ci impegniamo a esaminare la tua richiesta **rapidamente** e, in caso di legittimo dubbio sui
diritti, a **rimuovere o correggere il credito dell'immagine entro un termine ragionevole**, senza
che ciò pregiudichi un eventuale accordo successivo.

## 5. Segnalare un errore di credito

Un errore di attribuzione (autore errato, licenza inesatta) può esserci segnalato allo stesso
indirizzo. Correggiamo volentieri ogni inesattezza in buona fede.
MD;

    get_header();
    ?>
    <div style="max-width:700px;margin:0 auto;padding:0 20px">

      <div style="padding:8px 0 8px">
        <h1 style="margin:0 0 6px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:32px;line-height:1.05;color:#1D1D1B;letter-spacing:0.02em">Crédits photos</h1>
      </div>

      <div>
        <?php echo cs_legal_md_to_html($md_fr); ?>
      </div>

      <div style="margin:48px 0 0;padding-top:36px;border-top:1px solid #E3DCCE">
        <h1 style="margin:0 0 6px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:28px;line-height:1.1;color:#1D1D1B;letter-spacing:0.02em">Crediti fotografici</h1>
      </div>

      <div style="padding-bottom:60px">
        <?php echo cs_legal_md_to_html($md_it); ?>
      </div>

    </div>
    <?php
    get_footer();
    exit;
});
