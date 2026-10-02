# Construit la page d'accueil de TEST (02/10, page 13339, /test-accueil/) à partir d'un
# instantané de la base. Entrées, dans le dossier courant :
#   - home-donnees.json : extrait sur le serveur (execute-php) — événements à venir ou en
#     cours (SQL direct : The Events Calendar réécrit les WP_Query), allocation réelle de
#     la home (cs_home_build_allocation, snippet 44), ligne de lieu des cartes
#     (cs_event_venue_line, snippet 21 : Torino -> Turin), articles récents ;
#   - home.html : la page d'accueil en ligne (curl), d'où sont recopiées les six icônes ;
#   - accueil.css (à côté de ce script).
# Sortie : home_test.html, à poser tel quel dans post_content (bloc wp:html : wpautop ne
# passe pas, il cassait les SVG en ligne des pages précédentes).
# Plan validé par Franck : À la une, recherche + pavés, Ce week-end, 7 prochains jours,
# À lire (+ colonne), Par territoire, Par envie. Français seulement, aucun doublon entre
# sections, rien de passé (règle 5).
import json, re, html
from datetime import datetime, timedelta

d = json.load(open('home-donnees.json'))
NOW = datetime.strptime(d['now'], '%Y-%m-%d %H:%M:%S')
TERS = {'Savoie': ('savoie', 'https://agendasabauda.eu/territoire/savoie/'),
        'Piémont': ('piemonte', 'https://agendasabauda.eu/territoire/piemont/'),
        "Vallée d'Aoste": ('vallee-aoste', 'https://agendasabauda.eu/territoire/vallee-d-aoste/'),
        'Comté de Nice': ('nice', 'https://agendasabauda.eu/territoire/comte-de-nice/')}
E = {}
for e in d['ev']:
    ter = [t for t in e['ter'].split(',') if t in TERS]
    if not ter or not e.get('s'):
        continue  # italien ou sans territoire : hors de la page française
    e['T'] = ter[0]
    e['S'] = datetime.strptime(e['s'], '%Y-%m-%d %H:%M:%S')
    e['E'] = datetime.strptime(e['e'], '%Y-%m-%d %H:%M:%S')
    if e['E'] < NOW:
        continue
    E[e['id']] = e
A = {k: [i for i in v if i in E] for k, v in d['alloc'].items()}
vus = set()

MOIS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.']
JOURS = ['Lun.', 'Mar.', 'Mer.', 'Jeu.', 'Ven.', 'Sam.', 'Dim.']


def jm(x):
    return f'{x.day} {MOIS[x.month - 1]}'


def quand(e):
    s, f = e['S'], e['E']
    if s.date() == f.date():
        return f'{JOURS[s.weekday()]} {jm(s)}'
    if s <= NOW:
        return f'Jusqu’au {jm(f)}'
    if s.month == f.month and s.year == f.year:
        return f'{s.day} – {jm(f)}'
    return f'{jm(s)} – {jm(f)}'


def esc(x):
    return html.escape(x or '', quote=True)


def pill(e):
    c, _ = TERS[e['T']]
    return f'<span class="hp-ter as-pill--{c}">{esc(e["T"])}</span>'


def image(e, cls='hp-img'):
    if not e.get('img'):
        return f'<div class="{cls} hp-vide"></div>'
    r = (e['iw'] / e['ih']) if e.get('ih') else 1.33
    mode = 'couvre' if 1.15 < r < 1.6 else 'affiche'  # une affiche n'est pas recadrée
    return (f'<div class="{cls} {mode}" style="--bg:url(\'{esc(e["img"])}\')"><img src="{esc(e["img"])}" alt="" loading="lazy" decoding="async"></div>')


def lieu(e):
    # même ligne que les cartes du site (cs_event_venue_line, snippet 21 : Torino -> Turin)
    return esc(e.get('vl') or e.get('v') or '')


def ville(e):
    return esc((e.get('vl') or e.get('v') or '').split(' · ')[-1])


def carte(e, cls='hp-carte'):
    vus.add(e['id'])
    return (f'<article class="{cls}"><a href="{esc(e["u"])}">{image(e)}'
            f'<p class="hp-meta">{pill(e)}<span class="hp-date">{quand(e)}</span></p>'
            f'<h3 class="hp-t">{esc(e["t"])}</h3><p class="hp-lieu">{ville(e)}</p></a></article>')


def ligne(e, img=True):
    vus.add(e['id'])
    return (f'<li class="hp-ligne"><a href="{esc(e["u"])}">{image(e, "hp-vign") if img else ""}<span class="hp-ltxt">'
            f'<span class="hp-meta">{pill(e)}<span class="hp-date">{quand(e)}</span></span>'
            f'<span class="hp-lt">{esc(e["t"])}</span></span></a></li>')


