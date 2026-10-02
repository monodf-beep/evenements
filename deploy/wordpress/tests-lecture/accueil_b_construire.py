# Accueil de TEST B (02/10/2026) : la structure de guidatorino.com, nos contraintes.
#
# Demande de Franck, après le test A : « rester sur le modèle de Guidatorino, avec nos
# contraintes » — beaucoup d'informations sans submerger, et le côté « fait par des
# passionnés ». Mesures du 02/10 qui ont orienté la construction (docs/ACCUEIL_MODELE_GUIDATORINO.md) :
#   - même volume de texte que nous (≈ 1 000 mots), DEUX FOIS MOINS d'articles distincts
#     que le test A (24 contre 44) : l'impression de richesse ne vient pas de la quantité ;
#   - elle vient de la VARIÉTÉ des blocs (une quinzaine de types) et des images ou dessins
#     (≈ 48 contre 22, dont 8 dans le premier écran contre 4) ;
#   - le « fait main » est un système : logo croqué, pavés dont l'icône déborde, encadrés
#     au trait décalé, trois colonnes de blog, extraits avec mots en gras.
# Contraintes gardées : charte § 6 (pas de superlatifs, pas de « à ne pas manquer », pas
# de titres en capitales), règle 5 (rien de passé), aucune fausse présence humaine (pas de
# « coups de cœur » : la sélection est calculée), seuls des signaux vrais (heure du dernier
# ajout, date de vérification de chaque fiche).
#
# Entrées (dossier courant) : home-donnees.json et home-b-donnees.json (extraits du
# serveur), home.html (accueil en ligne : icônes et liens), skyline.svg n'est pas lu (la
# frise est appelée par son adresse). Sortie : home_b.html (bloc wp:html).
import json, re, html
from datetime import datetime, timedelta

A0 = json.load(open('home-donnees.json'))
B0 = json.load(open('home-b-donnees.json'))
NOW = datetime.strptime(A0['now'], '%Y-%m-%d %H:%M:%S')
TERS = {'Savoie': 'savoie', 'Piémont': 'piemonte', "Vallée d'Aoste": 'vallee-aoste', 'Comté de Nice': 'nice'}
MOIS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.']
MOIS_L = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
JOURS = ['Lun.', 'Mar.', 'Mer.', 'Jeu.', 'Ven.', 'Sam.', 'Dim.']
JOURS_L = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']


def prep(e):
    ter = [t for t in e['ter'].split(',') if t in TERS]
    if not ter or not e.get('s'):
        return None
    e['T'] = ter[0]
    e['S'] = datetime.strptime(e['s'], '%Y-%m-%d %H:%M:%S')
    e['E'] = datetime.strptime(e['e'], '%Y-%m-%d %H:%M:%S')
    return e if e['E'] >= NOW else None  # règle 5 : rien de terminé


E = {}
for e in A0['ev'] + B0['nouveautes']:
    x = prep(dict(e))
    if x:
        E.setdefault(x['id'], {}).update(x)
vus = set()
esc = lambda s: html.escape(s or '', quote=True)


def jm(x):
    return f'{x.day} {MOIS[x.month - 1]}'


def quand(e):
    s, f = e['S'], e['E']
    if s.date() == f.date():
        return f'{JOURS[s.weekday()]} {jm(s)}'
    if s <= NOW:
        return f'Jusqu’au {jm(f)}'
    if (s.month, s.year) == (f.month, f.year):
        return f'{s.day} – {jm(f)}'
    return f'{jm(s)} – {jm(f)}'


def ville(e):
    return esc((e.get('vl') or e.get('v') or '').split(' · ')[-1])


def pill(e):
    return f'<span class="gb-ter gb-{TERS[e["T"]]}">{esc(e["T"])}</span>'


