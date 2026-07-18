<?php
/**
 * "Confidentialité" (page 1701) — rendu complet en PHP (template_redirect),
 * même gabarit simple qu'apropos-template.php / legal-mentions-template.php :
 * H1 + contenu converti depuis docs/legal/confidentialite.md (FR + IT, trame
 * juridique rédigée par Franck). Largeur max 700px, typographie standard du
 * site.
 *
 * ⚠️ CONTENU INCOMPLET PAR CONCEPTION : le document source contient des
 * placeholders entre crochets ([RAISON SOCIALE], [ADRESSE POSTALE COMPLÈTE],
 * [NOM DE L'HÉBERGEUR], [OUTIL D'ANALYTICS — ex. Matomo / GA4], durées de
 * conservation "[par ex. 3 mois]", etc.) — informations réelles non fournies
 * ou décisions non tranchées (quel outil d'analytics est réellement utilisé ?
 * quel hébergeur ?), qu'il est interdit d'inventer. Ce gabarit les affiche
 * tels quels, surlignés (<mark>), pour qu'ils sautent aux yeux en relecture.
 * La page WordPress 1701 reste donc volontairement en post_status=draft tant
 * que Franck n'a pas fourni ces informations — ne JAMAIS publier cette page
 * en l'état (politique de confidentialité publique trompeuse/non conforme
 * RGPD : elle doit refléter les sous-traitants RÉELLEMENT utilisés).
 *
 * Réutilise cs_legal_md_inline()/cs_legal_md_to_html() définies dans
 * legal-mentions-template.php (mêmes fonctions, guardées par
 * function_exists() ici pour rester chargeable indépendamment de l'ordre des
 * snippets — les deux définitions sont identiques, donc peu importe laquelle
 * "gagne" au chargement).
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

        $lines = explode("\n", $md);
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

if (!function_exists('cs_legal_md_table')) {
    /**
     * Convertisseur de table markdown (`| a | b |`) → <table> HTML simple.
     * Le document source de la confidentialité contient 3 tableaux (données
     * traitées/finalités, sous-traitants) que le convertisseur ligne-à-ligne
     * de legal-mentions-template.php ne gère pas (celui-ci n'en a aucun).
     * Utilisé ICI en complément de cs_legal_md_to_html, pas à sa place.
     */
    function cs_legal_md_table($rows) {
        // $rows = tableau de lignes de tableau markdown brutes (avec les "|").
        $cells_of = function ($line) {
            $line = trim($line);
            $line = preg_replace('/^\||\|$/', '', $line);
            return array_map('trim', explode('|', $line));
        };
        $header = $cells_of($rows[0]);
        // $rows[1] = ligne de séparation "---|---|..." à ignorer.
        $body = array_slice($rows, 2);

        $table_style = 'width:100%;border-collapse:collapse;margin:0 0 22px;font-family:\'Nunito Sans\',sans-serif;font-size:13.5px;line-height:1.5;color:#1D1D1B';
        $th_style = 'text-align:left;padding:8px 10px;border-bottom:2px solid #1D1D1B;font-weight:700;background:#F7F1E8';
        $td_style = 'text-align:left;padding:8px 10px;border-bottom:1px solid #E3DCCE;vertical-align:top';

        $html = '<div style="overflow-x:auto;margin:0 0 18px"><table style="' . $table_style . '">' . "\n<thead><tr>\n";
        foreach ($header as $h) {
            $html .= '<th style="' . $th_style . '">' . cs_legal_md_inline($h) . '</th>' . "\n";
        }
        $html .= '</tr></thead><tbody>' . "\n";
        foreach ($body as $line) {
            if (trim($line) === '') { continue; }
            $cells = $cells_of($line);
            $html .= '<tr>' . "\n";
            foreach ($cells as $c) {
                $html .= '<td style="' . $td_style . '">' . cs_legal_md_inline($c) . '</td>' . "\n";
            }
            $html .= '</tr>' . "\n";
        }
        $html .= '</tbody></table></div>' . "\n";
        return $html;
    }
}

