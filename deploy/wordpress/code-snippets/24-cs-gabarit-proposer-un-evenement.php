/**
 * "Proposer un événement" (page 934) — formulaire public fonctionnel en PHP
 * (template_redirect), fidèle à "Agenda Sabaudo - Proposer un evenement.dc.html"
 * (lue le 2026-07-13). Le header spécifique de la maquette ("← Retour" + logo
 * seul) N'EST PAS repris — on garde le header/footer de marque site-wide
 * (site-header-footer.php) pour rester cohérent avec le reste du site déjà
 * reconstruit cette session (Recherche, Hubs, Ce week-end...).
 *
 * Chaque proposition crée un `tribe_events` en statut DRAFT (jamais publié
 * automatiquement — conforme à la promesse éditoriale de la maquette
 * "Aucune information n'est publiée avant vérification par la rédaction").
 * Dates/horaires et lieu sont des CHAMPS LIBRES saisis par l'organisateur
 * (pas de date picker dans la maquette) — stockés en meta `_as_submitted_*`
 * et repris dans le contenu du brouillon pour que la rédaction les structure
 * elle-même (heure TEC réelle, lieu TEC réel) avant publication. On ne tente
 * pas de parser automatiquement une date en texte libre (peu fiable, brief
 * §11 interdit toute donnée publiée sans vérification humaine de toute façon).
 */