def image(e, cls='gb-img', tot=False):
    # tot=True : image du premier écran, chargée tout de suite (un chargement différé
    # retarde le LCP : https://web.dev/articles/lcp-lazy-loading)
    if not e.get('img'):
        return f'<span class="{cls} gb-vide"></span>'
    r = (e['iw'] / e['ih']) if e.get('ih') else 1.4
    mode = 'couvre' if 1.2 < r < 1.9 else 'affiche'  # une affiche reste entière, sur un fond flouté d'elle-même
    charge = 'fetchpriority="high"' if tot == 'premier' else ('' if tot else 'loading="lazy" decoding="async"')
    return f'<span class="{cls} {mode}" style="--bg:url(\'{esc(e["img"])}\')"><img src="{esc(e["img"])}" alt="" {charge}></span>'


def onglet(titre, lien=None):
    t = f'<a href="{lien}">{titre} <span aria-hidden="true">›</span></a>' if lien else titre
    return f'<h2 class="gb-onglet">{t}</h2>'


def carte(e, tot=False):
    vus.add(e['id'])
    return (f'<article class="gb-carte"><a href="{esc(e["u"])}">{image(e, tot=tot)}'
            f'<span class="gb-meta">{pill(e)} <span class="gb-date">{quand(e)}</span></span>'
            f'<span class="gb-ct">{esc(e["t"])}</span></a></article>')


# Mots en gras dans les extraits, comme chez Guidatorino : mais seulement des FAITS
# (dates, lieu, ville, gratuité), repérés dans le texte, trois au plus. Aucun mot ajouté.
RE_DATE = re.compile(r'\b(?:(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\s+)?(?:du\s+)?\d{1,2}(?:er)?\s+(?:(?:au|et)\s+\d{1,2}\s+)?(?:' + '|'.join(MOIS_L) + r')(?:\s+20\d\d)?(?:\s+à\s+\d{1,2}\s?h(?:\s?\d\d)?)?', re.I)
RE_GRAT = re.compile(r'\b(?:gratuite?s?|entrée libre|accès libre)\b', re.I)


def gras(e, texte):
    t = esc(texte)
    spans = []
    for rx in (RE_DATE, RE_GRAT):
        for m in rx.finditer(t):
            spans.append((m.start(), m.end()))
    lieu = (e.get('vl') or '').split(' · ')[0]
    for mot in (lieu, ville(e)):
        mot = esc(mot)
        if len(mot) >= 4:
            i = t.find(mot)
            if i >= 0:
                spans.append((i, i + len(mot)))
    spans.sort()
    pris, fin = [], -1
    for a, b in spans:
        if a >= fin and len(pris) < 3:
            pris.append((a, b)); fin = b
    for a, b in reversed(pris):
        t = t[:a] + '<b>' + t[a:b] + '</b>' + t[b:]
    return t


def court(s, n=40):
    m = s.split()
    return ' '.join(m[:n]) + ('…' if len(m) > n else '')


# ---------- données des blocs ----------
alloc = {k: [i for i in v if i in E] for k, v in A0['alloc'].items()}
une = []
for i in alloc['ala-une'] + alloc['evidence'] + alloc['evidence-bottom'] + alloc['deplacement']:
    if i not in une:
        une.append(i)
une = [E[i] for i in une[:4]]
for e in une:
    vus.add(e['id'])

auj0 = NOW.replace(hour=0, minute=0, second=0)
fin_auj = auj0 + timedelta(hours=23, minutes=59)
aujourdhui = [e for e in E.values() if e['id'] not in vus and e['S'] <= fin_auj and (e['E'] - e['S']).days <= 10]
aujourdhui.sort(key=lambda e: (e['S'].date() != auj0.date(), -e.get('hs', 0)))  # ce qui COMMENCE aujourd'hui d'abord
aujourdhui = aujourdhui[:4]
for e in aujourdhui:
    vus.add(e['id'])

nouv = [E[n['id']] for n in B0['nouveautes'] if n['id'] in E and n['id'] not in vus][:8]
for e in nouv:
    vus.add(e['id'])
dernier = datetime.strptime(B0['nouveautes'][0]['pd'], '%Y-%m-%d %H:%M:%S')
nb_nouv = len([n for n in B0['nouveautes'] if n['id'] in E])

