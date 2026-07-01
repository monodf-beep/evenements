"""Gabarit « magazine » pour la newsletter Agenda Sabaudo.

Porté du gabarit magazine de l'Observatoire (Business Sabaudo) et adapté à
l'agenda culturel : mêmes bonnes pratiques (cadre AIDA), même structure —
héros « À la une », sommaire numéroté « Aussi cette semaine », cartes « Le tour
des territoires », favicons de source, pied éditorial — mais identité Agenda
Sabaudo et dates d'ÉVÉNEMENT (plages « du 5 au 8 juillet ») au lieu de dates de
publication.

Email responsive (600px, styles en ligne, structure en tableaux pour
Outlook/Gmail). Aucune dépendance externe.
"""
from __future__ import annotations

from html import escape

# Identité Agenda Sabaudo (bleu profond + rouge de Savoie — chaleureux, grand public).
BRAND = "#1a2b4a"       # bleu profond (masthead, intertitres)
ACCENT = "#c8102e"      # rouge de Savoie (CTA, point, accents)
INK = "#16202c"
MUTED = "#6b7280"
BORDER = "#e5e7eb"
BG = "#eef1f5"

_TERRITORY = {
    "Savoie": ("#e6effb", "#1a56b0", "Savoie"),
    "Piemonte": ("#fdeaea", "#b3261e", "Piémont"),
    "Vallee-Aoste": ("#e7f6ea", "#1e7d34", "Vallée d'Aoste"),
    "Nice": ("#fff1e0", "#b25e00", "Nice"),
}

_FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"


def favicon(domain: str, size: int = 64) -> str:
    return f"https://www.google.com/s2/favicons?domain={domain}&sz={size}"


def _tag(territory: str) -> str:
    _, dotc, label = _TERRITORY.get(territory, ("", "#64748b", territory or "—"))
    dot = (
        f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;'
        f'background:{dotc};margin-right:6px;vertical-align:middle;"></span>'
    )
    return (
        '<span style="display:inline-block;background:#eef2f7;color:#42526b;font-size:11px;'
        'font-weight:700;letter-spacing:.4px;text-transform:uppercase;padding:4px 11px;'
        f'border-radius:20px;vertical-align:middle;">{dot}{escape(label)}</span>'
    )


def _source(item: dict, size: int = 18) -> str:
    """Favicon + source + date d'événement (plage). Radar : ni favicon ni source."""
    name = escape(item.get("source", ""))
    dom = item.get("domain")
    icon = ""
    if dom:
        icon = (
            f'<img src="{favicon(dom)}" width="{size}" height="{size}" alt="" '
            f'style="border-radius:4px;vertical-align:middle;border:0;">&nbsp;'
        )
    date = escape(item.get("date_label", "") or "")
    sep = "&nbsp;·&nbsp;" if (name and date) else ""
    return (f'<span style="color:{MUTED};font-size:12px;font-weight:600;'
            f'vertical-align:middle;">{icon}{name}{sep}{date}</span>')


def _title(it: dict) -> str:
    """Titre cliquable si un lien existe, sinon texte simple (jamais de lien mort)."""
    label = escape(it["title"])
    if it.get("url"):
        return f'<a href="{escape(it["url"])}" style="color:{INK};text-decoration:none;">{label}</a>'
    return label


def _cta(url: str, label: str = "En savoir plus") -> str:
    if not url:
        return ""
    return (
        f'<a href="{escape(url)}" style="color:{ACCENT};font-size:14px;font-weight:700;'
        f'text-decoration:none;">{escape(label)} &rarr;</a>'
    )


def _button(url: str, label: str) -> str:
    return (
        f'<a href="{escape(url)}" style="display:inline-block;background:{ACCENT};color:#fff;'
        'font-size:14px;font-weight:700;text-decoration:none;padding:11px 22px;border-radius:8px;">'
        f"{escape(label)}</a>"
    )


