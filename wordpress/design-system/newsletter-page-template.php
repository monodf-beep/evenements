<?php
/**
 * "Newsletter" (page 1703, brouillon vide — créée par la structure de base) —
 * page minimale d'inscription. Reprend le pattern d'inscription déjà utilisé
 * en bas des Hubs territoire/catégorie (cf. taxonomy-archive-template.php :
 * bloc fond #FBF7F0, input e-mail + bouton texte rouge #DC5D45 « S'inscrire »),
 * ici en page dédiée avec H1 + courte intro éditoriale.
 *
 * Formulaire volontairement cosmétique en v1 : aucun fournisseur newsletter
 * n'est configuré côté outils ce soir (pas de connecteur Brevo/Mailchimp
 * disponible). Le POST est intercepté et affiche un état "Merci" mais
 * n'envoie rien nulle part — voir le TODO ci-dessous.
 */
add_action('template_redirect', function () {
    if (is_admin() || !is_page(1703)) {
        return;
    }

    $submitted = false;
    $errors = [];

    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['as_newsletter_nonce'])) {
        if (!wp_verify_nonce($_POST['as_newsletter_nonce'], 'as_newsletter')) {
            $errors[] = "Le formulaire a expiré, merci de réessayer.";
        } elseif (!empty($_POST['as_hp_check'])) {
            // Honeypot rempli par un bot : on affiche quand même "Merci" pour ne pas l'alerter.
            $submitted = true;
        } else {
            $email = sanitize_email($_POST['as_email'] ?? '');
            if ($email === '' || !is_email($email)) {
                $errors[] = "Une adresse e-mail valide est requise.";
            } else {
                // TODO: brancher un vrai fournisseur newsletter (Brevo/Mailchimp)
                // quand le compte sera configuré. Pour l'instant, l'e-mail saisi
                // n'est ni stocké ni transmis — le formulaire est cosmétique.
                $submitted = true;
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
        <p style="margin:0;font-family:'Nunito Sans',sans-serif;font-size:14px;line-height:1.6;color:#4A4A48">Votre inscription est enregistrée. À très vite dans votre boîte mail.</p>
      </div>

    <?php else: ?>

      <div style="padding:22px 0 0">
        <h1 style="margin:0 0 10px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:28px;line-height:1.12;color:#1D1D1B;letter-spacing:0.02em">Newsletter</h1>
        <p style="margin:0;font-family:'Nunito Sans',sans-serif;font-size:14px;line-height:1.6;color:#4A4A48">Chaque semaine, la sélection Agenda Sabauda dans votre boîte mail : ce qu'il ne faut pas manquer sur les quatre territoires, de la Savoie à Nice en passant par le Piémont et la Vallée d'Aoste.</p>
      </div>

      <?php if ($errors): ?>
        <div style="background:#FDEAEA;border:1px solid #B3261E;color:#B3261E;padding:12px 14px;margin-top:22px;font-family:'Nunito Sans',sans-serif;font-size:12.5px;line-height:1.6">
          <?php foreach ($errors as $e) echo '· ' . esc_html($e) . '<br>'; ?>
        </div>
      <?php endif; ?>

      <div style="margin:26px 0 24px;background:#FBF7F0;padding:20px 18px">
        <div style="font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:700;color:#1D1D1B;margin-bottom:12px">S'inscrire à la newsletter</div>
        <form method="post" style="display:flex;border-bottom:1px solid #1D1D1B;padding-bottom:8px">
          <?php wp_nonce_field('as_newsletter', 'as_newsletter_nonce'); ?>
          <input type="text" name="as_hp_check" value="" autocomplete="off" tabindex="-1" style="position:absolute;left:-9999px" aria-hidden="true">
          <input type="email" name="as_email" required placeholder="Votre adresse e-mail" value="<?php echo esc_attr($_POST['as_email'] ?? ''); ?>" style="flex:1;min-width:0;border:0;background:transparent;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B">
          <button type="submit" style="border:0;background:transparent;font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:800;color:#DC5D45;cursor:pointer">S'inscrire</button>
        </form>
      </div>

      <p style="margin:0 0 40px;font-family:'Nunito Sans',sans-serif;font-size:11.5px;line-height:1.6;color:#6F6B62">Un e-mail par semaine, jamais revendue à des tiers. Désinscription en un clic à chaque envoi.</p>

    <?php endif; ?>

    </div>
    <?php
    get_footer();
    exit;
});