fin_we = auj0 + timedelta(days=(6 - auj0.weekday()), hours=23, minutes=59)
we_tous = [e for e in E.values() if e['S'] <= fin_we and (e['E'] - e['S']).days <= 10]
we = sorted([e for e in we_tous if e['id'] not in vus], key=lambda e: (e['S'], -e.get('hs', 0)))[:7]

# Guides et curiosités : SEULEMENT ce qui ne parle pas d'un événement passé (règle 5).
# Exclus le 02/10 : Plaisirs de Culture (19-27 sept.), Journées du patrimoine (26-27 sept.),
# Festivals de l'été en Savoie. Le test A mettait le premier en vedette : c'était une faute.
GARDER = [8249, 3648, 2424, 2420, 8227, 8233, 8235]
P = {p['id']: p for p in A0['posts']}
coude = [P[i] for i in GARDER if i in P][:6]

# ---------- icônes et liens de l'accueil en ligne ----------
h0 = open('home.html', encoding='utf-8').read()
icones = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>\s*(<svg width="34".*?</svg>)\s*(?:<[^>]+>\s*)*([^<]+)<', h0, re.S)[:6]

ENVELOPPE = ('<svg class="gb-env" viewBox="0 0 24 24" aria-hidden="true"><g fill="none" stroke="#1D1D1B" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">'
             '<rect x="2.5" y="6" width="19" height="13" rx="1.5" fill="#fff"/><path d="M3.2 7.2l8.8 6.6 8.8-6.6"/></g>'
             '<path d="M12 18.6c-1.4-.9-2.9-2-2.9-3.5 0-.9.6-1.5 1.4-1.5.6 0 1.1.4 1.5.9.4-.5.9-.9 1.5-.9.8 0 1.4.6 1.4 1.5 0 1.5-1.5 2.6-2.9 3.5z" fill="#DC5D45"/></svg>')
CAL_PLUS = ('<svg class="gb-ico-enc" viewBox="0 0 24 24" aria-hidden="true"><g fill="none" stroke="#1D1D1B" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">'
            '<rect x="3.5" y="5" width="17" height="15.5" rx="1" fill="#fff"/><path d="M3.8 9.8c4.4-.2 9-.1 16.5 0M8 3v3.6M16 3v3.6"/></g>'
            '<path d="M12 12.2v6M9 15.2h6" fill="none" stroke="#DC5D45" stroke-width="2.3" stroke-linecap="round"/></svg>')
ECRAN = ('<svg class="gb-ico-enc" viewBox="0 0 24 24" aria-hidden="true"><g fill="none" stroke="#1D1D1B" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">'
         '<rect x="3" y="4" width="18" height="12.5" rx="1" fill="#fff"/><path d="M9 20.5h6M12 16.5v4"/></g>'
         '<path d="M8 10.3h8M8 7.6h5" fill="none" stroke="#DC5D45" stroke-width="2.3" stroke-linecap="round"/></svg>')

# Monuments de la frise de l'en-tête (agenda-skyline-full.svg, 784 x 236), recadrés par masque :
# (x, y, largeur, hauteur) dans la frise, et l'échelle d'affichage.
MONU = {'Piémont': (40, 6, 100, 216, .36, 'https://agendasabauda.eu/territoire/piemont/', 'Turin, la Mole'),
        'Comté de Nice': (214, 60, 88, 170, .45, 'https://agendasabauda.eu/territoire/comte-de-nice/', 'Nice'),
        "Vallée d'Aoste": (402, 118, 116, 110, .58, 'https://agendasabauda.eu/territoire/vallee-d-aoste/', 'Aoste, l’arc d’Auguste'),
        'Savoie': (586, 12, 154, 218, .36, 'https://agendasabauda.eu/territoire/savoie/', 'Chambéry, les Éléphants')}
SKY = 'https://agendasabauda.eu/wp-content/uploads/2026/07/agenda-skyline-full.svg'
# Compteur avec son périmètre écrit à côté (CLAUDE.md, règle 6) : fiches françaises à venir
# ou en cours, qui commencent au plus tard dans 75 jours (la fenêtre de l'extraction).
HORIZON = NOW + timedelta(days=75)
nb_ter = {t: len([e for e in E.values() if e['T'] == t and e['S'] <= HORIZON]) for t in TERS}

