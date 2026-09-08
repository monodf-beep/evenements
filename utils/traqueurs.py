#!/usr/bin/env python3
"""Reconnaître un LIEN DE TRAÇAGE de newsletter — un seul détecteur pour tout le dépôt.

POURQUOI UN MODULE À PART (2026-09-08)
Deux listes décrivaient la même chose et divergeaient : `scripts/publisher_as._TRACKING_HOSTS`
(+ `_TRACKING_PATH`, qui connaît le motif MailUp `/e/tr`) et
`scripts/moisson_officielle._TRAQUEURS` (qui connaît sendibm1, emailsp, awstrack… que l'autre
ignore). C'est la racine du journal du jour, `docs/ERREURS_2026-09-08.md` : « deux détecteurs
pour la même chose, un seul juste ». Mesuré le soir même sur les 108 fiches approuvées, à
venir et incomplètes : une vingtaine n'avaient pour seule adresse qu'un lien de traçage, et
la moisson ne reconnaissait pas la moitié des routeurs rencontrés —

  • Brevo en marque blanche : `lql1t.r.sp1-brevo.net`, `r.routage2.arenametrix.fr`
    (même chemin `/mk/cl/f/sh/…` que sendibm1.com, même page « Brevo | Page not found ») ;
  • MailUp sur le DOMAINE DU CLIENT : `tr.comune.torino.it/e/tr?q=…`,
    `go.fondazionetorinomusei.it/e/tr?q=…` — l'hôte est officiel, seul le chemin trahit le
    routeur. Une liste d'hôtes ne peut pas les voir ; `bct.comune.torino.it` (une vraie
    source, décision de Franck) doit rester acceptée, donc on ne bannit jamais le domaine ;
  • Postmark (`track.pstmrk.it/3s/…`), OpenEMM (`openemm.d40.it/r.html?uid=…`), Sequar
    (`enteturismolmr.sequar.com/r/6pf/m/651314`), le compteur de clics du département
    (`stats.departement06.fr/c6.php?ec=2&…&e=m`).

Deux familles de motifs, parce que les routeurs se cachent de deux façons : par leur
HÔTE (sendibm1.com, musvc3.net) ou par leur CHEMIN sur un hôte quelconque (/e/tr, /mk/cl/f/).
Un lien est un traqueur dès qu'il tombe dans l'une des deux.

CE QUE CE MODULE NE DÉCIDE PAS : ce qu'on fait du lien. La moisson le suit et juge la
destination ; le publieur refuse de l'afficher comme source ; le collecteur l'ignore.
Chacun garde sa politique, tous partagent la même définition.

Aucune dépendance hors bibliothèque standard : importable par n'importe quel audit.
"""
from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# ── 1. Par l'HÔTE ──────────────────────────────────────────────────────────────────
# Motif appliqué au seul nom d'hôte, ancré en fin : `(^|\.)` évite qu'un domaine légitime
# soit pris pour un routeur parce qu'il en CONTIENT le nom (musvc-editions.fr, disons).
HOTES = re.compile(
    r"(^|\.)("
    # Mailchimp
    r"list-manage\.com|mailchi\.mp|mcusercontent\.com"
    # MailUp : musvc1..9.net (plus le domaine de la marque)
    r"|musvc\d*\.net|mailup\.\w+|mailupnet\.it|emailsp\.com"
    # Brevo / Sendinblue, y compris les marques blanches (sp1-brevo.net, sendibm1..3.com,
    # arenametrix.fr — routeur Brevo revendu aux salles de spectacle, vu sur Malraux Chambéry)
    r"|sendinblue\.com|brevo\.com|sp\d*-brevo\.net|sendibm\d*\.com|sibautomation\.com"
    r"|mailin\.fr|arenametrix\.fr"
    # Autres routeurs d'emailing
    r"|mailerlite\.com|sendgrid\.net|sg-links\.\w+|hubspotlinks\.com|mailjet\.com"
    r"|acumbamail\.com|awstrack\.me|pstmrk\.it|sequar\.com|cmail\d*\.com"
    r"|exct\.net|mktdns\.com"
    # Salesforce Marketing Cloud : le domaine est celui du CLIENT, seul le sous-domaine
    # trahit le routeur (click.marketingcloud.turismotorino.org, WP#7113, 2026-08-05).
    r"|marketingcloud\.\w[\w.-]*"
    # Sous-domaine « click. » / « clicks. » d'un domaine quelconque.
    r"|\w*clicks?\w*\.\w[\w.-]*\.(?:org|com|it|fr|net|eu)"
    r")$", re.I)

# ── 2. Par le CHEMIN, sur n'importe quel hôte ──────────────────────────────────────
CHEMINS = re.compile(
    # MailUp : /e/tr?q=… (long) et /e/r?q=… (court), y compris sur le domaine du client
    r"/e/tr\b|/e/r(?=[/?]|$)"
    # Identifiant d'abonné ou de suivi en paramètre (e=, eid=, subscriber=, qs=) : c'est
    # NOTRE identifiant, jamais publiable (docs/CONFORMITE.md §5).
    r"|[?&](e|eid|subscriber|qs)="
    # Brevo et ses marques blanches : /mk/cl/f/sh/<jeton>/<clé>
    r"|/mk/cl/f/"
    # OpenEMM : /r.html?uid=…
    r"|/r\.html\?uid="
    # Sequar : https://<client>.sequar.com/r/<campagne>/m/<n>
    r"|^https?://[^/]+/r/[^/]+/m/\d+"
    # Compteur de clics maison (departement06) : /c6.php?ec=2&l=…&e=…
    r"|/c\d\.php\?ec=",
    re.I)

# Paramètres de suivi qu'une page officielle traîne après un rebond (comune.asti.it/…
# ?utm_source=Giugno+in+Langhe…, vu le 08/09). Retirés AVANT de mémoriser une adresse :
# sans ça la même page serait mémorisée sous autant de formes qu'il y a eu de campagnes.
# Seulement des noms SANS AMBIGUÏTÉ : « ref » ou « source » désignent parfois la page
# elle-même sur certains sites, on ne les touche pas.
_PARAMS_DE_SUIVI = re.compile(r"^(utm_\w+|mc_[ce]id|fbclid|gclid|dclid|msclkid|_hsenc|_hsmi"
                              r"|mkt_tok|igshid|yclid)$", re.I)


def hote(url: str) -> str:
    """Nom d'hôte en minuscules, sans port, '' si l'adresse n'en a pas."""
    try:
        return (urlsplit((url or "").strip()).hostname or "").lower()
    except ValueError:
        return ""


def est_traqueur(url: str) -> bool:
    """L'adresse est-elle un lien de traçage (par son hôte ou par son chemin) ?

    Ne dit rien de la destination : un traqueur peut mener à une page officielle, à de la
    presse, à un autre traqueur, ou nulle part (jeton périmé ou tronqué). C'est à
    l'appelant de télécharger et de juger l'arrivée — jamais l'adresse écrite.
    """
    u = (url or "").strip()
    if not u:
        return False
    h = hote(u)
    return bool((h and HOTES.search(h)) or CHEMINS.search(u))


def sans_parametres_de_suivi(url: str) -> str:
    """L'adresse débarrassée de ses paramètres de suivi (utm_*, fbclid…), fragment retiré.
    Les autres paramètres (id=, lang=…) sont conservés : ils peuvent désigner la page."""
    u = (url or "").strip()
    if not u:
        return ""
    try:
        p = urlsplit(u)
    except ValueError:
        return u
    garde = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if not _PARAMS_DE_SUIVI.match(k)]
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(garde, doseq=True), ""))
