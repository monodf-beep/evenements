<?php
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
    if (is_admin() || !is_page(934)) {
        return;
    }

    $errors = [];
    $submitted = false;

    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['as_propose_nonce'])) {
        if (!wp_verify_nonce($_POST['as_propose_nonce'], 'as_propose_event')) {
            $errors[] = "Le formulaire a expiré, merci de réessayer.";
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

            if ($title === '') $errors[] = "Le titre de l'événement est requis.";
            if ($dates === '') $errors[] = "Les dates et horaires sont requis.";
            if ($lieu === '') $errors[] = "Le lieu est requis.";
            if ($email === '' || !is_email($email)) $errors[] = "Une adresse e-mail valide est requise.";
            if (!$consent) $errors[] = "Merci d'accepter l'utilisation de ces informations pour valider l'envoi.";

            $photo_id = 0;
            if (empty($errors) && !empty($_FILES['as_photo']['name'])) {
                require_once ABSPATH . 'wp-admin/includes/image.php';
                require_once ABSPATH . 'wp-admin/includes/file.php';
                require_once ABSPATH . 'wp-admin/includes/media.php';
                $allowed = ['jpg' => 'image/jpeg', 'jpeg' => 'image/jpeg', 'png' => 'image/png', 'webp' => 'image/webp'];
                $photo_id = media_handle_upload('as_photo', 0, [], ['mimes' => $allowed, 'test_form' => false]);
                if (is_wp_error($photo_id)) {
                    $errors[] = "La photo n'a pas pu être envoyée (" . esc_html($photo_id->get_error_message()) . ").";
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
                    $errors[] = "L'enregistrement a échoué, merci de réessayer.";
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
        <h1 style="margin:0 0 10px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:26px;line-height:1.15;color:#1D1D1B;letter-spacing:0.02em">Merci pour votre proposition</h1>
        <p style="margin:0 0 4px;font-family:'Nunito Sans',sans-serif;font-size:13.5px;line-height:1.55;color:#4A4A48">Nous relisons chaque événement sous 5 jours ouvrés.</p>
        <p style="margin:0;font-family:'Nunito Sans',sans-serif;font-size:13.5px;line-height:1.55;color:#4A4A48">Rien n'est publié sans vérification par la rédaction.</p>
      </div>

    <?php else: ?>

      <div style="padding:24px 0 12px">
        <div style="font-family:'Nunito Sans',sans-serif;font-size:10px;font-weight:700;letter-spacing:0.18em;color:#DC5D45;text-transform:uppercase;margin-bottom:8px">Proposer un événement</div>
        <h1 style="margin:0 0 10px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:26px;line-height:1.1;color:#1D1D1B;letter-spacing:0.02em">Organisateur ?</h1>
        <p style="margin:0 0 22px;font-family:'Nunito Sans',sans-serif;font-size:13px;line-height:1.55;color:#4A4A48">Ajoutez votre événement gratuitement, nous le relisons avant publication.</p>
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
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.08em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px">Titre de l'événement</div>
          <input type="text" name="as_title" required placeholder="Ex. Marché nocturne des artisans" value="<?php echo esc_attr($_POST['as_title'] ?? ''); ?>" style="width:100%;box-sizing:border-box;padding:10px 12px;background:#fff;border:1px solid #E3DCCE;border-radius:3px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B">
        </label>

        <label style="display:block">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.08em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px">Catégorie</div>
          <select name="as_category" style="width:100%;box-sizing:border-box;padding:10px 12px;background:#fff;border:1px solid #E3DCCE;border-radius:3px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B">
            <option value="">Concerts &amp; Musique, Marchés, Expositions…</option>
            <?php foreach ($categories as $t): ?>
              <option value="<?php echo esc_attr($t->term_id); ?>"><?php echo esc_html($t->name); ?></option>
            <?php endforeach; ?>
          </select>
        </label>

        <label style="display:block">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.08em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px">Territoire / ville</div>
          <select name="as_territoire" style="width:100%;box-sizing:border-box;padding:10px 12px;background:#fff;border:1px solid #E3DCCE;border-radius:3px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B">
            <option value="">Savoie · Piémont · Vallée d'Aoste · Nice</option>
            <?php foreach ($territoires as $t): ?>
              <option value="<?php echo esc_attr($t->term_id); ?>"><?php echo esc_html($t->name); ?></option>
            <?php endforeach; ?>
          </select>
        </label>

        <label style="display:block">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.08em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px">Dates et horaires</div>
          <input type="text" name="as_dates" required placeholder="Ex. 12–13 juillet 2026 · 18h–23h" value="<?php echo esc_attr($_POST['as_dates'] ?? ''); ?>" style="width:100%;box-sizing:border-box;padding:10px 12px;background:#fff;border:1px solid #E3DCCE;border-radius:3px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B">
        </label>

        <label style="display:block">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.08em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px">Lieu</div>
          <input type="text" name="as_lieu" required placeholder="Ex. Place du marché, Aoste" value="<?php echo esc_attr($_POST['as_lieu'] ?? ''); ?>" style="width:100%;box-sizing:border-box;padding:10px 12px;background:#fff;border:1px solid #E3DCCE;border-radius:3px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B">
        </label>

        <label style="display:block">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.08em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px">Description</div>
          <textarea name="as_description" rows="4" placeholder="Quelques lignes sur l'événement, son intérêt, le public visé…" style="width:100%;box-sizing:border-box;padding:10px 12px;background:#fff;border:1px solid #E3DCCE;border-radius:3px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B"><?php echo esc_textarea($_POST['as_description'] ?? ''); ?></textarea>
        </label>

        <label style="display:block">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.08em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px">Lien billetterie (facultatif)</div>
          <input type="url" name="as_billetterie" placeholder="https://…" value="<?php echo esc_attr($_POST['as_billetterie'] ?? ''); ?>" style="width:100%;box-sizing:border-box;padding:10px 12px;background:#fff;border:1px solid #E3DCCE;border-radius:3px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B">
        </label>

        <label style="display:block">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.08em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px">Photo (1)</div>
          <input type="file" name="as_photo" accept="image/jpeg,image/png,image/webp" style="width:100%;box-sizing:border-box;padding:16px 12px;background:#fff;border:1px dashed #C9C4B8;border-radius:3px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#6F6B62">
        </label>

        <label style="display:block">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.08em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px">Votre e-mail</div>
          <input type="email" name="as_email" required placeholder="Pour vous recontacter si besoin" value="<?php echo esc_attr($_POST['as_email'] ?? ''); ?>" style="width:100%;box-sizing:border-box;padding:10px 12px;background:#fff;border:1px solid #E3DCCE;border-radius:3px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B">
        </label>

        <label style="display:flex;align-items:flex-start;gap:10px;cursor:pointer">
          <input type="checkbox" name="as_consent" required style="width:16px;height:16px;flex-shrink:0;margin:1px 0 0">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:12px;line-height:1.5;color:#4A4A48">J'accepte que ces informations soient utilisées pour l'examen et la publication de cet événement, conformément à la politique de confidentialité.</div>
        </label>

        <button type="submit" style="display:block;width:100%;text-align:center;background:#1D1D1B;color:#F7F1E8;border:0;cursor:pointer;padding:13px 0;font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:800;letter-spacing:0.02em">Envoyer pour validation</button>
        <div style="font-family:'Nunito Sans',sans-serif;font-size:11.5px;line-height:1.6;color:#6F6B62">Aucune information n'est publiée avant vérification par la rédaction.</div>
      </form>

    <?php endif; ?>

    </div>
    <?php
    get_footer();
    exit;
});