# ---------- assemblage ----------
s = []
s.append('<p class="gb-test">Page de test B de l’accueil (noindex), sur le modèle de Guidatorino. Instantané de la base du '
         f'{NOW.day} {MOIS[NOW.month-1]} à {NOW.hour} h {NOW.minute:02d}. La vraie page d’accueil n’est pas modifiée. '
         '<span class="gb-choix">Texte : <a href="#" data-gbt="sans">sans empattement (actuel)</a> <a href="#" data-gbt="serif">Georgia, comme Guidatorino</a></span> '
         '<span class="gb-choix">Encadrés : <a href="#" data-gbc="croque">au trait décalé</a> <a href="#" data-gbc="sobre">sobres</a></span> '
         '<span class="gb-choix">Haut de page : <a href="#" data-gbh="tous">les 4 empilées</a> <a href="#" data-gbh="actuel">1. carrousel actuel</a> <a href="#" data-gbh="carnet">2. carnet</a> '
         '<a href="#" data-gbh="frise">3. frise</a> <a href="#" data-gbh="une">4. une fixe, sans carrousel</a></span></p>')

# 0. En-tête de l'accueil (la vraie home l'affiche AU-DESSUS du menu ; une page de test
#    hérite de l'en-tête réduit des pages intérieures, d'où son absence signalée par Franck).
s.append('<div class="gh-mast"><p class="gh-mot"><b>Agenda</b> <span>Sabauda</span></p>'
         f'<div class="gh-frise" role="img" aria-label="Frise des 4 territoires : Turin, Nice, Aoste, Chambéry" style="-webkit-mask-image:url({SKY});mask-image:url({SKY})"></div>'
         '<p class="gh-devise">Quoi faire, où manger · 4 territoires</p></div>')

# 0 bis. Haut de page : quatre options à comparer.
ICO = {html.unescape(l.strip()): sv for u, sv, l in icones}


def ico(nom):
    sv = ICO.get(nom, '')
    return re.sub(r'<svg width="34" height="34"', '<svg class="gh-ico" aria-hidden="true"', sv.replace(chr(10), ' '))


def photo(evs):
    """La meilleure PHOTO (pas une affiche) d'une liste : un fond de carrousel doit être un paysage."""
    for e in sorted(evs, key=lambda e: -e.get('hs', 0)):
        if e.get('img') and e.get('ih') and 1.3 < e['iw'] / e['ih'] < 2.2:
            return e['img']
    return ''


def dans(mot):
    return [e for e in E.values() if mot in e.get('cat', '') and e['S'] <= HORIZON]


ven = auj0
dim = fin_we
expos = [e for e in dans('Expositions') if e['S'] <= NOW]
gastro = [e for e in dans('Gastronomie') if e['S'].month == NOW.month or e['S'] <= NOW]
famille = dans('famille') + dans('Famille')
# Photos des couvertures : CHOISIES, pas tirées des fiches. Le 02/10, le choix automatique
# a pris une affiche portant « Samedi 19 sept. » (date passée) pour illustrer « Ce week-end ».
# Une couverture de rubrique se choisit une fois, comme les couvertures actuelles.
def ph_post(i):
    return P[i]['img'] if i in P else ''


def ph_ev(i):
    return E[i]['img'] if i in E else ''