def tete(titre, lien=None, label='Voir tout', id_=None):
    a = f'<a class="hp-voir" href="{lien}">{label} →</a>' if lien else ''
    return f'<div class="hp-h"{f" id={chr(34)}{id_}{chr(34)}" if id_ else ""}><h2>{titre}</h2>{a}</div>'


# 1. À la une : allocation 'ala-une', complétée par 'evidence' (comme la home actuelle)
une = []
for i in A['ala-une'] + A['evidence'] + A['evidence-bottom'] + A['deplacement']:
    if i not in une:
        une.append(i)
une = une[:4]
g = E[une[0]]
vus.add(g['id'])
s_une = (tete('À la une') + '<div class="hp-une">'
         f'<article class="hp-grande"><a href="{esc(g["u"])}">{image(g, "hp-img hp-img-g")}'
         f'<p class="hp-meta">{pill(g)}<span class="hp-date">{quand(g)}</span></p><h3 class="hp-tg">{esc(g["t"])}</h3>'
         f'<p class="hp-lieu">{lieu(g)}</p></a></article><ul class="hp-liste">'
         + ''.join(ligne(E[i]) for i in une[1:]) + '</ul></div>')

# 2. Ce week-end (ven. 2 – dim. 4) : allocation d'abord, puis le meilleur score
d0 = NOW.replace(hour=0, minute=0, second=0)
fin_we = d0 + timedelta(days=(6 - d0.weekday()), hours=23, minutes=59)
we_all = [e for e in E.values() if e['S'] <= fin_we and e['E'] >= NOW]
# une exposition de plusieurs mois n'est pas « ce week-end » : on la laisse aux autres sections
we_court = [e for e in we_all if (e['E'] - e['S']).days <= 10]
ordre = [E[i] for i in A['weekend'] + A['jour'] + A['venir'] + A['venir-bottom'] if i in E]
ordre += sorted(we_court, key=lambda e: -e.get('hs', 0))
we = []
for e in ordre:
    if e in we_court and e['id'] not in vus and e not in we:
        we.append(e)
we = we[:8]
s_we = (tete('Ce week-end', 'https://agendasabauda.eu/ce-week-end/') + '<div class="hp-grille">' + ''.join(carte(e) for e in we) + '</div>'
        f'<p class="hp-plus"><a class="hp-btn" href="https://agendasabauda.eu/ce-week-end/">Tout le week-end : {len(we_court)} rendez-vous</a></p>')

# 3. Les 7 prochains jours, façon agenda papier (lun. 5 → ven. 9)
jours = []
for k in range(1, 8):
    j = d0 + timedelta(days=k)
    if j <= fin_we:
        continue
    if len(jours) == 5:
        break
    du_jour = [e for e in E.values() if e['S'].date() == j.date() and e['id'] not in vus]
    du_jour.sort(key=lambda e: -e.get('hs', 0))
    jours.append((j, du_jour))
s_7 = tete('La semaine prochaine', 'https://agendasabauda.eu/tout-l-agenda/', 'Tout l’agenda') + '<div class="hp-agenda">'
for j, evs in jours:
    if not evs:
        continue
    s_7 += f'<div class="hp-jour"><p class="hp-jl"><b>{JOURS[j.weekday()]}</b> {j.day} {MOIS[j.month - 1]}</p><ul>'
    if not evs:
        s_7 += '<li class="hp-rien">Pas de rendez-vous ce jour-là pour l’instant.</li>'
    for e in evs[:3]:
        vus.add(e['id'])
        s_7 += f'<li><a href="{esc(e["u"])}">{esc(e["t"])}</a> <span class="hp-v">{pill(e)} {ville(e)}</span></li>'
    if len(evs) > 3:
        s_7 += f'<li class="hp-autres">+ {len(evs) - 3} autres ce jour-là</li>'
    s_7 += '</ul></div>'
s_7 += '</div>'

