<?php
/**
 * Fiche article "Le Fil" (native `post` WP) — rendu complet en PHP
 * (template_redirect), fidèle à "Agenda Sabaudo - Article.dc.html" (lue le
 * 2026-07-13) dans une version SCOPÉE v1 : le contenu éditorial, le fil
 * d'Ariane, les encadrés structurés (Quand/Où/Prix/Infos), la carte, "En
 * vedette", réseaux sociaux, recherche, newsletter et CTA pub sont repris.
 *
 * ⚠️ Scoping assumé : la maquette réelle a 8 blocs publicitaires/liens
 * sponsorisés quasi identiques, entièrement décoratifs à ce stade (aucune
 * régie pub réelle configurée). Un seul encadré "Publicité" représentatif
 * est gardé ici plutôt que de dupliquer les 8 — à revoir avec Franck une
 * fois une stratégie de monétisation réelle décidée (pas une perte
 * d'information : les 8 blocs de la maquette sont strictement identiques
 * en structure, juste répétés à différentes positions de scroll).
 *
 * Encadrés Quand/Où/Prix/Infos pilotés par des champs meta libres
 * (`as_article_quand`, `as_article_ou`, `as_article_prix`,
 * `as_article_infos`) — à saisir manuellement par la rédaction dans
 * l'éditeur natif WP (champs personnalisés), pas encore une vraie Meta Box
 * JetEngine (à faire si ce type de contenu est confirmé prioritaire).
 * N'affiche que les sections dont le champ est renseigné.
 */