# Photos choisies le 02/10 parmi les 327 grandes photos en paysage de la médiathèque, en les
# REGARDANT (planche contact) : haute définition, pas de visage au premier plan, un territoire chacune.
CREDITS = {'https://agendasabauda.eu/wp-content/uploads/2026/07/promenade-des-anglais-nice-alexander-migl-cc-by-sa-scaled.jpg': 'Photo : Alexander Migl, CC BY-SA'}
SLIDES = [  # (surtitre, titre, ligne chiffrée — périmètre écrit, lien, icône, photo)
    (f'{JOURS_L[ven.weekday()].capitalize()} {ven.day} – {JOURS_L[dim.weekday()]} {dim.day} {MOIS_L[dim.month-1]}', 'Ce week-end',
     f'<b>{len(we_tous)} rendez-vous</b> dans les quatre territoires', 'https://agendasabauda.eu/ce-week-end/', ico('Ce week-end'), 'https://agendasabauda.eu/wp-content/uploads/2026/07/chamonix-vallee-mont-blanc-scaled.jpg'),
    ('Fraîchement ajoutées', 'Les nouveautés', f'<b>{nb_nouv} fiches</b> ajoutées depuis le {jm(datetime.strptime(B0["nouveautes"][-1]["pd"], "%Y-%m-%d %H:%M:%S"))}',
     'https://agendasabauda.eu/selections/les-nouveautes/', CAL_PLUS.replace('gb-ico-enc', 'gh-ico'), 'https://agendasabauda.eu/wp-content/uploads/2026/07/promenade-des-anglais-nice-alexander-migl-cc-by-sa-scaled.jpg'),
    (f'En {MOIS_L[NOW.month-1]}', 'Fêtes, foires et sagre', f'<b>{len(gastro)} rendez-vous</b> de gastronomie ce mois-ci',
     'https://agendasabauda.eu/selections/quelle-sagre-ce-mois/', ico('Saveurs & gastronomie'), 'https://agendasabauda.eu/wp-content/uploads/2026/10/fiera-nazionale-del-marrone-27a-edizione-original-c33256943c.webp'),
    ('En ce moment', 'Les expositions', f'<b>{len(expos)} expositions</b> ouvertes aujourd’hui', 'https://agendasabauda.eu/evenements/categorie/expositions-patrimoine/',
     ico('Expositions'), 'https://agendasabauda.eu/wp-content/uploads/2026/09/apertura-serale-di-villa-della-regina-a-torino-original-115db17e5e.webp'),
    ('Avec les enfants', 'En famille', f'<b>{len(famille)} sorties</b> d’ici le {jm(HORIZON)}', 'https://agendasabauda.eu/evenements/categorie/jeune-public-famille/',
     ico('En famille'), 'https://agendasabauda.eu/wp-content/uploads/2026/09/le-mele-di-orasso-dalla-bellezza-del-paesaggio-al-piacere-de-c3694bd63f-scaled.webp'),
]
VAGUE = '<svg class="gh-vague" viewBox="0 0 120 8" aria-hidden="true"><path d="M2 5c10-4 18 3 29 0s19-4 29-1 19 4 29 0 19-3 29 0" fill="none" stroke="#DC5D45" stroke-width="2.6" stroke-linecap="round"/></svg>'


COUR, PRIO, LAZY = ' aria-current="true"', 'fetchpriority="high"', 'loading="lazy"'


def carrousel(cls, slides):
    piste = ''.join(f'<li class="gh-slide">{x}</li>' for x in slides)
    points = ''.join(f'<button type="button" data-i="{i}" aria-label="Diapositive {i+1}"{COUR if i == 0 else ""}></button>' for i in range(len(slides)))
    return (f'<div class="gh-car {cls}"><ul class="gh-piste">{piste}</ul>'
            '<button type="button" class="gh-nav gh-prec" data-dir="-1" aria-label="Précédent">‹</button>'
            '<button type="button" class="gh-nav gh-suiv" data-dir="1" aria-label="Suivant">›</button>'
            f'<div class="gh-points">{points}</div></div>')


# 1. le carrousel d'aujourd'hui, tel quel (cinq couvertures, texte incrusté dans l'image)
COUV = re.findall(r'<li class="as-cs__slide"[^>]*>\s*<a href="([^"]+)">\s*<img[^>]*src="([^"]+)"[^>]*alt="([^"]*)"', h0)
COUV = list(dict.fromkeys(COUV))  # l'accueil contient le carrousel deux fois (ordinateur et téléphone)
actuel = carrousel('gh-actuel', [f'<a href="{u}"><img src="{im}" alt="{esc(html.unescape(al))}" loading="lazy"></a>' for u, im, al in COUV])
# 2. « carnet » : nos photos, notre cartouche au trait décalé, nos icônes, des chiffres VRAIS en texte
carnet = carrousel('gh-carnet', [
    (f'<a href="{u}"><img src="{esc(ph)}" alt="" {PRIO if i == 0 else LAZY}>'
     f'<span class="gh-cart">{ic}<span class="gh-sur">{sur}</span><span class="gh-t">{t}</span>{VAGUE}<span class="gh-l">{ligne}</span>'
     '<span class="gh-voir">Voir la sélection ›</span></span>' + (f'<span class="gh-credit">{CREDITS[ph]}</span>' if ph in CREDITS else '') + '</a>')
    for i, (sur, t, ligne, u, ic, ph) in enumerate(SLIDES)])