if (!function_exists('cs_legal_md_to_html_with_tables')) {
    /**
     * Passe le markdown à cs_legal_md_to_html() en isolant d'abord les blocs
     * de tableau (lignes qui commencent par "|") pour les faire traiter par
     * cs_legal_md_table() à la place — le convertisseur ligne-à-ligne ne
     * connaît pas la syntaxe table.
     */
    function cs_legal_md_to_html_with_tables($md) {
        $lines = explode("\n", $md);
        $html = '';
        $buf = [];
        $table_buf = [];
        $in_table = false;

        $flush_buf = function () use (&$buf, &$html) {
            if (!empty($buf)) {
                $html .= cs_legal_md_to_html(implode("\n", $buf));
                $buf = [];
            }
        };
        $flush_table = function () use (&$table_buf, &$html) {
            if (!empty($table_buf)) {
                $html .= cs_legal_md_table($table_buf);
                $table_buf = [];
            }
        };

        foreach ($lines as $line) {
            $trimmed = trim($line);
            if (strpos($trimmed, '|') === 0) {
                if (!$in_table) {
                    $flush_buf();
                    $in_table = true;
                }
                $table_buf[] = $line;
            } else {
                if ($in_table) {
                    $flush_table();
                    $in_table = false;
                }
                $buf[] = $line;
            }
        }
        $flush_table();
        $flush_buf();

        return $html;
    }
}

