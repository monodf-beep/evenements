<?php
/**
 * "Mentions légales" (page 1700) — rendu complet en PHP (template_redirect),
 * gabarit simple : H1 + contenu converti depuis
 * docs/legal/mentions_legales.md (FR + IT, trame juridique rédigée par
 * Franck). Largeur max 700px, typographie standard du site, comme
 * apropos-template.php.
 *
 * Infos légales réelles fournies par Franck le 18/07/2026 (raison sociale,
 * statut, adresse du siège, directeur de publication, hébergeur) — plus de
 * placeholder bloquant. N° d'immatriculation/TVA/téléphone non communiqués
 * par Franck, affichés en clair comme "Non communiqué" plutôt qu'inventés.
 * Page publiée (post_status=publish) une fois vérifiée en live.
 *
 * Convertisseur markdown→HTML minimal maison (cs_legal_md_to_html) : gère
 * uniquement le sous-ensemble utilisé par le document source (## / ###,
 * paragraphes, listes à puces "- " avec lignes de continuation indentées,
 * **gras**, *italique*, URLs nues, placeholders [entre crochets]). Pas un
 * parseur markdown généraliste — volontairement limité ("HTML simple"
 * demandé), suffisant pour ce document.
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
        // liste qui déborde sur la ligne suivante, ex. section 6 FR/IT du
        // document source) à la ligne logique précédente, avant le parsing.
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
    if (is_admin() || !is_page(1700)) {
        return;
    }

    // --- FR : sections 1 à 10 (le H1 "# 🇫🇷 Mentions légales" du document
    // source est rendu séparément ci-dessous, pas via le convertisseur) ---
    $md_fr = <<<'MD'
*Dernière mise à jour : 18/07/2026*

## 1. Éditeur du site

Le site **Agenda Sabauda** (https://agendasabauda.eu) est édité par **Cultura Sabauda**, média
culturel bilingue de l'espace alpin occidental (Savoie et Haute-Savoie, Piémont, Vallée d'Aoste,
Nice et Alpes-Maritimes).

- **Raison sociale / dénomination :** Franck Monod — Cultura Sabauda
- **Statut juridique :** Entrepreneur individuel (indépendant)
- **Adresse du siège :** 267 rue de la République, 73000 Chambéry, France
- **Numéro d'immatriculation :** Non communiqué
- **Numéro de TVA intracommunautaire :** Non assujetti à la TVA
- **Adresse électronique de contact :** contact@culturasabauda.eu
- **Téléphone :** Non communiqué

## 2. Directeur de la publication

Le directeur de la publication est **Franck Monod**, éditeur du site.

## 3. Hébergeur

Le site est hébergé par :

- **Hébergeur :** OVH SAS
- **Adresse :** 2 rue Kellermann, 59100 Roubaix, France
- **Contact :** https://www.ovhcloud.com

## 4. Nature du site : un agrégateur culturel

Agenda Sabauda est un **agenda agrégateur** : il recense des manifestations culturelles à venir
(expositions, concerts, spectacles, festivals, sagre, marchés, fêtes traditionnelles, rendez-vous
en famille et événements sportifs) sur ses quatre territoires.

**Origine des informations événementielles.** Les données pratiques diffusées (intitulé, dates,
horaires, lieu, ville, tarif ou gratuité, catégorie, organisateur) sont **vérifiées à la source
officielle** : la page du lieu, de l'organisateur, de l'office de tourisme ou de la billetterie
officielle. L'attribution et les liens renvoient toujours vers ces **acteurs primaires**.

**Faits et expression.** Les informations factuelles relatives à un événement (une date, un lieu,
un programme) ne sont pas, en elles-mêmes, protégées par le droit d'auteur : Agenda Sabauda les
recueille et les republie librement. En revanche, l'éditeur **ne reproduit jamais l'expression**
d'un tiers (le texte, les formules ou l'analyse d'un article de presse).

**Contenu détecté via la presse (« radar »).** Certains événements sont *repérés* grâce à une
veille de la presse locale. Cette veille sert **uniquement à la détection** : les articles de
presse ne sont **ni cités, ni crédités, ni reproduits** sur Agenda Sabauda. Le contenu publié est
systématiquement reconstitué et vérifié à partir des sources officielles de l'événement.

## 5. Propriété intellectuelle

L'architecture du site, sa charte graphique, ses textes éditoriaux originaux (chapôs, intros de
rubriques, sélections rédactionnelles) et la marque **Agenda Sabauda** sont la propriété de
l'éditeur ou de son maison-mère Cultura Sabauda. Toute reproduction ou réutilisation, totale ou
partielle, sans autorisation écrite préalable, est interdite.

Les **données factuelles** relatives aux événements peuvent être librement consultées et partagées.

Les **images** obéissent à une politique dédiée : voir la page **Crédits photos**
(https://agendasabauda.eu/fr/credits-photos/). Les logos et visuels des lieux et organisateurs
demeurent la propriété de leurs titulaires respectifs.

## 6. Signaler ou demander le retrait d'un événement

Un lieu, un organisateur ou un ayant droit peut à tout moment demander la **correction** ou le
**retrait** d'un événement le concernant.

- **Adresse :** contact@culturasabauda.eu
- **Objet à indiquer :** « Signalement / retrait — nom de l'événement concerné »
- **À préciser :** l'URL de la fiche concernée, la nature de la demande (erreur factuelle, doublon,
  demande de retrait) et, pour un ayant droit, la qualité à agir.

L'éditeur s'engage à examiner chaque demande dans les meilleurs délais et à procéder, le cas
échéant, à la correction ou au retrait dans un **délai raisonnable**.

## 7. Liens hypertextes

Agenda Sabauda renvoie vers des sites externes (lieux, organisateurs, billetteries officielles)
sur lesquels l'éditeur n'exerce aucun contrôle et ne saurait être tenu pour responsable de leur
contenu.

## 8. Responsabilité

L'éditeur s'efforce d'assurer l'exactitude et la mise à jour des informations. Les événements
étant susceptibles d'évoluer (report, annulation, changement de tarif ou d'horaire), il est
recommandé de **vérifier auprès de l'organisateur** avant de se déplacer. La responsabilité de
l'éditeur ne saurait être engagée en cas d'erreur, d'omission ou d'indisponibilité du service.

## 9. Données personnelles et cookies

Le traitement des données personnelles et l'usage des cookies sont décrits dans la
**Politique de confidentialité** (https://agendasabauda.eu/fr/confidentialite/).

## 10. Droit applicable

Les présentes mentions sont soumises au **droit français**. Tout litige relève, à défaut de
résolution amiable, des tribunaux compétents du ressort du siège de l'éditeur.
MD;

    // --- IT : sections 1 à 10 ---
    $md_it = <<<'MD'
*Ultimo aggiornamento: 18/07/2026*

## 1. Editore del sito

Il sito **Agenda Sabauda** (https://agendasabauda.eu) è edito da **Cultura Sabauda**, testata
culturale bilingue dello spazio alpino occidentale (Savoia e Alta Savoia, Piemonte, Valle d'Aosta,
Nizza e Alpi Marittime).

- **Denominazione / ragione sociale:** Franck Monod — Cultura Sabauda
- **Forma giuridica:** Imprenditore individuale (indipendente)
- **Sede legale:** 267 rue de la République, 73000 Chambéry, Francia
- **Numero di iscrizione:** Non comunicato
- **Partita IVA:** Soggetto non titolare di partita IVA
- **Indirizzo e-mail di contatto:** contact@culturasabauda.eu
- **Telefono:** Non comunicato

## 2. Direttore responsabile della pubblicazione

Il direttore responsabile della pubblicazione è **Franck Monod**, editore del sito.

## 3. Hosting

Il sito è ospitato da:

- **Provider di hosting:** OVH SAS
- **Indirizzo:** 2 rue Kellermann, 59100 Roubaix, Francia
- **Contatti:** https://www.ovhcloud.com

## 4. Natura del sito: un aggregatore culturale

Agenda Sabauda è un **agenda aggregatore**: raccoglie eventi culturali in programma (mostre,
concerti, spettacoli, festival, sagre, mercati, feste tradizionali, appuntamenti per le famiglie
ed eventi sportivi) sui suoi quattro territori.

**Origine delle informazioni sugli eventi.** I dati pratici pubblicati (titolo, date, orari,
luogo, città, prezzo o gratuità, categoria, organizzatore) sono **verificati alla fonte
ufficiale**: la pagina del luogo, dell'organizzatore, dell'ente del turismo o della biglietteria
ufficiale. L'attribuzione e i collegamenti rimandano sempre a questi **soggetti primari**.

**Fatti ed espressione.** Le informazioni fattuali su un evento (una data, un luogo, un programma)
non sono di per sé protette dal diritto d'autore: Agenda Sabauda le raccoglie e le ripubblica
liberamente. L'editore, invece, **non riproduce mai l'espressione** di terzi (il testo, le formule
o l'analisi di un articolo di stampa).

**Contenuti individuati tramite la stampa («radar»).** Alcuni eventi vengono *individuati* grazie
al monitoraggio della stampa locale. Questo monitoraggio serve **unicamente all'individuazione**:
gli articoli di stampa **non sono citati, né accreditati, né riprodotti** su Agenda Sabauda. Il
contenuto pubblicato è sempre ricostruito e verificato a partire dalle fonti ufficiali
dell'evento.

## 5. Proprietà intellettuale

L'architettura del sito, la veste grafica, i testi editoriali originali (occhielli, introduzioni
di rubrica, selezioni redazionali) e il marchio **Agenda Sabauda** sono di proprietà dell'editore
o della sua casa editrice Cultura Sabauda. Ogni riproduzione o riutilizzo, totale o parziale,
senza previa autorizzazione scritta, è vietato.

I **dati fattuali** relativi agli eventi possono essere liberamente consultati e condivisi.

Le **immagini** seguono una politica dedicata: si veda la pagina **Crediti fotografici**
(https://agendasabauda.eu/it/crediti-foto/). I loghi e i materiali visivi dei luoghi e degli
organizzatori restano di proprietà dei rispettivi titolari.

## 6. Segnalare o chiedere la rimozione di un evento

Un luogo, un organizzatore o un avente diritto può in qualsiasi momento chiedere la **correzione**
o la **rimozione** di un evento che lo riguarda.

- **Indirizzo:** contact@culturasabauda.eu
- **Oggetto da indicare:** «Segnalazione / rimozione — nome dell'evento in questione»
- **Da specificare:** l'URL della scheda interessata, la natura della richiesta (errore fattuale,
  duplicato, richiesta di rimozione) e, per un avente diritto, il titolo ad agire.

L'editore si impegna a esaminare ogni richiesta nel più breve tempo possibile e a procedere, se del
caso, alla correzione o alla rimozione entro un **termine ragionevole**.

## 7. Collegamenti ipertestuali

Agenda Sabauda rimanda a siti esterni (luoghi, organizzatori, biglietterie ufficiali) sui quali
l'editore non esercita alcun controllo e di cui non può essere ritenuto responsabile.

## 8. Responsabilità

L'editore si adopera per garantire l'esattezza e l'aggiornamento delle informazioni. Poiché gli
eventi possono subire variazioni (rinvio, annullamento, modifica di prezzo od orario), si
raccomanda di **verificare presso l'organizzatore** prima di recarsi sul posto. L'editore non può
essere ritenuto responsabile in caso di errore, omissione o indisponibilità del servizio.

## 9. Dati personali e cookie

Il trattamento dei dati personali e l'uso dei cookie sono descritti nell'**Informativa sulla
privacy** (https://agendasabauda.eu/it/privacy/).

## 10. Legge applicabile

Le presenti note legali sono soggette al **diritto francese**. Ogni controversia rientra, in
mancanza di soluzione amichevole, nella competenza dei tribunali della sede dell'editore.
MD;

    get_header();
    ?>
    <div style="max-width:700px;margin:0 auto;padding:0 20px">

      <div style="padding:8px 0 8px">
        <h1 style="margin:0 0 6px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:32px;line-height:1.05;color:#1D1D1B;letter-spacing:0.02em">Mentions légales</h1>
      </div>

      <div>
        <?php echo cs_legal_md_to_html($md_fr); ?>
      </div>

      <div style="margin:48px 0 0;padding-top:36px;border-top:1px solid #E3DCCE">
        <h1 style="margin:0 0 6px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:28px;line-height:1.1;color:#1D1D1B;letter-spacing:0.02em">Note legali</h1>
      </div>

      <div style="padding-bottom:60px">
        <?php echo cs_legal_md_to_html($md_it); ?>
      </div>

    </div>
    <?php
    get_footer();
    exit;
});