# 3. « frise » : pas de photo, les quatre monuments cliquables
ZONES = {'Piémont': (40, 100), 'Comté de Nice': (214, 88), "Vallée d'Aoste": (402, 116), 'Savoie': (586, 154)}
frise = ('<div class="gh-frise-g"><p class="gh-frise-t">Choisissez votre côté des Alpes</p><div class="gh-frise-b">'
         f'<div class="gh-frise-d" style="-webkit-mask-image:url({SKY});mask-image:url({SKY})"></div>'
         + ''.join(f'<a class="gh-zone gh-z-{TERS[t]}" href="{MONU[t][5]}" style="left:{x/784*100:.2f}%;width:{w/784*100:.2f}%">'
                   f'<span class="gh-zn">{esc(t)}</span><span class="gh-zc">{nb_ter[t]} rendez-vous</span></a>' for t, (x, w) in ZONES.items())
         + f'</div><p class="gh-frise-p">Rendez-vous comptés d’ici le {jm(HORIZON)}.</p></div>')
# 4. « une fixe » : la recommandation des études (pas de carrousel) — une grande, trois à côté
g0 = une[0]
unefixe = (f'<div class="gh-une"><a class="gh-une-g" href="{esc(g0["u"])}"><img src="{esc(g0["img"])}" alt="" fetchpriority="high">'
           f'<span class="gh-cart"><span class="gh-sur">À la une · {esc(g0["T"])}</span><span class="gh-t gh-t-s">{esc(g0["t"])}</span>{VAGUE}'
           f'<span class="gh-l"><b>{quand(g0)}</b> · {ville(g0)}</span></span></a><div class="gh-une-l">'
           + ''.join(f'<a href="{esc(e["u"])}">{image(e, "gb-img")}<span><span class="gb-meta">{pill(e)} <span class="gb-date">{quand(e)}</span></span>'
                     f'<span class="gb-ct">{esc(e["t"])}</span></span></a>' for e in une[1:4]) + '</div></div>')
s.append('<div class="gh">' + ''.join(f'<div class="gh-opt" data-lbl="{l}">{x}</div>' for l, x in (("Option 1 · carrousel actuel", actuel), ("Option 2 · carnet", carnet), ("Option 3 · frise", frise), ("Option 4 · une fixe, sans carrousel", unefixe))) + '</div>')

# 1. Accroche + recherche
s.append('<div class="gb-accroche"><div><p class="gb-h1">Que faire en Savoie, en Piémont, en Vallée d’Aoste et dans le Comté de Nice</p>'
         f'<p class="gb-sous">Les sorties culturelles des deux côtés des Alpes. Dernier ajout : ce matin à {dernier.hour} h {dernier.minute:02d}.</p></div>'
         '<form class="gb-cherche" role="search" action="https://agendasabauda.eu/"><input type="search" name="s" aria-label="Rechercher" placeholder="Un événement, une ville…"><button type="submit">Chercher</button></form></div>')

# 2. Pavés dessinés + lettre d'information
paves = ''.join(f'<a class="gb-pave" href="{u}">{re.sub(chr(10), " ", sv)}<span>{html.escape(html.unescape(l.strip()))}</span></a>' for u, sv, l in icones)
s.append('<div class="gb-portes"><nav class="gb-paves" aria-label="Accès rapides">' + paves + '</nav>'
         '<a class="gb-enc gb-nl" href="https://agendasabauda.eu/newsletter/">' + ENVELOPPE +
         '<span class="gb-nl-t">Recevez l’essentiel des quatre territoires</span><span class="gb-nl-s">Chaque vendredi matin, dans votre boîte.</span>'
         '<span class="gb-nl-b">S’inscrire à la lettre</span></a></div>')