def _dashboard_band(url: str) -> str:
    """Bandeau « Voir tout l'agenda » → site/tableau de bord. Vide si pas d'URL."""
    if not url:
        return ""
    return (
        '<tr><td style="padding:2px 36px 30px;text-align:center;">'
        f'<a href="{escape(url)}" style="display:inline-block;background:{BRAND};color:#fff;'
        'font-size:14px;font-weight:700;text-decoration:none;padding:12px 24px;border-radius:8px;">'
        "Voir tout l'agenda de la période &rarr;</a>"
        f'<div style="font-size:12px;color:{MUTED};margin-top:9px;line-height:1.5;">'
        "Cette lettre est une <strong>sélection</strong>. "
        "Retrouvez tout l'agenda sur le site.</div>"
        "</td></tr>"
    )


def _veille_link(url: str) -> str:
    """Petit lien sous « Aussi cette semaine » → tout l'agenda."""
    if not url:
        return ""
    return (
        '<div style="padding:14px 0 0;font-size:13px;">'
        f'<a href="{escape(url)}" style="color:{ACCENT};font-weight:700;text-decoration:none;">'
        "Et tout l'agenda de la période &rarr;</a></div>"
    )


def _header(week_label: str, tagline: str, logo_url: str | None = None) -> str:
    """Masthead éditorial blanc : surtitre + logo éditeur (petit) + titre + date."""
    logo_cell = ""
    if logo_url:
        logo_cell = (
            f'<td align="right" valign="middle"><img src="{logo_url}" alt="Une publication Cultura Sabauda" '
            'height="24" style="height:24px;width:auto;max-height:24px;max-width:170px;'
            'border:0;display:inline-block;"></td>'
        )
    return (
        '<tr><td style="padding:28px 36px 0;background:#fff;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
        f'<td valign="middle" style="font-size:11px;font-weight:800;letter-spacing:1.8px;'
        f'text-transform:uppercase;color:{ACCENT};">Agenda culturel</td>'
        f"{logo_cell}"
        "</tr></table></td></tr>"
        '<tr><td style="padding:14px 36px 0;background:#fff;">'
        f'<div style="font-size:34px;font-weight:800;letter-spacing:-.5px;color:{BRAND};line-height:1;">'
        f'Agenda Sabaudo<span style="color:{ACCENT};">.</span></div>'
        f'<div style="font-size:13px;color:{MUTED};margin-top:9px;letter-spacing:.2px;">{escape(tagline)}</div>'
        "</td></tr>"
        '<tr><td style="padding:18px 36px 0;background:#fff;">'
        f'<div style="height:1px;background:{BORDER};line-height:1px;font-size:0;">&nbsp;</div></td></tr>'
        '<tr><td style="padding:12px 36px 22px;background:#fff;">'
        f'<span style="font-size:11px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;color:{MUTED};">'
        f"{escape(week_label)}</span></td></tr>"
    )


def _eyebrow(text: str) -> str:
    """Intertitre de section : petit filet rouge + libellé en capitales."""
    return (
        '<div style="margin-bottom:14px;">'
        f'<span style="display:inline-block;width:26px;height:3px;background:{ACCENT};'
        'vertical-align:middle;margin-right:9px;border-radius:2px;"></span>'
        f'<span style="font-size:12px;font-weight:800;letter-spacing:1.5px;text-transform:uppercase;'
        f'color:{BRAND};vertical-align:middle;">{escape(text)}</span></div>'
    )