add_action('template_redirect', function () {
    if (is_admin() || !is_page(1701)) {
        return;
    }

    // --- FR : sections 1 à 9 (le H1 "# 🇫🇷 Politique de confidentialité" du
    // document source est rendu séparément ci-dessous, pas via le convertisseur) ---
    $md_fr = <<<'MD'
*Dernière mise à jour : [JJ/MM/AAAA]*

Agenda Sabauda (https://agendasabauda.eu), édité par **Cultura Sabauda**, accorde une importance
particulière à la protection de vos données personnelles. La présente politique explique quelles
données sont traitées, dans quel but, sur quelle base légale, combien de temps elles sont
conservées et comment exercer vos droits. Nous appliquons le principe de **minimisation** : nous
ne collectons que les données strictement nécessaires, sans dark pattern ni case pré-cochée.

## 1. Responsable de traitement

- **Responsable :** [RAISON SOCIALE — Cultura Sabauda]
- **Adresse :** [ADRESSE POSTALE COMPLÈTE]
- **Contact :** [contact@culturasabauda.eu]
- **Délégué à la protection des données (DPO), le cas échéant :** [NOM / dpo@culturasabauda.eu]
  *(Si aucun DPO n'est désigné, indiquer le point de contact « protection des données ».)*

## 2. Données traitées, finalités et bases légales

| Traitement | Données collectées | Finalité | Base légale (RGPD) |
|---|---|---|---|
| **Newsletter** | Adresse e-mail (et prénom, facultatif) | Vous envoyer l'agenda et la sélection culturelle | **Consentement** (art. 6.1.a) — opt-in explicite |
| **Formulaire « Proposer un événement »** | Nom, e-mail, informations sur l'événement proposé | Traiter votre proposition, vous recontacter si besoin | **Consentement** / intérêt légitime à répondre (art. 6.1.a / 6.1.f) |
| **Formulaire de contact** | Nom, e-mail, message | Répondre à votre demande | **Consentement** / intérêt légitime (art. 6.1.a / 6.1.f) |
| **Mesure d'audience** | Données de navigation (pages vues, source, appareil), le cas échéant IP tronquée | Comprendre l'usage du site et l'améliorer | **Consentement** (art. 6.1.a) via le bandeau cookies — *ou* intérêt légitime si l'outil est configuré sans cookie ni traceur (voir §6) |

Nous **ne vendons jamais** vos données et ne les utilisons pas à des fins de publicité ciblée.

## 3. Durées de conservation

- **Newsletter :** jusqu'au retrait de votre consentement (désinscription), puis suppression ou
  anonymisation sous [par ex. 3 mois].
- **Proposer un événement / Contact :** le temps de traiter la demande, puis archivage limité,
  au maximum [par ex. 12 mois] à compter du dernier échange.
- **Mesure d'audience :** les données de suivi sont conservées [par ex. 13 mois maximum], les
  statistiques agrégées et anonymes pouvant être conservées au-delà.

## 4. Destinataires et sous-traitants

Vos données sont traitées par l'éditeur et par les prestataires techniques strictement nécessaires
au service, agissant comme **sous-traitants** au sens de l'article 28 du RGPD :

| Sous-traitant | Rôle | Localisation / garanties |
|---|---|---|
| **Brevo (ex-Sendinblue)** | Envoi et gestion de la newsletter | Union européenne (société française) — [préciser] |
| **[NOM DE L'HÉBERGEUR]** | Hébergement du site et des formulaires | [Localisation des serveurs — préciser] |
| **[OUTIL D'ANALYTICS — ex. Matomo / GA4]** | Mesure d'audience | [Localisation / configuration — préciser] |

Chaque sous-traitant est lié par un contrat garantissant un niveau de protection conforme au RGPD.

## 5. Transferts hors Union européenne

Nous privilégions des prestataires hébergeant les données au sein de l'**Union européenne**. Si un
outil implique un transfert hors UE (par exemple [outil concerné]), celui-ci est encadré par les
**clauses contractuelles types** de la Commission européenne ou un mécanisme équivalent. Les
détails sont précisés ici : [préciser le cas échéant, sinon indiquer « aucun transfert hors UE »].

## 6. Cookies et traceurs

À votre arrivée sur le site, un **bandeau de consentement** vous permet d'**accepter** ou de
**refuser** les cookies non essentiels, avec un choix aussi simple pour refuser que pour accepter
(pas de case pré-cochée, pas de consentement déduit du défilement).

- **Cookies strictement nécessaires** (fonctionnement du site, mémorisation de votre choix de
  langue et de vos préférences cookies) : déposés sans consentement, car indispensables.
- **Cookies de mesure d'audience :** déposés **uniquement après votre accord**. *(Si l'outil est
  configuré en mode « sans cookie » et exempté au sens des recommandations de la CNIL, le préciser
  ici.)*

Vous pouvez à tout moment **modifier ou retirer votre choix** via le lien « Gérer les cookies » en
pied de page, ou en réglant votre navigateur.

## 7. Vos droits

Conformément au RGPD, vous disposez des droits suivants sur vos données :

- **Droit d'accès** — savoir quelles données nous détenons sur vous ;
- **Droit de rectification** — corriger une donnée inexacte ;
- **Droit à l'effacement** (« droit à l'oubli ») — demander la suppression de vos données ;
- **Droit d'opposition** — vous opposer à un traitement fondé sur l'intérêt légitime ;
- **Droit à la limitation** du traitement ;
- **Droit à la portabilité** — récupérer vos données dans un format réutilisable ;
- **Droit de retirer votre consentement** à tout moment, sans que cela remette en cause la
  licéité du traitement effectué avant le retrait.

**Comment les exercer :** écrivez à **[contact@culturasabauda.eu]** (ou au DPO le cas échéant :
[dpo@culturasabauda.eu]), en précisant votre demande. Nous pourrons vous demander un justificatif
d'identité si un doute raisonnable existe. Nous répondons dans un délai d'**un mois**.

Pour la newsletter, un lien de **désinscription** figure dans chaque envoi : un clic suffit.

**Réclamation :** si vous estimez que vos droits ne sont pas respectés, vous pouvez saisir la
**CNIL** (Commission nationale de l'informatique et des libertés — www.cnil.fr).

## 8. Sécurité

Nous mettons en œuvre des mesures techniques et organisationnelles raisonnables (accès restreint,
connexion chiffrée HTTPS, choix de prestataires conformes) pour protéger vos données contre tout
accès, altération ou divulgation non autorisés.

## 9. Modifications

La présente politique peut être mise à jour. La date de dernière révision figure en tête de page.
En cas de changement substantiel, une information sera portée sur le site.
MD;

    // --- IT : sections 1 à 9 ---
    $md_it = <<<'MD'
*Ultimo aggiornamento: [GG/MM/AAAA]*

Agenda Sabauda (https://agendasabauda.eu), edito da **Cultura Sabauda**, attribuisce particolare
importanza alla protezione dei tuoi dati personali. La presente informativa spiega quali dati
vengono trattati, per quali finalità, su quale base giuridica, per quanto tempo sono conservati e
come esercitare i tuoi diritti. Applichiamo il principio di **minimizzazione**: raccogliamo solo i
dati strettamente necessari, senza dark pattern né caselle pre-selezionate.

## 1. Titolare del trattamento

- **Titolare:** [RAGIONE SOCIALE — Cultura Sabauda]
- **Indirizzo:** [INDIRIZZO POSTALE COMPLETO]
- **Contatti:** [contact@culturasabauda.eu]
- **Responsabile della protezione dei dati (DPO), se nominato:** [NOME / dpo@culturasabauda.eu]
  *(Se non è nominato alcun DPO, indicare il punto di contatto «protezione dei dati».)*

## 2. Dati trattati, finalità e basi giuridiche

| Trattamento | Dati raccolti | Finalità | Base giuridica (GDPR) |
|---|---|---|---|
| **Newsletter** | Indirizzo e-mail (e nome, facoltativo) | Inviarti l'agenda e la selezione culturale | **Consenso** (art. 6.1.a) — opt-in esplicito |
| **Modulo «Proponi un evento»** | Nome, e-mail, informazioni sull'evento proposto | Gestire la tua proposta, ricontattarti se necessario | **Consenso** / legittimo interesse a rispondere (art. 6.1.a / 6.1.f) |
| **Modulo di contatto** | Nome, e-mail, messaggio | Rispondere alla tua richiesta | **Consenso** / legittimo interesse (art. 6.1.a / 6.1.f) |
| **Misurazione del traffico** | Dati di navigazione (pagine viste, provenienza, dispositivo), eventualmente IP troncato | Comprendere l'uso del sito e migliorarlo | **Consenso** (art. 6.1.a) tramite il banner cookie — *oppure* legittimo interesse se lo strumento è configurato senza cookie né tracciatori (vedi §6) |

**Non vendiamo mai** i tuoi dati e non li utilizziamo per pubblicità profilata.

## 3. Tempi di conservazione

- **Newsletter:** fino alla revoca del consenso (cancellazione dell'iscrizione), poi soppressione o
  anonimizzazione entro [ad es. 3 mesi].
- **Proponi un evento / Contatto:** per il tempo necessario a gestire la richiesta, poi archiviazione
  limitata, al massimo [ad es. 12 mesi] dall'ultimo scambio.
- **Misurazione del traffico:** i dati di monitoraggio sono conservati [ad es. massimo 13 mesi]; le
  statistiche aggregate e anonime possono essere conservate oltre.

## 4. Destinatari e responsabili del trattamento

I tuoi dati sono trattati dall'editore e dai fornitori tecnici strettamente necessari al servizio,
che agiscono come **responsabili del trattamento** ai sensi dell'articolo 28 del GDPR:

| Responsabile | Ruolo | Localizzazione / garanzie |
|---|---|---|
| **Brevo (ex Sendinblue)** | Invio e gestione della newsletter | Unione europea (società francese) — [precisare] |
| **[NOME DEL PROVIDER DI HOSTING]** | Hosting del sito e dei moduli | [Localizzazione dei server — precisare] |
| **[STRUMENTO DI ANALYTICS — es. Matomo / GA4]** | Misurazione del traffico | [Localizzazione / configurazione — precisare] |

Ciascun responsabile è vincolato da un contratto che garantisce un livello di protezione conforme
al GDPR.

## 5. Trasferimenti fuori dall'Unione europea

Privilegiamo fornitori che conservano i dati all'interno dell'**Unione europea**. Se uno strumento
comporta un trasferimento fuori dall'UE (ad esempio [strumento interessato]), esso è disciplinato
dalle **clausole contrattuali tipo** della Commissione europea o da un meccanismo equivalente. I
dettagli sono precisati qui: [precisare se del caso, altrimenti indicare «nessun trasferimento
fuori dall'UE»].

## 6. Cookie e tracciatori

Al tuo arrivo sul sito, un **banner di consenso** ti permette di **accettare** o **rifiutare** i
cookie non essenziali, con una scelta di rifiuto altrettanto semplice quanto quella di accettazione
(nessuna casella pre-selezionata, nessun consenso dedotto dallo scorrimento).

- **Cookie strettamente necessari** (funzionamento del sito, memorizzazione della lingua scelta e
  delle preferenze sui cookie): installati senza consenso, in quanto indispensabili.
- **Cookie di misurazione del traffico:** installati **solo dopo il tuo consenso**. *(Se lo
  strumento è configurato in modalità «senza cookie» ed esente secondo le raccomandazioni del
  Garante, precisarlo qui.)*

Puoi in qualsiasi momento **modificare o revocare la tua scelta** tramite il link «Gestisci i
cookie» a piè di pagina, o intervenendo sulle impostazioni del tuo browser.

## 7. I tuoi diritti

In conformità al GDPR, hai i seguenti diritti sui tuoi dati:

- **Diritto di accesso** — sapere quali dati deteniamo su di te;
- **Diritto di rettifica** — correggere un dato inesatto;
- **Diritto alla cancellazione** («diritto all'oblio») — chiedere la soppressione dei tuoi dati;
- **Diritto di opposizione** — opporti a un trattamento basato sul legittimo interesse;
- **Diritto alla limitazione** del trattamento;
- **Diritto alla portabilità** — ottenere i tuoi dati in un formato riutilizzabile;
- **Diritto di revocare il consenso** in qualsiasi momento, senza che ciò pregiudichi la liceità
  del trattamento effettuato prima della revoca.

**Come esercitarli:** scrivi a **[contact@culturasabauda.eu]** (o al DPO se nominato:
[dpo@culturasabauda.eu]), precisando la tua richiesta. Potremo chiederti un documento d'identità in
caso di ragionevole dubbio. Rispondiamo entro **un mese**.

Per la newsletter, in ogni invio è presente un link di **cancellazione**: basta un clic.

**Reclamo:** se ritieni che i tuoi diritti non siano rispettati, puoi rivolgerti al **Garante per
la protezione dei dati personali** (www.garanteprivacy.it) o all'autorità di controllo competente,
in Francia la **CNIL** (www.cnil.fr).

## 8. Sicurezza

Adottiamo misure tecniche e organizzative ragionevoli (accesso limitato, connessione cifrata HTTPS,
scelta di fornitori conformi) per proteggere i tuoi dati da accessi, alterazioni o divulgazioni non
autorizzati.

## 9. Modifiche

La presente informativa può essere aggiornata. La data dell'ultima revisione è indicata in cima
alla pagina. In caso di modifica sostanziale, ne verrà data comunicazione sul sito.
MD;

    get_header();
    ?>
    <div style="max-width:700px;margin:0 auto;padding:0 20px">

      <div style="margin:28px 0 32px;padding:16px 18px;background:#FBF3E3;border:1px solid #E8C98A;border-radius:6px;font-family:'Nunito Sans',sans-serif;font-size:14px;line-height:1.6;color:#1D1D1B">
        <strong>⚠️ Brouillon interne — page non publiée.</strong> Ce document est une trame
        rédactionnelle à faire valider par un juriste ; elle ne constitue pas un conseil
        juridique. Les passages surlignés en <mark style="background:#F7D9A0;color:#1D1D1B;padding:0 3px;border-radius:2px">jaune</mark>
        sont des informations réelles manquantes ou des décisions non tranchées (raison sociale,
        adresse, DPO, hébergeur, outil d'analytics réellement utilisé, durées de conservation…)
        qui doivent être fournies puis remplacées avant toute mise en ligne.
      </div>

      <div style="padding:8px 0 8px">
        <h1 style="margin:0 0 6px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:32px;line-height:1.05;color:#1D1D1B;letter-spacing:0.02em">Politique de confidentialité</h1>
      </div>

      <div>
        <?php echo cs_legal_md_to_html_with_tables($md_fr); ?>
      </div>

      <div style="margin:48px 0 0;padding-top:36px;border-top:1px solid #E3DCCE">
        <h1 style="margin:0 0 6px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:28px;line-height:1.1;color:#1D1D1B;letter-spacing:0.02em">Informativa sulla privacy</h1>
      </div>

      <div style="padding-bottom:60px">
        <?php echo cs_legal_md_to_html_with_tables($md_it); ?>
      </div>

    </div>
    <?php
    get_footer();
    exit;
});
