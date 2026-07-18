<?php
/**
 * "Contact" (page 1699, brouillon — pas encore publiée, cf. STATUS.md) —
 * page minimale mais réelle : adresse e-mail de contact + court formulaire.
 *
 * Même logique anti-spam/nonce/envoi que "Annoncer" (page 995,
 * annoncer-template.php, déjà vérifié en prod) : honeypot + nonce, pas de
 * stockage WP, chaque soumission envoie un e-mail via `wp_mail()` vers
 * contact@culturasabauda.eu.
 */
add_action('template_redirect', function () {
    if (is_admin() || !is_page(1699)) {
        return;
    }

    $errors = [];
    $submitted = false;

    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['as_contact_nonce'])) {
        if (!wp_verify_nonce($_POST['as_contact_nonce'], 'as_contact')) {
            $errors[] = "Le formulaire a expiré, merci de réessayer.";
        } elseif (!empty($_POST['as_hp_check'])) {
            $submitted = true;
        } else {
            $nom = sanitize_text_field($_POST['as_nom'] ?? '');
            $email = sanitize_email($_POST['as_email'] ?? '');
            $message = sanitize_textarea_field($_POST['as_message'] ?? '');

            if ($nom === '') $errors[] = "Le nom est requis.";
            if ($email === '' || !is_email($email)) $errors[] = "Une adresse e-mail valide est requise.";
            if ($message === '') $errors[] = "Le message est requis.";

            if (empty($errors)) {
                $body = "Nouveau message via le formulaire de contact d'agendasabauda.eu\n\n"
                    . "Nom : {$nom}\n"
                    . "E-mail : {$email}\n\n"
                    . "Message :\n{$message}";

                $sent = wp_mail(
                    'contact@culturasabauda.eu',
                    'Message de contact — ' . $nom,
                    $body,
                    ['Reply-To: ' . $email]
                );

                if (!$sent) {
                    $errors[] = "L'envoi a échoué, merci de réessayer ou d'écrire directement à contact@culturasabauda.eu.";
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
        <p style="margin:0;font-family:'Nunito Sans',sans-serif;font-size:14px;line-height:1.6;color:#4A4A48">Votre message a bien été envoyé, nous vous répondrons rapidement.</p>
      </div>

    <?php else: ?>

      <div style="padding:22px 0 0">
        <h1 style="margin:0 0 10px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:28px;line-height:1.12;color:#1D1D1B;letter-spacing:0.02em">Contact</h1>
        <p style="margin:0;font-family:'Nunito Sans',sans-serif;font-size:14px;line-height:1.6;color:#4A4A48">Une question, un signalement, une suggestion ? Écrivez-nous directement ou passez par le formulaire ci-dessous.</p>
      </div>

      <div style="padding:24px 0 0">
        <div style="border:1px solid #E3DCCE;background:#fff;padding:16px 18px;display:flex;align-items:center;gap:12px">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#DC5D45" stroke-width="1.8" style="flex-shrink:0"><path d="M3 5h18v14H3z"></path><path d="M3 6l9 7 9-7"></path></svg>
          <a href="mailto:contact@culturasabauda.eu" style="font-family:'Nunito Sans',sans-serif;font-size:14px;font-weight:700;color:#1D1D1B;text-decoration:none">contact@culturasabauda.eu</a>
        </div>
      </div>

      <?php if ($errors): ?>
        <div style="background:#FDEAEA;border:1px solid #B3261E;color:#B3261E;padding:12px 14px;margin-top:22px;font-family:'Nunito Sans',sans-serif;font-size:12.5px;line-height:1.6">
          <?php foreach ($errors as $e) echo '· ' . esc_html($e) . '<br>'; ?>
        </div>
      <?php endif; ?>

      <form method="post" style="padding:26px 0 24px">
        <div style="font-family:'Nunito Sans',sans-serif;font-size:10px;font-weight:700;letter-spacing:0.18em;color:#1D1D1B;text-transform:uppercase;border-top:1px solid #1D1D1B;padding-top:12px;margin-bottom:18px">Nous écrire</div>

        <?php wp_nonce_field('as_contact', 'as_contact_nonce'); ?>
        <input type="text" name="as_hp_check" value="" autocomplete="off" tabindex="-1" style="position:absolute;left:-9999px" aria-hidden="true">

        <div style="display:flex;flex-direction:column;gap:16px">
          <label style="display:block">
            <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.06em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px">Nom</div>
            <input type="text" name="as_nom" required placeholder="Votre nom" value="<?php echo esc_attr($_POST['as_nom'] ?? ''); ?>" style="width:100%;box-sizing:border-box;padding:12px 14px;background:#fff;border:1px solid #E3DCCE;font-family:'Nunito Sans',sans-serif;font-size:14px;color:#1D1D1B">
          </label>
          <label style="display:block">
            <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.06em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px">E-mail</div>
            <input type="email" name="as_email" required placeholder="vous@exemple.com" value="<?php echo esc_attr($_POST['as_email'] ?? ''); ?>" style="width:100%;box-sizing:border-box;padding:12px 14px;background:#fff;border:1px solid #E3DCCE;font-family:'Nunito Sans',sans-serif;font-size:14px;color:#1D1D1B">
          </label>
          <label style="display:block">
            <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.06em;color:#1D1D1B;text-transform:uppercase;margin-bottom:6px">Message</div>
            <textarea name="as_message" required rows="5" placeholder="Votre message…" style="width:100%;box-sizing:border-box;padding:12px 14px;background:#fff;border:1px solid #E3DCCE;font-family:'Nunito Sans',sans-serif;font-size:14px;color:#1D1D1B"><?php echo esc_textarea($_POST['as_message'] ?? ''); ?></textarea>
          </label>
        </div>

        <button type="submit" style="display:block;width:100%;text-align:center;margin-top:22px;background:#1D1D1B;color:#F7F1E8;border:0;cursor:pointer;padding:15px 0;font-family:'Nunito Sans',sans-serif;font-size:14px;font-weight:800;letter-spacing:0.02em">Envoyer</button>
      </form>

    <?php endif; ?>

    </div>
    <?php
    get_footer();
    exit;
});