def _footer(logo_url: str | None = None) -> str:
    logo = ""
    if logo_url:
        logo = (
            f'<div style="margin-bottom:16px;"><img src="{logo_url}" alt="Agenda Sabaudo" '
            'width="44" height="44" style="width:44px;height:44px;max-width:44px;'
            'border:0;display:block;"></div>'
        )
    return (
        f'<tr><td style="background:#f7f9fc;padding:26px 36px;border-top:1px solid {BORDER};">'
        f"{logo}"
        f'<div style="color:{INK};font-size:13px;line-height:1.6;margin-bottom:12px;">'
        "💬 Un événement à signaler, une coquille repérée&nbsp;? "
        "<strong>Répondez à cet email</strong>, on lit tout."
        "</div>"
        f'<div style="color:{MUTED};font-size:12px;line-height:1.6;">'
        "<strong style=\"color:%s;\">Agenda Sabaudo</strong>, l'agenda des sorties de l'espace alpin occidental<br>"
        "Savoie · Piémont · Vallée d'Aoste · Nice<br>"
        "<em>Une sélection culturelle proposée par la rédaction, en collaboration avec Cultura Sabauda.</em><br>"
        '<a href="https://culturasabauda.eu" style="color:%s;">culturasabauda.eu</a> · '
        '<a href="{{ unsubscribe }}" style="color:#6b7280;">Se désabonner</a>'
        "</div></td></tr>" % (BRAND, MUTED)
    )


def _shell(inner: str, *, preheader: str) -> str:
    return (
        '<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        "<title>Agenda Sabaudo</title></head>"
        # Signature unique du gabarit — permet de distinguer à coup sûr un brouillon
        # fraîchement généré d'un ancien (chercher ASABAUDO-MAGAZINE-2026A).
        "<!-- ASABAUDO-MAGAZINE-2026A · gabarit magazine (Le tour des territoires) -->"
        f'<body style="margin:0;padding:0;background:{BG};font-family:{_FONT};">'
        f'<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{escape(preheader)}</div>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{BG};padding:24px 12px;">'
        '<tr><td align="center">'
        '<table role="presentation" width="600" cellpadding="0" cellspacing="0" '
        'style="width:600px;max-width:100%;background:#fff;border-radius:14px;overflow:hidden;">'
        '<tr><td style="padding:7px 32px;background:#fff;text-align:right;font-size:11px;color:#9aa3af;">'
        '<a href="{{ mirror }}" style="color:#9aa3af;text-decoration:none;">Voir en ligne</a></td></tr>'
        f"{inner}"
        "</table></td></tr></table></body></html>"
    )


def _credit(item: dict) -> str:
    """Légende de crédit sous une image (photo licenciable). Vide si pas de crédit."""
    c = (item.get("credit") or "").strip()
    if not c:
        return ""
    return (f'<div style="font-size:11px;color:{MUTED};margin-top:4px;'
            f'line-height:1.4;">📷 {escape(c)}</div>')


def _hero_block(hero: dict) -> str:
    """Section « À la une » (héros). hero doit contenir title/summary/territory."""
    img = ""
    if hero.get("image"):
        img = (
            f'<tr><td style="padding:0 36px;"><img src="{escape(hero["image"])}" width="528" alt="" '
            'style="width:100%;height:auto;display:block;border-radius:10px;border:0;">'
            f'{_credit(hero)}</td></tr>'
        )
    button = ""
    if hero.get("url"):
        button = (f'<div style="margin-top:16px;">'
                  f'{_button(hero["url"], hero.get("cta_label", "Découvrir l’événement"))}</div>')
    return (
        f'<tr><td style="padding:26px 36px 0;">{_eyebrow("À la une")}</td></tr>'
        + img
        + f'<tr><td style="padding:14px 36px 6px;">{_tag(hero["territory"])}&nbsp;&nbsp;{_source(hero)}'
          f'<div style="font-size:25px;font-weight:800;color:{INK};line-height:1.25;margin:11px 0 8px;">'
          f'{escape(hero["title"])}</div>'
          f'<div style="font-size:15px;color:#374151;line-height:1.6;">{escape(hero["summary"])}</div>'
          f"{button}</td></tr>"
    )


