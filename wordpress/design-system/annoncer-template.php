<?php
/**
 * "Annoncer sur Agenda Sabauda" (page 995, brouillon — pas encore publiée,
 * cf. STATUS.md) — page commerciale B2B, fidèle à
 * "Agenda Sabaudo - Annoncer.dc.html" (lue le 2026-07-13) : accroche,
 * bénéfices, atouts, offre de lancement, formulaire de contact.
 *
 * Contrairement à "Proposer un événement" (qui crée un brouillon éditorial
 * à réviser), une demande publicitaire n'a pas vocation à devenir du
 * contenu WP — chaque soumission envoie un e-mail via `wp_mail()` à
 * l'adresse de contact du site, sans rien stocker en base.
 */
add_action('template_redirect', function () {
    if (is_admin() || !is_page(995)) {
        return;
    }

    $errors = [];
    $submitted = false;

    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['as_annoncer_nonce'])) {
        if (!wp_verify_nonce($_POST['as_annoncer_nonce'], 'as_annoncer')) {
            $errors[] = "Le formulaire a expiré, merci de réessayer.";
        } elseif (!empty($_POST['as_hp_check'])) {
            $submitted = true;
        } else {
            $nom = sanitize_text_field($_POST['as_nom'] ?? '');
            $structure = sanitize_text_field($_POST['as_structure'] ?? '');
            $email = sanitize_email($_POST['as_email'] ?? '');
            $telephone = sanitize_text_field($_POST['as_telephone'] ?? '');
            $type_demande = sanitize_text_field($_POST['as_type_demande'] ?? '');
            $territoires = array_map('sanitize_text_field', (array) ($_POST['as_territoires'] ?? []));
            $message = sanitize_textarea_field($_POST['as_message'] ?? '');
            $consent = !empty($_POST['as_consent']);

            if ($nom === '') $errors[] = "Le nom est requis.";
            if ($email === '' || !is_email($email)) $errors[] = "Une adresse e-mail valide est requise.";
            if (!$consent) $errors[] = "Merci d'accepter l'utilisation de ces informations pour valider l'envoi.";

            if (empty($errors)) {
                $body = "Nouvelle demande publicitaire via agendasabauda.eu\n\n"
                    . "Nom : {$nom}\n"
                    . "Structure : {$structure}\n"
                    . "E-mail : {$email}\n"
                    . "Téléphone : {$telephone}\n"
                    . "Type de demande : {$type_demande}\n"
                    . "Territoire(s) : " . implode(', ', $territoires) . "\n\n"
                    . "Message :\n{$message}";

                $sent = wp_mail(
                    'contact@culturasabauda.eu',
                    'Demande publicitaire — ' . $nom,
                    $body,
                    ['Reply-To: ' . $email]
                );

                if (!$sent) {
                    $errors[] = "L'envoi a échoué, merci de réessayer ou d'écrire directement à contact@agendasabauda.eu.";
                } else {
                    $submitted = true;
                }
            }
        }
    }

    get_header();
    ?>
    <div style="max-width:560px;margin:0 auto;padding:0 20px">

    <?php if ($submitted): ?>

      <div style="padding:60px 0;text-align:center">
        <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="#1D1D1B" stroke-width="1.6" style="margin-bottom:18px"><circle cx="12" cy="12" r="9.5"></circle><polyline points="8 12.5 11 15.5 16 9"></polyline></svg>
        <h1 style="margin:0 0 10px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:26px;line-height:1.15;color:#1D1D1B;letter-spacing:0.02em">Merci</h1>
        <p style="margin:0;font-family:'Nunito Sans',sans-serif;font-size:14px;line-height:1.6;color:#4A4A48">Nous revenons vers vous avec nos formats et nos tarifs.</p>
      </div>

    <?php else: ?>

      <div style="padding:22px 0 0">
        <h1 style="margin:0 0 10px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:28px;line-height:1.12;color:#1D1D1B;letter-spacing:0.02em">Annoncer sur Agenda Sabauda</h1>
        <p style="margin:0;font-family:'Nunito Sans',sans-serif;font-size:14px;line-height:1.6;color:#4A4A48">L'agenda culturel transfrontalier des Alpes : mettez-vous devant une audience qui cherche quoi faire près de chez elle.</p>
      </div>

      <div style="padding:26px 0 0">
        <div style="font-family:'Nunito Sans',sans-serif;font-size:10px;font-weight:700;letter-spacing:0.18em;color:#1D1D1B;text-transform:uppercase;border-top:1px solid #1D1D1B;padding-top:12px;margin-bottom:16px">Ce qu'annoncer chez nous vous apporte</div>

        <?php
        $benefices = [
            ['Une audience qualifiée', 'Des lecteurs qui planifient activement une sortie, un week-end, une visite.'],
            ['Un ciblage géographique fin', "Par ville, par territoire ou sur l'ensemble des quatre bassins."],
            ['Un positionnement transfrontalier', 'Contenus natifs FR et IT, sans traduction automatique.'],
            ['Plusieurs formats', "Mise en avant d'événement, display, article partenaire, newsletter, réseaux."],
            ['Un cadre éditorial de confiance', 'Chaque emplacement reste identifié et distinct des contenus rédactionnels.'],
        ];
        foreach ($benefices as [$titre, $texte]): ?>
        <div style="display:flex;gap:14px;margin-bottom:18px">
          <div style="width:26px;height:26px;flex-shrink:0;border:1.5px solid #1D1D1B;border-radius:50%"></div>
          <div>
            <div style="font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:15.5px;color:#1D1D1B;margin-bottom:3px"><?php echo esc_html($titre); ?></div>
            <div style="font-family:'Nunito Sans',sans-serif;font-size:13px;line-height:1.5;color:#4A4A48"><?php echo esc_html($texte); ?></div>
          </div>
        </div>
        <?php endforeach; ?>
      </div>

      <div style="padding:24px 0 0">
        <div style="font-family:'Nunito Sans',sans-serif;font-size:10px;font-weight:700;letter-spacing:0.18em;color:#1D1D1B;text-transform:uppercase;border-top:1px solid #1D1D1B;padding-top:12px;margin-bottom:14px">Nos atouts</div>
        <ul style="margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:10px">
          <?php foreach ([
              'Une niche défendable : aucun média équivalent sur ce territoire précis',
              'Une audience fidélisée par la newsletter hebdomadaire',
              'Des contenus vérifiés, bilingues, tenus à jour par la rédaction',
              'Un interlocuteur direct, pas de plateforme automatisée',
          ] as $atout): ?>
          <li style="font-family:'Nunito Sans',sans-serif;font-size:13.5px;line-height:1.5;color:#1D1D1B;padding-left:16px;position:relative"><span style="position:absolute;left:0;color:#DC5D45">·</span><?php echo esc_html($atout); ?></li>
          <?php endforeach; ?>
        </ul>
      </div>

      <div style="padding:22px 0 0">
        <div style="border:1.5px solid #DC5D45;padding:16px 18px">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:10px;font-weight:800;letter-spacing:0.12em;color:#DC5D45;text-transform:uppercase;margin-bottom:8px">Offre de lancement</div>
          <div style="font-family:'Nunito Sans',sans-serif;font-size:13.5px;line-height:1.55;color:#1D1D1B">Partenaire des débuts : conditions préférentielles et visibilité renforcée.</div>
        </div>
      </div>

      <?php if ($errors): ?>
        <div style="background:#FDEAEA;border:1px solid #B3261E;color:#B3261E;padding:12px 14px;margin-top:22px;font-family:'Nunito Sans',sans-serif;font-size:12.5px;line-height:1.6">
          <?php foreach ($errors as $e) echo '· ' . esc_html($e) . '<br>'; ?>
        </div>
      <?php endif; ?>

      <form method="post" style="padding:26px 0 24px">
        <div style="font-family:'Nunito Sans',sans-serif;font-size:10px;font-weight:700;letter-spacing:0.18em;color:#1D1D1B;text-transform:uppercase;border-top:1px solid #1D1D1B;padding-top:12px;margin-bottom:18px">Nous contacter</div>

        <?php wp_nonce_field('as_annoncer', 'as_annoncer_nonce'); ?>
        <input type="text" name="as_hp_check" value="" autocomplete="off" tabindex="-1" style="position:absolute;left:-9999px" aria-hidden="true">

        <div style="display:flex;flex-direction:column;gap:16px">
          <label style="display:block">
            <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.06em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px">Nom</div>
            <input type="text" name="as_nom" required placeholder="Votre nom" value="<?php echo esc_attr($_POST['as_nom'] ?? ''); ?>" style="width:100%;box-sizing:border-box;padding:12px 14px;background:#fff;border:1px solid #E3DCCE;font-family:'Nunito Sans',sans-serif;font-size:14px;color:#1D1D1B">
          </label>
          <label style="display:block">
            <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.06em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px">Structure / organisation</div>
            <input type="text" name="as_structure" placeholder="Nom de votre structure" value="<?php echo esc_attr($_POST['as_structure'] ?? ''); ?>" style="width:100%;box-sizing:border-box;padding:12px 14px;background:#fff;border:1px solid #E3DCCE;font-family:'Nunito Sans',sans-serif;font-size:14px;color:#1D1D1B">
          </label>
          <label style="display:block">
            <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.06em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px">E-mail</div>
            <input type="email" name="as_email" required placeholder="vous@exemple.com" value="<?php echo esc_attr($_POST['as_email'] ?? ''); ?>" style="width:100%;box-sizing:border-box;padding:12px 14px;background:#fff;border:1px solid #E3DCCE;font-family:'Nunito Sans',sans-serif;font-size:14px;color:#1D1D1B">
          </label>
          <label style="display:block">
            <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.06em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px">Téléphone (facultatif)</div>
            <input type="tel" name="as_telephone" placeholder="+33 …" value="<?php echo esc_attr($_POST['as_telephone'] ?? ''); ?>" style="width:100%;box-sizing:border-box;padding:12px 14px;background:#fff;border:1px solid #E3DCCE;font-family:'Nunito Sans',sans-serif;font-size:14px;color:#1D1D1B">
          </label>

          <label style="display:block">
            <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.06em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px">Type de demande</div>
            <select name="as_type_demande" style="width:100%;box-sizing:border-box;padding:12px 14px;background:#fff;border:1px solid #E3DCCE;font-family:'Nunito Sans',sans-serif;font-size:14px;color:#1D1D1B">
              <option value="">Choisir…</option>
              <option value="Mise en avant d'événement">Mise en avant d'événement</option>
              <option value="Display">Display</option>
              <option value="Article partenaire">Article partenaire</option>
              <option value="Newsletter">Newsletter</option>
              <option value="Réseaux sociaux">Réseaux sociaux</option>
              <option value="Autre">Autre</option>
            </select>
          </label>

          <div>
            <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.06em;color:#1D1D1B;text-transform:uppercase;margin-bottom:10px">Territoire(s)</div>
            <div style="display:flex;flex-direction:column;gap:10px">
              <?php foreach (['Savoie', 'Haute-Savoie', 'Piémont', "Vallée d'Aoste", 'Nice'] as $t): ?>
              <label style="display:flex;align-items:center;gap:10px;cursor:pointer;min-height:22px">
                <input type="checkbox" name="as_territoires[]" value="<?php echo esc_attr($t); ?>" style="width:20px;height:20px;flex-shrink:0">
                <div style="font-family:'Nunito Sans',sans-serif;font-size:14px;color:#1D1D1B"><?php echo esc_html($t); ?></div>
              </label>
              <?php endforeach; ?>
            </div>
          </div>

          <label style="display:block">
            <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.06em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px">Message</div>
            <textarea name="as_message" rows="4" placeholder="Parlez-nous de votre projet, vos échéances, vos objectifs…" style="width:100%;box-sizing:border-box;padding:12px 14px;background:#fff;border:1px solid #E3DCCE;font-family:'Nunito Sans',sans-serif;font-size:14px;color:#1D1D1B"><?php echo esc_textarea($_POST['as_message'] ?? ''); ?></textarea>
          </label>
        </div>

        <label style="display:flex;align-items:flex-start;gap:10px;margin-top:20px;cursor:pointer">
          <input type="checkbox" name="as_consent" required style="width:20px;height:20px;flex-shrink:0;margin-top:1px">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:12.5px;line-height:1.55;color:#4A4A48">J'accepte que ces informations soient utilisées pour traiter ma demande, conformément à la politique de confidentialité.</div>
        </label>

        <button type="submit" style="display:block;width:100%;text-align:center;margin-top:22px;background:#1D1D1B;color:#F7F1E8;border:0;cursor:pointer;padding:15px 0;font-family:'Nunito Sans',sans-serif;font-size:14px;font-weight:800;letter-spacing:0.02em">Envoyer</button>

        <div style="margin-top:16px;font-family:'Nunito Sans',sans-serif;font-size:12.5px;line-height:1.6;color:#6F6B62;text-align:center">ou écrivez-nous à <a href="mailto:contact@culturasabauda.eu" style="color:#1D1D1B;text-decoration:underline">contact@culturasabauda.eu</a></div>
      </form>

    <?php endif; ?>

    </div>
    <?php
    get_footer();
    exit;
});
