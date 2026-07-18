<?php
/**
 * "À propos" (page 933) — rendu complet en PHP (template_redirect), gabarit
 * simple : H1 + paragraphes, largeur max 700px comme les autres pages
 * (Ce week-end / Tout l'agenda / Proposer un événement...).
 *
 * Texte FR prêt à coller, tel que rédigé dans
 * docs/PLAN_DU_SITE_AGENDA_SABAUDO.md §4 "Texte « À propos »" — copié tel
 * quel, non réécrit. Version IT ignorée pour l'instant (pas de page /it/).
 *
 * Header/footer de marque déjà injectés site-wide par le snippet #19
 * (site-header-footer.php) — pas recréés ici.
 */
add_action('template_redirect', function () {
    if (is_admin() || !is_page(933)) {
        return;
    }

    get_header();
    ?>
    <div style="max-width:700px;margin:0 auto;padding:0 20px">

      <div style="padding:32px 0 8px">
        <h1 style="margin:0 0 20px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:32px;line-height:1.05;color:#1D1D1B;letter-spacing:0.02em">À propos</h1>
      </div>

      <div style="padding-bottom:40px;font-family:'Nunito Sans',sans-serif;font-size:15px;line-height:1.65;color:#1D1D1B">

        <p style="margin:0 0 18px">Agenda Sabauda est l'agenda culturel de l'espace alpin occidental — un territoire sans frontière qui relie la Savoie et la Haute-Savoie, le Piémont, la Vallée d'Aoste et Nice. Notre objectif : rassembler en un seul endroit tout ce qu'il y a à faire, à voir et à vivre sur ces quatre territoires que l'histoire, la langue et la montagne ont toujours reliés.</p>

        <p style="margin:0 0 18px">Né de la conviction que la culture ne s'arrête pas aux frontières administratives, Agenda Sabaudo recense chaque semaine les expositions, concerts, spectacles, festivals, sagre, marchés, fêtes traditionnelles, rendez-vous en famille et grands moments sportifs — des institutions les plus prestigieuses aux plus petites communes de village.</p>

        <p style="margin:0 0 18px">Agenda Sabauda s'adresse à tous : au voyageur de passage pour un week-end comme à l'habitant qui veut découvrir, ou redécouvrir, ce qui se passe près de chez lui — d'un versant à l'autre des Alpes. Vous y trouverez, semaine après semaine, une sélection vivante et l'agenda complet de la période : ce qui commence, ce qui se termine, et ce qu'il ne faut pas manquer ce week-end.</p>

        <p style="margin:0 0 18px">Nous nous engageons à vérifier nos informations à la source officielle — le lieu, l'organisateur —, à créditer chaque photographie et à ne jamais publier autre chose que des événements réels, à venir. Agenda Sabauda est édité par <strong>Cultura Sabauda</strong>, média culturel bilingue de l'espace alpin occidental.</p>

        <p style="margin:24px 0 0;font-style:italic;color:#6F6B62;font-size:14px;border-top:1px solid #E3DCCE;padding-top:20px">Retrouvez sur Agenda Sabauda tout ce qu'il ne faut pas manquer : que faire ce week-end · les 4 territoires · expositions &amp; patrimoine · concerts, spectacles &amp; festivals · gastronomie, sagre &amp; marchés · en famille.</p>

      </div>

    </div>
    <?php
    get_footer();
    exit;
});