def _signaux_block(sig_list: list[dict], dashboard_url: str) -> str:
    """Section « Aussi cette semaine » : sommaire numéroté, cliquable."""
    if not sig_list:
        return ""
    signaux = ""
    for i, s in enumerate(sig_list, 1):
        border = "" if i == len(sig_list) else f"border-bottom:1px solid {BORDER};"
        badge = (
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>'
            f'<td width="24" height="24" align="center" valign="middle" '
            f'style="width:24px;height:24px;background:{BRAND};color:#fff;border-radius:50%;'
            f'font-size:12px;font-weight:800;font-family:{_FONT};line-height:24px;text-align:center;">'
            f'{i}</td></tr></table>'
        )
        s_title = escape(s["title"])
        if s.get("url"):
            s_title = f'<a href="{escape(s["url"])}" style="color:{INK};text-decoration:none;">{s_title}</a>'
        signaux += (
            "<tr>"
            f'<td width="36" valign="top" style="padding:12px 0;{border}">{badge}</td>'
            f'<td valign="top" style="padding:12px 0;{border}">{_tag(s["territory"])}'
            f'<div style="font-size:15px;color:{INK};font-weight:700;line-height:1.4;margin-top:5px;">'
            f'{s_title}</div></td></tr>'
        )
    return (
        f'<tr><td style="padding:30px 36px 4px;">{_eyebrow("Aussi cette semaine")}'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{signaux}</table>'
        f'{_veille_link(dashboard_url)}</td></tr>'
    )


def _cards_block(items: list[dict]) -> str:
    """Section « Le tour des territoires » : cartes détaillées."""
    if not items:
        return ""
    cards = ""
    for idx, it in enumerate(items):
        wrap = (
            "margin:0;padding:0;" if idx == len(items) - 1
            else f"border-bottom:1px solid {BORDER};margin:0 0 24px;padding:0 0 22px;"
        )
        img = ""
        if it.get("image"):
            img = (
                f'<tr><td style="padding:0 0 12px;"><img src="{escape(it["image"])}" width="528" alt="" '
                'style="width:100%;height:auto;display:block;border-radius:10px;border:0;">'
                f'{_credit(it)}</td></tr>'
            )
        cards += (
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="{wrap}">'
            f"{img}"
            f'<tr><td style="padding:0 0 8px;">{_tag(it["territory"])}&nbsp;&nbsp;{_source(it)}</td></tr>'
            f'<tr><td style="padding:0 0 6px;font-size:19px;font-weight:700;color:{INK};line-height:1.3;">'
            f'{_title(it)}</td></tr>'
            f'<tr><td style="font-size:15px;color:#374151;line-height:1.6;">{escape(it["summary"])}</td></tr>'
            f'<tr><td style="padding:10px 0 0;">{_cta(it.get("url", ""), it.get("cta_label", "En savoir plus"))}</td></tr>'
            "</table>"
        )
    return (
        f'<tr><td style="padding:30px 36px 34px;">{_eyebrow("Le tour des territoires")}'
        f'{cards}</td></tr>'
    )


def variant_magazine(data: dict) -> str:
    """Assemble l'email « magazine » Agenda Sabaudo à partir des données structurées.

    Clés attendues : week_label, preheader. Optionnelles : hero (dict), signaux
    (liste), items (liste), dashboard_url, logo_url, pictogram_url, tagline.
    Chaque événement : title, summary, territory ; optionnels url, source, domain,
    date_label, image, cta_label.
    """
    tagline = data.get("tagline", "Savoie · Piémont · Vallée d'Aoste · Nice")
    inner = _header(data["week_label"], tagline, data.get("logo_url"))
    if data.get("hero"):
        inner += _hero_block(data["hero"])
    inner += _signaux_block(data.get("signaux") or [], data.get("dashboard_url", ""))
    inner += _cards_block(data.get("items") or [])
    inner += _dashboard_band(data.get("dashboard_url", ""))
    inner += _footer(data.get("pictogram_url") or data.get("logo_url"))
    return _shell(inner, preheader=data.get("preheader", ""))