add_action('template_redirect', function () {
    if (is_admin() || (!is_page(934) && !is_page(3183))) {
        return;
    }

    $is_it = function_exists('pll_current_language') && pll_current_language() === 'it';
    $LB = $is_it ? array(
      'Le formulaire a expiré, merci de réessayer.' => 'Il modulo è scaduto, riprova.',
      "Le titre de l'événement est requis." => "Il titolo dell'evento è obbligatorio.",
      'Les dates et horaires sont requis.' => 'Le date e gli orari sono obbligatori.',
      'Le lieu est requis.' => 'È obbligatorio indicare il luogo.',
      'Une adresse e-mail valide est requise.' => 'È obbligatorio un indirizzo email valido.',
      "Merci d'accepter l'utilisation de ces informations pour valider l'envoi." => "Accetta l'uso di queste informazioni per convalidare l'invio.",
      "La photo n'a pas pu être envoyée (" => 'Non è stato possibile inviare la foto (',
      "L'enregistrement a échoué, merci de réessayer." => 'La registrazione non è riuscita, riprova.',
      'Merci pour votre proposition' => 'Grazie per la tua proposta',
      'Nous relisons chaque événement sous 5 jours ouvrés.' => 'Esaminiamo ogni evento entro 5 giorni lavorativi.',
      "Rien n'est publié sans vérification par la rédaction." => 'Nulla viene pubblicato senza la verifica della redazione.',
      'Proposer un événement' => 'Proponi un evento',
      'Organisateur ?' => 'Organizzatore?',
      "Ajoutez votre événement gratuitement, nous le relisons avant publication." => "Aggiungi il tuo evento gratuitamente, lo esaminiamo prima della pubblicazione.",
      "Titre de l'événement" => "Titolo dell'evento",
      'Ex. Marché nocturne des artisans' => 'Es. Mercato notturno degli artigiani',
      'Catégorie' => 'Categoria',
      'Concerts &amp; Musique, Marchés, Expositions…' => 'Concerti e musica, mercati, mostre...',
      'Territoire / ville' => 'Territorio / città',
      "Savoie · Piémont · Vallée d'Aoste · Nice" => "Savoia · Piemonte · Valle d'Aosta · Nizza",
      'Dates et horaires' => 'Date e orari',
      'Ex. 12–13 juillet 2026 · 18h–23h' => 'Es. 12-13 luglio 2026 · 18-23',
      'Lieu' => 'Luogo',
      'Ex. Place du marché, Aoste' => 'Es. Piazza del mercato, Aosta',
      'Description' => 'Descrizione',
      "Quelques lignes sur l'événement, son intérêt, le public visé…" => "Qualche riga sull'evento, il suo interesse, il pubblico previsto...",
      'Lien billetterie (facultatif)' => 'Link biglietteria (facoltativo)',
      'Photo (1)' => 'Foto (1)',
      'Votre e-mail' => 'La tua email',
      'Pour vous recontacter si besoin' => 'Per ricontattarti se necessario',
      "J'accepte que ces informations soient utilisées pour l'examen et la publication de cet événement, conformément à la politique de confidentialité." => "Accetto che queste informazioni siano utilizzate per l'esame e la pubblicazione di questo evento, in conformità con l'informativa sulla privacy.",
      'Envoyer pour validation' => 'Invia per la convalida',
      'Vous publiez un agenda ?' => 'Pubblichi un calendario di eventi?',
      "Envoyez-nous votre flux RSS ou le lien d'inscription à votre newsletter : nous le relisons et l'ajoutons à nos sources." => 'Inviaci il tuo feed RSS o il link di iscrizione alla tua newsletter: lo esaminiamo e lo aggiungiamo alle nostre fonti.',
      'Type de source' => 'Tipo di fonte',
      'Flux RSS' => 'Feed RSS',
      'Newsletter (lien d’inscription)' => 'Newsletter (link di iscrizione)',
      'Autre / je ne sais pas' => 'Altro / non so',
      'Adresse du flux ou de la page d’inscription' => 'Indirizzo del feed o della pagina di iscrizione',
      'Organisme (facultatif)' => 'Ente (facoltativo)',
      'Ex. Office de tourisme de Chambéry' => 'Es. Ufficio del turismo di Aosta',
      'Proposer cette source' => 'Proponi questa fonte',
      'Merci, la source est bien reçue' => 'Grazie, la fonte è stata ricevuta',
      'Nous la vérifions avant de l’ajouter à notre veille.' => 'La verifichiamo prima di aggiungerla al nostro monitoraggio.',
      'Une adresse (flux ou page d’inscription) valide est requise.' => 'È obbligatorio un indirizzo valido (feed o pagina di iscrizione).',
      "Aucune information n'est publiée avant vérification par la rédaction." => 'Nessuna informazione viene pubblicata senza verifica della redazione.',
    ) : array();
    $tr = function($s) use ($LB){ return isset($LB[$s]) ? $LB[$s] : $s; };

    $errors = [];
    $submitted = false;

    // 2026-09-06 (Franck) : proposer aussi une SOURCE (flux RSS ou lien d'inscription a une
    // newsletter), sans evenement. Rangee dans l'option cs_sources_proposees et annoncee sur
    // Slack par cs_slack_notify_form -- donc dans le recapitulatif quotidien de 11h45, comme
    // les propositions d'evenement (decision Franck : un seul message Slack par jour).
    $src_errors = [];
    $src_submitted = false;
    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['as_source_nonce'])) {
        if (!wp_verify_nonce($_POST['as_source_nonce'], 'as_propose_source')) {
            $src_errors[] = $tr("Le formulaire a expiré, merci de réessayer.");
        } elseif (!empty($_POST['as_hp_check'])) {
            $src_submitted = true;
        } else {
            $src_type = in_array($_POST['as_source_type'] ?? '', ['rss', 'newsletter', 'autre'], true) ? $_POST['as_source_type'] : 'autre';
            $src_url = esc_url_raw(trim((string) ($_POST['as_source_url'] ?? '')));
            $src_org = sanitize_text_field($_POST['as_source_org'] ?? '');
            $src_email = sanitize_email($_POST['as_source_email'] ?? '');
            $src_consent = !empty($_POST['as_source_consent']);
            if ($src_url === '' || !filter_var($src_url, FILTER_VALIDATE_URL)) $src_errors[] = $tr('Une adresse (flux ou page d’inscription) valide est requise.');
            if ($src_email === '' || !is_email($src_email)) $src_errors[] = $tr("Une adresse e-mail valide est requise.");
            if (!$src_consent) $src_errors[] = $tr("Merci d'accepter l'utilisation de ces informations pour valider l'envoi.");
            if (empty($src_errors)) {
                $liste = get_option('cs_sources_proposees', []);
                if (!is_array($liste)) { $liste = []; }
                $liste[] = ['at' => current_time('mysql'), 'type' => $src_type, 'url' => $src_url, 'org' => $src_org, 'email' => $src_email, 'lang' => $is_it ? 'it' : 'fr'];
                update_option('cs_sources_proposees', $liste, false);
                $src_submitted = true;
                $src_type_lbl = ['rss' => 'Flux RSS', 'newsletter' => 'Newsletter', 'autre' => 'Autre / inconnu'][$src_type];
                if (function_exists('cs_slack_notify_form')) {
                    cs_slack_notify_form(
                        ":satellite: *Source proposee* (formulaire " . ($is_it ? 'IT' : 'FR') . ")\n"
                        . "*Type :* {$src_type_lbl}\n"
                        . "*Adresse :* {$src_url}\n"
                        . ($src_org !== '' ? "*Organisme :* {$src_org}\n" : '')
                        . "*Contact :* {$src_email}\n"
                        . "_Rangee dans l'option cs_sources_proposees (" . count($liste) . " au total)._"
                    );
                }
            }
        }
    }

    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['as_propose_nonce'])) {
        if (!wp_verify_nonce($_POST['as_propose_nonce'], 'as_propose_event')) {
            $errors[] = $tr("Le formulaire a expiré, merci de réessayer.");
        } elseif (!empty($_POST['as_hp_check'])) {
            // Honeypot rempli → soumission automatisée, on ignore silencieusement.
            $submitted = true;
        } else {
            $title = sanitize_text_field($_POST['as_title'] ?? '');
            $category = absint($_POST['as_category'] ?? 0);
            $territoire = absint($_POST['as_territoire'] ?? 0);
            $dates = sanitize_text_field($_POST['as_dates'] ?? '');
            $lieu = sanitize_text_field($_POST['as_lieu'] ?? '');
            $description = sanitize_textarea_field($_POST['as_description'] ?? '');
            $billetterie = !empty($_POST['as_billetterie']) ? esc_url_raw($_POST['as_billetterie']) : '';
            $email = sanitize_email($_POST['as_email'] ?? '');
            $consent = !empty($_POST['as_consent']);

            if ($title === '') $errors[] = $tr("Le titre de l'événement est requis.");
            if ($dates === '') $errors[] = $tr("Les dates et horaires sont requis.");
            if ($lieu === '') $errors[] = $tr("Le lieu est requis.");
            if ($email === '' || !is_email($email)) $errors[] = $tr("Une adresse e-mail valide est requise.");
            if (!$consent) $errors[] = $tr("Merci d'accepter l'utilisation de ces informations pour valider l'envoi.");

            $photo_id = 0;
            if (empty($errors) && !empty($_FILES['as_photo']['name'])) {
                require_once ABSPATH . 'wp-admin/includes/image.php';
                require_once ABSPATH . 'wp-admin/includes/file.php';
                require_once ABSPATH . 'wp-admin/includes/media.php';
                $allowed = ['jpg' => 'image/jpeg', 'jpeg' => 'image/jpeg', 'png' => 'image/png', 'webp' => 'image/webp'];
                $photo_id = media_handle_upload('as_photo', 0, [], ['mimes' => $allowed, 'test_form' => false]);
                if (is_wp_error($photo_id)) {
                    $errors[] = $tr("La photo n'a pas pu être envoyée (") . esc_html($photo_id->get_error_message()) . ").";
                    $photo_id = 0;
                }
            }

            if (empty($errors)) {
                $content = "Proposition reçue via le formulaire public.\n\n"
                    . "Dates et horaires (texte libre organisateur) : {$dates}\n"
                    . "Lieu (texte libre organisateur) : {$lieu}\n\n"
                    . ($description !== '' ? $description . "\n\n" : '')
                    . ($billetterie !== '' ? "Billetterie : {$billetterie}\n" : '')
                    . "Contact organisateur : {$email}";

                $post_id = wp_insert_post([
                    'post_type' => 'tribe_events',
                    'post_status' => 'draft',
                    'post_title' => $title,
                    'post_content' => $content,
                ], true);

                if (is_wp_error($post_id)) {
                    $errors[] = $tr("L'enregistrement a échoué, merci de réessayer.");
                } else {
                    update_post_meta($post_id, '_as_submitted_dates', $dates);
                    update_post_meta($post_id, '_as_submitted_lieu', $lieu);
                    update_post_meta($post_id, '_as_submitted_email', $email);
                    if ($billetterie !== '') {
                        update_post_meta($post_id, '_EventURL', $billetterie);
                    }
                    if ($category) {
                        wp_set_object_terms($post_id, [$category], 'tribe_events_cat');
                    }
                    if ($territoire) {
                        wp_set_object_terms($post_id, [$territoire], 'territoire');
                    }
                    if ($photo_id) {
                        set_post_thumbnail($post_id, $photo_id);
                    }
                    $submitted = true;

                    $cat_nom = $category ? (get_term($category)->name ?? "#{$category}") : '(non precisee)';
                    $terr_nom = $territoire ? (get_term($territoire)->name ?? "#{$territoire}") : '(non precise)';
                    cs_slack_notify_form(
                        ":calendar: *Proposition d'evenement*\n"
                        . "*Titre :* {$title}\n"
                        . "*Dates :* {$dates}\n"
                        . "*Lieu :* {$lieu}\n"
                        . "*Categorie :* {$cat_nom} — *Territoire :* {$terr_nom}\n"
                        . "*Contact :* {$email}\n"
                        . admin_url('post.php?post=' . $post_id . '&action=edit')
                    );
                }
            }
        }
    }

    get_header();

    $categories = get_terms(['taxonomy' => 'tribe_events_cat', 'hide_empty' => false]);
    $territoires = get_terms(['taxonomy' => 'territoire', 'hide_empty' => false, 'parent' => 0]);
    ?>
    <div style="max-width:560px;margin:0 auto;padding:0 20px">

    <?php if ($submitted): ?>

      <div style="padding:48px 0;text-align:center">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#1D1D1B" stroke-width="1.6" style="margin-bottom:16px"><circle cx="12" cy="12" r="9.5"></circle><polyline points="8 12.5 11 15.5 16 9"></polyline></svg>
        <h1 style="margin:0 0 10px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:26px;line-height:1.15;color:#1D1D1B;letter-spacing:0.02em"><?php echo esc_html($tr("Merci pour votre proposition")); ?></h1>
        <p style="margin:0 0 4px;font-family:'Nunito Sans',sans-serif;font-size:13.5px;line-height:1.55;color:#4A4A48"><?php echo esc_html($tr("Nous relisons chaque événement sous 5 jours ouvrés.")); ?></p>
        <p style="margin:0;font-family:'Nunito Sans',sans-serif;font-size:13.5px;line-height:1.55;color:#4A4A48"><?php echo esc_html($tr("Rien n'est publié sans vérification par la rédaction.")); ?></p>
      </div>

    <?php else: ?>

      <div style="padding:24px 0 12px">
        <div style="font-family:'Nunito Sans',sans-serif;font-size:10px;font-weight:700;letter-spacing:0.18em;color:#DC5D45;text-transform:uppercase;margin-bottom:8px"><?php echo esc_html($tr("Proposer un événement")); ?></div>
        <h1 style="margin:0 0 10px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:26px;line-height:1.1;color:#1D1D1B;letter-spacing:0.02em"><?php echo esc_html($tr("Organisateur ?")); ?></h1>
        <p style="margin:0 0 22px;font-family:'Nunito Sans',sans-serif;font-size:13px;line-height:1.55;color:#4A4A48"><?php echo esc_html($tr("Ajoutez votre événement gratuitement, nous le relisons avant publication.")); ?></p>
      </div>

      <?php if ($errors): ?>
        <div style="background:#FDEAEA;border:1px solid #B3261E;color:#B3261E;padding:12px 14px;margin-bottom:18px;font-family:'Nunito Sans',sans-serif;font-size:12.5px;line-height:1.6">
          <?php foreach ($errors as $e) echo '· ' . esc_html($e) . '<br>'; ?>
        </div>
      <?php endif; ?>

      <form method="post" enctype="multipart/form-data" style="display:flex;flex-direction:column;gap:16px;padding-bottom:24px">
        <?php wp_nonce_field('as_propose_event', 'as_propose_nonce'); ?>
        <input type="text" name="as_hp_check" value="" autocomplete="off" tabindex="-1" style="position:absolute;left:-9999px" aria-hidden="true">

        <label style="display:block">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.08em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px"><?php echo esc_html($tr("Titre de l'événement")); ?></div>
          <input type="text" name="as_title" required placeholder="<?php echo esc_attr($tr("Ex. Marché nocturne des artisans")); ?>" value="<?php echo esc_attr($_POST['as_title'] ?? ''); ?>" style="width:100%;box-sizing:border-box;padding:10px 12px;background:#fff;border:1px solid #E3DCCE;border-radius:3px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B">
        </label>

        <label style="display:block">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.08em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px"><?php echo esc_html($tr("Catégorie")); ?></div>
          <select name="as_category" style="width:100%;box-sizing:border-box;padding:10px 12px;background:#fff;border:1px solid #E3DCCE;border-radius:3px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B">
            <option value=""><?php echo esc_html($tr("Concerts &amp; Musique, Marchés, Expositions…")); ?></option>
            <?php foreach ($categories as $t): ?>
              <option value="<?php echo esc_attr($t->term_id); ?>"><?php echo esc_html($t->name); ?></option>
            <?php endforeach; ?>
          </select>
        </label>

        <label style="display:block">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.08em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px"><?php echo esc_html($tr("Territoire / ville")); ?></div>
          <select name="as_territoire" style="width:100%;box-sizing:border-box;padding:10px 12px;background:#fff;border:1px solid #E3DCCE;border-radius:3px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B">
            <option value=""><?php echo esc_html($tr("Savoie · Piémont · Vallée d'Aoste · Nice")); ?></option>
            <?php foreach ($territoires as $t): ?>
              <option value="<?php echo esc_attr($t->term_id); ?>"><?php echo esc_html($t->name); ?></option>
            <?php endforeach; ?>
          </select>
        </label>

        <label style="display:block">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.08em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px"><?php echo esc_html($tr("Dates et horaires")); ?></div>
          <input type="text" name="as_dates" required placeholder="<?php echo esc_attr($tr("Ex. 12–13 juillet 2026 · 18h–23h")); ?>" value="<?php echo esc_attr($_POST['as_dates'] ?? ''); ?>" style="width:100%;box-sizing:border-box;padding:10px 12px;background:#fff;border:1px solid #E3DCCE;border-radius:3px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B">
        </label>

        <label style="display:block">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.08em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px"><?php echo esc_html($tr("Lieu")); ?></div>
          <input type="text" name="as_lieu" required placeholder="<?php echo esc_attr($tr("Ex. Place du marché, Aoste")); ?>" value="<?php echo esc_attr($_POST['as_lieu'] ?? ''); ?>" style="width:100%;box-sizing:border-box;padding:10px 12px;background:#fff;border:1px solid #E3DCCE;border-radius:3px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B">
        </label>

        <label style="display:block">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.08em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px"><?php echo esc_html($tr("Description")); ?></div>
          <textarea name="as_description" rows="4" placeholder="<?php echo esc_attr($tr("Quelques lignes sur l'événement, son intérêt, le public visé…")); ?>" style="width:100%;box-sizing:border-box;padding:10px 12px;background:#fff;border:1px solid #E3DCCE;border-radius:3px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B"><?php echo esc_textarea($_POST['as_description'] ?? ''); ?></textarea>
        </label>

        <label style="display:block">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.08em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px"><?php echo esc_html($tr("Lien billetterie (facultatif)")); ?></div>
          <input type="url" name="as_billetterie" placeholder="https://…" value="<?php echo esc_attr($_POST['as_billetterie'] ?? ''); ?>" style="width:100%;box-sizing:border-box;padding:10px 12px;background:#fff;border:1px solid #E3DCCE;border-radius:3px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B">
        </label>

        <label style="display:block">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.08em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px"><?php echo esc_html($tr("Photo (1)")); ?></div>
          <input type="file" name="as_photo" accept="image/jpeg,image/png,image/webp" style="width:100%;box-sizing:border-box;padding:16px 12px;background:#fff;border:1px dashed #C9C4B8;border-radius:3px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#6F6B62">
        </label>

        <label style="display:block">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.08em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px"><?php echo esc_html($tr("Votre e-mail")); ?></div>
          <input type="email" name="as_email" required placeholder="<?php echo esc_attr($tr("Pour vous recontacter si besoin")); ?>" value="<?php echo esc_attr($_POST['as_email'] ?? ''); ?>" style="width:100%;box-sizing:border-box;padding:10px 12px;background:#fff;border:1px solid #E3DCCE;border-radius:3px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B">
        </label>

        <label style="display:flex;align-items:flex-start;gap:10px;cursor:pointer">
          <input type="checkbox" name="as_consent" required style="width:16px;height:16px;flex-shrink:0;margin:1px 0 0">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:12px;line-height:1.5;color:#4A4A48"><?php echo esc_html($tr("J'accepte que ces informations soient utilisées pour l'examen et la publication de cet événement, conformément à la politique de confidentialité.")); ?></div>
        </label>

        <button type="submit" style="display:block;width:100%;text-align:center;background:#1D1D1B;color:#F7F1E8;border:0;cursor:pointer;padding:13px 0;font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:800;letter-spacing:0.02em"><?php echo esc_html($tr("Envoyer pour validation")); ?></button>
        <div style="font-family:'Nunito Sans',sans-serif;font-size:11.5px;line-height:1.6;color:#6F6B62"><?php echo esc_html($tr("Aucune information n'est publiée avant vérification par la rédaction.")); ?></div>
      </form>

    <?php endif; ?>

    <?php $cs_in = "width:100%;box-sizing:border-box;padding:10px 12px;background:#fff;border:1px solid #E3DCCE;border-radius:3px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B"; $cs_lbl = "font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.08em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px"; ?>
    <div id="source" style="border-top:2px solid #1D1D1B;margin:8px 0 32px;padding-top:22px">
      <?php if ($src_submitted): ?>
        <div style="padding:16px 0 8px;text-align:center">
          <h2 style="margin:0 0 8px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:22px;line-height:1.15;color:#1D1D1B"><?php echo esc_html($tr('Merci, la source est bien reçue')); ?></h2>
          <p style="margin:0;font-family:'Nunito Sans',sans-serif;font-size:13.5px;line-height:1.55;color:#4A4A48"><?php echo esc_html($tr('Nous la vérifions avant de l’ajouter à notre veille.')); ?></p>
        </div>
      <?php else: ?>
        <h2 style="margin:0 0 8px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:22px;line-height:1.1;color:#1D1D1B;letter-spacing:0.02em"><?php echo esc_html($tr('Vous publiez un agenda ?')); ?></h2>
        <p style="margin:0 0 18px;font-family:'Nunito Sans',sans-serif;font-size:13px;line-height:1.55;color:#4A4A48"><?php echo esc_html($tr("Envoyez-nous votre flux RSS ou le lien d'inscription à votre newsletter : nous le relisons et l'ajoutons à nos sources.")); ?></p>
        <?php if ($src_errors): ?>
          <div style="background:#FDEAEA;border:1px solid #B3261E;color:#B3261E;padding:12px 14px;margin-bottom:18px;font-family:'Nunito Sans',sans-serif;font-size:12.5px;line-height:1.6"><?php foreach ($src_errors as $se) echo '· ' . esc_html($se) . '<br>'; ?></div>
        <?php endif; ?>
        <form method="post" action="#source" style="display:flex;flex-direction:column;gap:16px">
          <?php wp_nonce_field('as_propose_source', 'as_source_nonce'); ?>
          <input type="text" name="as_hp_check" value="" autocomplete="off" tabindex="-1" style="position:absolute;left:-9999px" aria-hidden="true">
          <label style="display:block"><div style="<?php echo $cs_lbl; ?>"><?php echo esc_html($tr('Type de source')); ?></div>
            <select name="as_source_type" style="<?php echo $cs_in; ?>">
              <option value="rss"><?php echo esc_html($tr('Flux RSS')); ?></option>
              <option value="newsletter"><?php echo esc_html($tr('Newsletter (lien d’inscription)')); ?></option>
              <option value="autre"><?php echo esc_html($tr('Autre / je ne sais pas')); ?></option>
            </select></label>
          <label style="display:block"><div style="<?php echo $cs_lbl; ?>"><?php echo esc_html($tr('Adresse du flux ou de la page d’inscription')); ?></div>
            <input type="url" name="as_source_url" required placeholder="https://…" value="<?php echo esc_attr($_POST['as_source_url'] ?? ''); ?>" style="<?php echo $cs_in; ?>"></label>
          <label style="display:block"><div style="<?php echo $cs_lbl; ?>"><?php echo esc_html($tr('Organisme (facultatif)')); ?></div>
            <input type="text" name="as_source_org" placeholder="<?php echo esc_attr($tr('Ex. Office de tourisme de Chambéry')); ?>" value="<?php echo esc_attr($_POST['as_source_org'] ?? ''); ?>" style="<?php echo $cs_in; ?>"></label>
          <label style="display:block"><div style="<?php echo $cs_lbl; ?>"><?php echo esc_html($tr('Votre e-mail')); ?></div>
            <input type="email" name="as_source_email" required placeholder="<?php echo esc_attr($tr('Pour vous recontacter si besoin')); ?>" value="<?php echo esc_attr($_POST['as_source_email'] ?? ''); ?>" style="<?php echo $cs_in; ?>"></label>
          <label style="display:flex;align-items:flex-start;gap:10px;cursor:pointer"><input type="checkbox" name="as_source_consent" required style="width:16px;height:16px;flex-shrink:0;margin:1px 0 0"><div style="font-family:'Nunito Sans',sans-serif;font-size:12px;line-height:1.5;color:#4A4A48"><?php echo esc_html($tr("J'accepte que ces informations soient utilisées pour l'examen et la publication de cet événement, conformément à la politique de confidentialité.")); ?></div></label>
          <button type="submit" style="display:block;width:100%;text-align:center;background:#1D1D1B;color:#F7F1E8;border:0;cursor:pointer;padding:13px 0;font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:800;letter-spacing:0.02em"><?php echo esc_html($tr('Proposer cette source')); ?></button>
        </form>
      <?php endif; ?>
    </div>

    </div>
    <?php
    get_footer();
    exit;
});