# 4. À lire + colonne
P = d['posts']
p0 = P[0]
s_lire = (tete('À lire', 'https://agendasabauda.eu/articles/', 'Tous les articles') + '<div class="hp-lire"><div class="hp-lire-g">'
          f'<article class="hp-art"><a href="{esc(p0["u"])}"><div class="hp-img couvre" style="--bg:url(\'{esc(p0["img"])}\')"><img src="{esc(p0["img"])}" alt="" loading="lazy"></div>'
          f'<p class="hp-meta"><span class="hp-rub">{esc(p0["cat"])}</span></p><h3 class="hp-tg">{esc(p0["t"])}</h3><p class="hp-ex">{esc(p0["ex"][:180])}</p></a></article>'
          '<ul class="hp-arts">' + ''.join(f'<li><a href="{esc(p["u"])}"><span class="hp-rub">{esc(p["cat"])}</span>{esc(p["t"])}</a></li>' for p in [P[1], P[2], P[3], P[4]]) + '</ul></div>'
          '<aside class="hp-col"><div class="hp-nl"><p class="hp-nl-t">Recevez l’essentiel des quatre territoires</p><p>Chaque vendredi matin, dans votre boîte.</p>'
          '<a href="https://agendasabauda.eu/newsletter/">S’inscrire</a></div>'
          '<div class="hp-pub"><span>Publicité</span><div>Exemple d’emplacement<br>300 × 250</div></div></aside></div>')

# 5. Par territoire
s_ter = tete('Par territoire') + '<div class="hp-ters">'
for t, (c, u) in TERS.items():
    evs = sorted([e for e in E.values() if e['T'] == t and e['id'] not in vus and e['S'] > NOW and (e['E'] - e['S']).days <= 10],
                 key=lambda e: (e['S'].date(), -e.get('hs', 0)))[:3]
    s_ter += f'<div class="hp-ter-b hp-ter-{c}"><a class="hp-ter-n" href="{u}">{esc(t)} →</a><ul>'
    for e in evs:
        vus.add(e['id'])
        s_ter += f'<li><a href="{esc(e["u"])}"><span class="hp-date">{quand(e)}</span>{esc(e["t"])}</a></li>'
    s_ter += '</ul></div>'
s_ter += '</div>'

# 6. Par envie (allocation réelle des catégories)
ENV = [('Concerts', 'cat-concerts', 'https://agendasabauda.eu/evenements/categorie/concerts-musique/'),
       ('Expositions', 'cat-expositions', 'https://agendasabauda.eu/evenements/categorie/expositions-patrimoine/'),
       ('Gastronomie', 'cat-gastronomie', 'https://agendasabauda.eu/evenements/categorie/gastronomie-sagre/')]
s_env = tete('Par envie') + '<div class="hp-envies">'
for nom, k, u in ENV:
    evs = [E[i] for i in A[k] if i not in vus][:3]
    if len(evs) < 3:  # l'allocation a déjà servi plus haut : on complète par le meilleur score de la catégorie
        mot = {'Concerts': 'Concerts', 'Expositions': 'Expositions', 'Gastronomie': 'Gastronomie'}[nom]
        evs += sorted([e for e in E.values() if mot in e['cat'] and e['id'] not in vus and e not in evs and e['S'] > NOW],
                      key=lambda e: -e.get('hs', 0))[:3 - len(evs)]
    s_env += f'<div class="hp-envie"><a class="hp-env-n" href="{u}">{nom} →</a><ul class="hp-liste">' + ''.join(ligne(e) for e in evs) + '</ul></div>'
s_env += '</div>'

# Recherche + pavés (icônes de l'accueil, recopiées telles quelles)
h0 = open('home.html', encoding='utf-8').read()
icones = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>\s*(<svg width="34".*?</svg>)\s*(?:<[^>]+>\s*)*([^<]+)<', h0, re.S)[:6]
paves = ''.join(f'<a class="hp-pave" href="{u}">{re.sub(chr(10), " ", s)}<span>{html.escape(html.unescape(l.strip()))}</span></a>' for u, s, l in icones)
s_porte = ('<form class="hp-cherche" role="search" action="https://agendasabauda.eu/"><input type="search" name="s" placeholder="Un événement, une ville, un lieu…" aria-label="Rechercher">'
           '<button type="submit">Chercher</button></form><nav class="hp-paves" aria-label="Accès rapides">' + paves + '</nav>')

CSS = open('accueil.css', encoding='utf-8').read()
nb_we = len(we_court)
bandeau = (f'<p class="hp-test">Page de test de l’accueil (noindex). Instantané de la base du {NOW.day} {MOIS[NOW.month-1]} à {NOW.hour} h {NOW.minute:02d} : '
           f'il ne se met pas à jour tout seul. La vraie page d’accueil n’est pas modifiée.</p>')
corps = ('<div class="hp">' + bandeau + s_une + s_porte + s_we + s_7 + s_lire + s_ter + s_env + '</div>')
page = '<!-- wp:html -->\n<style>' + CSS + '</style>' + corps + '\n<!-- /wp:html -->'
assert '\n\n' not in page
open('home_test.html', 'w', encoding='utf-8').write(page)
print('une', une, '| we', [e['id'] for e in we], 'sur', nb_we, '| jours', [(j.day, len(x)) for j, x in jours], '| paves', len(icones), '| octets', len(page.encode()))