add_action('template_redirect', function () {
    if (is_admin() || !is_single() || get_post_type() !== 'post') {
        return;
    }

    $post_id = get_the_ID();
    $categories = get_the_category($post_id);
    $primary_cat = $categories ? $categories[0] : null;

    $quand = get_post_meta($post_id, 'as_article_quand', true);
    $ou = get_post_meta($post_id, 'as_article_ou', true);
    $prix = get_post_meta($post_id, 'as_article_prix', true);
    $infos = get_post_meta($post_id, 'as_article_infos', true);

    $featured = new WP_Query([
        'post_type' => 'post',
        'post_status' => 'publish',
        'posts_per_page' => 2,
        'post__not_in' => [$post_id],
        'orderby' => 'date',
        'order' => 'DESC',
    ]);

    get_header();
    ?>
    <div style="max-width:700px;margin:0 auto;padding:0 20px">

      <div style="padding:12px 0 0;font-family:'Nunito Sans',sans-serif;font-size:11px;color:#6F6B62;line-height:1.6">
        <a href="<?php echo esc_url(home_url('/')); ?>" style="color:#6F6B62;text-decoration:none">Accueil</a>
        <?php if ($primary_cat): ?> &gt; <a href="<?php echo esc_url(get_category_link($primary_cat)); ?>" style="color:#6F6B62;text-decoration:none"><?php echo esc_html($primary_cat->name); ?></a><?php endif; ?>
      </div>

      <div style="padding:10px 0 0">
        <h1 style="margin:0;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:23px;line-height:1.22;color:#1D1D1B"><?php the_title(); ?></h1>
      </div>

      <?php if ($quand || $ou): ?>
      <div style="padding:14px 0 0">
        <div style="border-top:1px solid #E3DCCE;border-bottom:1px solid #E3DCCE;padding:11px 0;display:flex;flex-wrap:wrap;align-items:center;gap:8px 14px">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:9px;font-weight:800;letter-spacing:0.18em;text-transform:uppercase;color:#6F6B62">Dans cet article</div>
          <?php if ($quand): ?><a href="#as-quand" style="font-family:'Nunito Sans',sans-serif;font-size:12.5px;font-weight:700;color:#1D1D1B;text-decoration:none">Quand</a><?php endif; ?>
          <?php if ($ou): ?><a href="#as-ou" style="font-family:'Nunito Sans',sans-serif;font-size:12.5px;font-weight:700;color:#1D1D1B;text-decoration:none">Où &amp; prix</a><?php endif; ?>
          <?php if ($ou): ?><a href="#as-carte" style="font-family:'Nunito Sans',sans-serif;font-size:12.5px;font-weight:700;color:#1D1D1B;text-decoration:none">Carte</a><?php endif; ?>
        </div>
      </div>
      <?php endif; ?>

      <?php if (has_post_thumbnail($post_id)): ?>
      <div style="padding:16px 0 0">
        <div style="aspect-ratio:4/3;overflow:hidden;background:#1D1D1B"><?php echo get_the_post_thumbnail($post_id, 'large', ['style' => 'width:100%;height:100%;object-fit:cover']); ?></div>
      </div>
      <?php endif; ?>

      <div style="padding:18px 0 0;font-family:'Nunito Sans',sans-serif;font-size:14.5px;line-height:1.65;color:#1D1D1B">
        <?php the_content(); ?>
      </div>

      <?php if ($quand): ?>
      <div id="as-quand" style="padding:20px 0 0;scroll-margin-top:16px">
        <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.1em;color:#1D1D1B;text-transform:uppercase;margin-bottom:8px">Quand</div>
        <div style="font-family:'Nunito Sans',sans-serif;font-size:14px;color:#1D1D1B;line-height:1.7"><?php echo nl2br(esc_html($quand)); ?></div>
      </div>
      <?php endif; ?>

      <?php if ($ou || $prix || $infos): ?>
      <div id="as-ou" style="padding:20px 0 0;scroll-margin-top:16px">
        <?php if ($ou): ?>
        <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.1em;color:#1D1D1B;text-transform:uppercase;margin-bottom:8px">Où</div>
        <div style="font-family:'Nunito Sans',sans-serif;font-size:14px;color:#1D1D1B;line-height:1.6;margin-bottom:18px"><?php echo nl2br(esc_html($ou)); ?></div>
        <?php endif; ?>
        <?php if ($prix): ?>
        <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.1em;color:#1D1D1B;text-transform:uppercase;margin-bottom:8px">Prix</div>
        <div style="font-family:'Nunito Sans',sans-serif;font-size:14px;color:#1D1D1B;line-height:1.6;margin-bottom:18px"><?php echo esc_html($prix); ?></div>
        <?php endif; ?>
        <?php if ($infos): ?>
        <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.1em;color:#1D1D1B;text-transform:uppercase;margin-bottom:8px">Autres informations</div>
        <div style="font-family:'Nunito Sans',sans-serif;font-size:14px;margin-bottom:18px"><?php echo esc_html($infos); ?></div>
        <?php endif; ?>
        <?php if ($primary_cat): ?>
        <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.1em;color:#1D1D1B;text-transform:uppercase;margin-bottom:8px">Catégorie</div>
        <a href="<?php echo esc_url(get_category_link($primary_cat)); ?>" style="display:inline-block;font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:700;color:#DC5D45;text-decoration:underline"><?php echo esc_html($primary_cat->name); ?></a>
        <?php endif; ?>
      </div>
      <?php endif; ?>

      <?php if ($ou): ?>
      <div id="as-carte" style="padding:20px 0 0;scroll-margin-top:16px">
        <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.1em;color:#1D1D1B;text-transform:uppercase;margin-bottom:8px">Carte</div>
        <div style="aspect-ratio:16/11;background:#FBF7F0;border:1px solid #E3DCCE;display:flex;align-items:center;justify-content:center;position:relative">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#6F6B62" stroke-width="1.5"><path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"></path><circle cx="12" cy="9.5" r="2.3"></circle></svg>
          <a href="<?php echo esc_url('https://www.google.com/maps/search/?api=1&query=' . rawurlencode($ou)); ?>" target="_blank" rel="noopener" style="position:absolute;top:10px;left:10px;background:#F7F1E8;border:1px solid #1D1D1B;text-decoration:none;padding:5px 10px;font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:700;color:#1D1D1B">Ouvrir dans Maps ↗</a>
        </div>
      </div>
      <?php endif; ?>

      <div style="margin:24px 0 0;border:1px solid #E3DCCE">
        <div style="display:flex;justify-content:flex-end;padding:4px 8px 0"><div style="font-family:'Nunito Sans',sans-serif;font-size:8.5px;font-weight:700;color:#6F6B62;text-transform:uppercase;letter-spacing:0.08em">Publicité</div></div>
        <div style="aspect-ratio:5/2;background:#FBF7F0;display:flex;align-items:center;justify-content:center">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;color:#6F6B62">Emplacement publicitaire</div>
        </div>
      </div>

      <div style="padding:24px 0 0;display:flex;flex-direction:column;gap:12px">
        <a href="#" style="display:flex;align-items:center;justify-content:space-between;text-decoration:none;background:#FBF7F0;border:1px solid #1D1D1B;padding:16px 18px">
          <div style="font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:16px;color:#1D1D1B">Suivez-nous sur Instagram</div>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#1D1D1B" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="4"></rect><circle cx="12" cy="12" r="4"></circle><circle cx="17.5" cy="6.5" r="1"></circle></svg>
        </a>
        <a href="#" style="display:flex;align-items:center;justify-content:space-between;text-decoration:none;background:#FBF7F0;border:1px solid #1D1D1B;padding:16px 18px">
          <div style="font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:16px;color:#1D1D1B">Suivez-nous sur Facebook</div>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#1D1D1B" stroke-width="1.5"><path d="M15 4h-2a4 4 0 0 0-4 4v3H7v3h2v7h3v-7h2.5l.5-3H12V8a1 1 0 0 1 1-1h2z"></path></svg>
        </a>
      </div>

      <form role="search" method="get" action="<?php echo esc_url(home_url('/')); ?>" style="padding:20px 0 0;display:flex;gap:8px">
        <input type="search" name="s" placeholder="Rechercher…" style="flex:1;border:1px solid #1D1D1B;padding:11px 14px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B;background:transparent">
        <button type="submit" style="background:#1D1D1B;color:#F7F1E8;border:0;cursor:pointer;padding:11px 18px;font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:700">Chercher</button>
      </form>

      <div style="padding:20px 0 0">
        <div style="background:#DC5D45;padding:18px 20px">
          <div style="font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:17px;color:#F7F1E8;margin-bottom:10px">Recevez les dernières actualités de l'agenda</div>
          <a href="#" style="display:block;text-align:center;background:#F7F1E8;color:#1D1D1B;text-decoration:none;padding:11px 0;font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:800">S'inscrire à la newsletter</a>
        </div>
      </div>

      <div style="padding:20px 0 0">
        <a href="mailto:contact@culturasabauda.eu" style="display:flex;align-items:center;justify-content:space-between;text-decoration:none;background:#1D1D1B;padding:16px 18px">
          <div style="font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:16px;color:#F7F1E8">Vous voulez faire de la publicité ici ? Écrivez-nous</div>
          <span style="color:#F7F1E8;font-size:18px">→</span>
        </a>
      </div>

      <?php if ($featured->have_posts()): ?>
      <div style="padding:24px 0 0">
        <div style="font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:24px;letter-spacing:0.02em;color:#1D1D1B;border-top:1px solid #1D1D1B;padding-top:14px;margin-bottom:14px">En vedette</div>
        <?php while ($featured->have_posts()): $featured->the_post(); ?>
        <a href="<?php the_permalink(); ?>" style="display:block;text-decoration:none;margin-bottom:18px">
          <div style="aspect-ratio:3/2;overflow:hidden;background:#FBF7F0;margin-bottom:8px"><?php echo get_the_post_thumbnail(get_the_ID(), 'medium', ['style' => 'width:100%;height:100%;object-fit:cover']); ?></div>
          <div style="font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:15.5px;color:#1D1D1B;line-height:1.25"><?php the_title(); ?></div>
        </a>
        <?php endwhile; wp_reset_postdata(); ?>
      </div>
      <?php endif; ?>

      <div style="padding:24px 0 24px"></div>

    </div>
    <?php
    get_footer();
    exit;
});