# 3. À la une, 4. Aujourd'hui
s.append('<div class="gb-une-r">' + onglet('À la une') + '<div class="gb-rang">' + ''.join(carte(e, True) for e in une) + '</div></div>')
s.append(onglet(f'Aujourd’hui, {JOURS_L[NOW.weekday()]} {NOW.day} {MOIS_L[NOW.month-1]}', 'https://agendasabauda.eu/aujourdhui/')
         + '<div class="gb-rang">' + ''.join(carte(e) for e in aujourdhui) + '</div>')

# 5. Trois colonnes
col1 = onglet('Nouveautés de l’agenda')
for e in nouv:
    ex = court(e.get('ex') or '', 40)
    verif = e.get('verif') or ''
    v = ''
    if verif:
        dv = datetime.strptime(verif[:10], '%Y-%m-%d')
        v = f'<span class="gb-verif">{pill(e)} · {quand(e)} · vérifié auprès de la source le {jm(dv)}</span>'
    col1 += (f'<article class="gb-nouv"><h3><a href="{esc(e["u"])}">{esc(e["t"])}</a></h3><div class="gb-nouv-c">'
             f'<a href="{esc(e["u"])}" tabindex="-1" aria-hidden="true">{image(e, "gb-img gb-img-n")}</a>'
             f'<p>{gras(e, ex)} <a class="gb-suite" href="{esc(e["u"])}" aria-label="Lire : {esc(e["t"])}">»</a></p></div>{v}</article>')
col1 += f'<p class="gb-plus"><a href="https://agendasabauda.eu/tout-l-agenda/">{nb_nouv} fiches ajoutées depuis le {jm(datetime.strptime(B0["nouveautes"][-1]["pd"], "%Y-%m-%d %H:%M:%S"))} : tout l’agenda ›</a></p>'

col2 = '<div class="gb-terrs">'
for t, (x, y, w, hh, k, u, lab) in MONU.items():
    st = (f'width:{w*k:.0f}px;height:{hh*k:.0f}px;-webkit-mask-image:url({SKY});mask-image:url({SKY});'
          f'-webkit-mask-size:{784*k:.1f}px {236*k:.1f}px;mask-size:{784*k:.1f}px {236*k:.1f}px;'
          f'-webkit-mask-position:-{x*k:.1f}px -{y*k:.1f}px;mask-position:-{x*k:.1f}px -{y*k:.1f}px')
    col2 += (f'<a class="gb-terr gb-terr-{TERS[t]}" href="{u}"><span class="gb-monu" role="img" aria-label="{esc(lab)}" style="{st}"></span>'
             f'<span class="gb-terr-n">{esc(t)}</span><span class="gb-terr-c">{nb_ter[t]} rendez-vous d’ici le {jm(HORIZON)}</span></a>')
col2 += '</div><div class="gb-boite"><h2 class="gb-boite-t">À garder sous le coude</h2>'
for p in coude:
    col2 += (f'<a class="gb-coude" href="{esc(p["u"])}"><span class="gb-img couvre" style="--bg:url(\'{esc(p["img"])}\')"><img src="{esc(p["img"])}" alt="" loading="lazy"></span>'
             f'<span>{esc(p["t"])}</span></a>')
col2 += '</div>'

col3 = ('<div class="gb-pub"><span>Publicité</span><div>Exemple d’emplacement<br>300 × 250</div></div>'
        '<a class="gb-enc gb-enc-c" href="https://agendasabauda.eu/proposer-un-evenement/">' + CAL_PLUS +
        '<span class="gb-enc-t">Vous organisez un événement ?</span><span class="gb-enc-s">Proposez-le à l’agenda.</span></a>'
        '<a class="gb-enc gb-enc-c" href="https://agendasabauda.eu/annoncer/">' + ECRAN +
        '<span class="gb-enc-t">Faire connaître votre lieu</span><span class="gb-enc-s">Publicité sur Agenda Sabauda : écrivez-nous.</span></a>'
        f'<div class="gb-boite"><h2 class="gb-boite-t"><a href="https://agendasabauda.eu/ce-week-end/">Ce week-end ›</a></h2>')
for e in we:
    vus.add(e['id'])
    col3 += (f'<a class="gb-we" href="{esc(e["u"])}">{image(e, "gb-img gb-img-w")}<span><span class="gb-we-t">{esc(e["t"])}</span>'
             f'<span class="gb-date">{quand(e)} · {ville(e)}</span></span></a>')
col3 += f'<p class="gb-plus"><a href="https://agendasabauda.eu/ce-week-end/">Les {len(we_tous)} rendez-vous du week-end ›</a></p></div>'
col3 += '<p class="gb-contact">Écrire à l’agenda : <a href="mailto:contact@culturasabauda.eu">contact@culturasabauda.eu</a></p>'

s.append(f'<div class="gb-cols"><div class="gb-c1">{col1}</div><div class="gb-c2">{col2}</div><aside class="gb-c3" aria-label="À côté">{col3}</aside></div>')

JS = ('<script>(function(){var g=document.querySelector(".gb");if(!g){return}'
      'document.addEventListener("click",function(e){if(!e.target.closest){return}var a=e.target.closest("a[data-gbt],a[data-gbc]");if(!a){return}e.preventDefault();'
      'if(a.dataset.gbt){g.dataset.texte=a.dataset.gbt}else{g.dataset.cadre=a.dataset.gbc}});'
      # sélecteur du haut de page
      'document.addEventListener("click",function(e){if(!e.target.closest){return}var a=e.target.closest("a[data-gbh]");if(!a){return}e.preventDefault();g.dataset.hero=a.dataset.gbh;'
      'try{localStorage.setItem("gb-hero-v2",a.dataset.gbh)}catch(x){}});'
      'try{var h=localStorage.getItem("gb-hero-v2");if(h){g.dataset.hero=h}}catch(x){}'
      # carrousels : défilement au doigt (scroll-snap), flèches et points ; AUCUN défilement automatique
      'document.querySelectorAll(".gh-car").forEach(function(c){var p=c.querySelector(".gh-piste");var pts=c.querySelectorAll(".gh-points button");'
      'function va(i){p.scrollTo({left:i*p.clientWidth,behavior:"smooth"})}'
      'c.querySelectorAll(".gh-nav").forEach(function(b){b.addEventListener("click",function(){var i=Math.round(p.scrollLeft/p.clientWidth)+Number(b.dataset.dir);'
      'if(i==-1){i=pts.length-1}if(i==pts.length){i=0}va(i)})});'
      'pts.forEach(function(b){b.addEventListener("click",function(){va(Number(b.dataset.i))})});'
      'p.addEventListener("scroll",function(){var i=Math.round(p.scrollLeft/p.clientWidth);pts.forEach(function(b,k){if(k==i){b.setAttribute("aria-current","true")}else{b.removeAttribute("aria-current")}})},{passive:true})})'
      '})();</script>')
CSS = open('accueil_b.css', encoding='utf-8').read()
page = '<!-- wp:html -->\n<style>' + CSS + '</style><div class="gb" data-texte="sans" data-cadre="croque" data-hero="tous">' + ''.join(s) + '</div>' + JS + '\n<!-- /wp:html -->'
assert '\n\n' not in page and '&&' not in JS and '<' not in JS.replace('<script>', '').replace('</script>', '')
print('carnet', [(sl[1], bool(sl[5])) for sl in SLIDES], '| couvertures', len(COUV))
open('home_b.html', 'w', encoding='utf-8').write(page)
print('une', [e['id'] for e in une], '| auj', [e['id'] for e in aujourdhui], '| nouv', [e['id'] for e in nouv], '| we', len(we), '/', len(we_tous),
      '| coude', [p['id'] for p in coude], '| paves', len(icones), '| ter', nb_ter, '| octets', len(page.encode()))
