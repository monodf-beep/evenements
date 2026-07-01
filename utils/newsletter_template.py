"""Gabarit HTML de la newsletter « Agenda Sabaudo » (adapté de l'Observatoire).

Email responsive (600px, styles en ligne, structure en tableaux pour Outlook/Gmail),
assemblé à partir d'événements : en-tête de marque, intro, cartes (image + pastille
territoire + source + date + titre + résumé + lien), pied de page avec la mention
« en collaboration avec Cultura Sabauda ». Aucune dépendance externe.
"""
from __future__ import annotations

from html import escape

# Identité Agenda Sabaudo (bleu profond + rouge de Savoie — chaleureux, grand public).
BRAND = "#1a2b4a"
ACCENT = "#c8102e"
INK = "#1a1a1a"
MUTED = "#6b7280"
BORDER = "#e5e7eb"
BG = "#eef1f5"

# Pastille par territoire : (fond, texte, libellé affiché).
_TERRITORY = {
    "Savoie": ("#e6effb", "#1a56b0", "Savoie"),
    "Piemonte": ("#fdeaea", "#b3261e", "Piémont"),
    "Vallee-Aoste": ("#e7f6ea", "#1e7d34", "Vallée d'Aoste"),
    "Nice": ("#fff1e0", "#b25e00", "Nice"),
}


def _territory_tag(territory: str) -> str:
    bg, fg, label = _TERRITORY.get(territory, ("#eceff3", "#374151", territory or "—"))
    return (
        f'<span style="display:inline-block;background:{bg};color:{fg};'
        'font-size:11px;font-weight:700;letter-spacing:.3px;text-transform:uppercase;'
        f'padding:3px 10px;border-radius:20px;">{escape(label)}</span>'
    )


def _card(item: dict) -> str:
    image = item.get("image")
    title = escape(item.get("title", ""))
    summary = escape(item.get("summary", ""))
    url = item.get("url", "")
    source = item.get("source", "")
    territory = item.get("territory", "")
    date = item.get("date", "")

    img_html = ""
    if image:
        img_html = (
            f'<tr><td style="padding:0 0 12px;"><img src="{escape(image)}" alt="" width="600" '
            'style="width:100%;max-width:600px;height:auto;display:block;border-radius:10px;border:0;"></td></tr>'
        )
    title_html = title
    if url:
        title_html = f'<a href="{escape(url)}" style="color:{INK};text-decoration:none;">{title}</a>'

    meta_bits = [_territory_tag(territory)]
    if date:
        meta_bits.append(f'<span style="color:{MUTED};font-size:12px;">🗓 {escape(date)}</span>')
    if source:
        meta_bits.append(f'<span style="color:{MUTED};font-size:12px;">{escape(source)}</span>')
    meta_html = "&nbsp;&nbsp;".join(meta_bits)

    link_html = ""
    if url:
        link_html = (
            f'<tr><td style="padding:10px 0 0;"><a href="{escape(url)}" '
            f'style="color:{ACCENT};font-size:14px;font-weight:600;text-decoration:none;">'
            "En savoir plus &rarr;</a></td></tr>"
        )

    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-bottom:1px solid {BORDER};margin:0 0 24px;padding:0 0 20px;">'
        f"{img_html}"
        f'<tr><td style="padding:0 0 8px;">{meta_html}</td></tr>'
        f'<tr><td style="padding:0 0 6px;"><span style="font-size:19px;font-weight:700;'
        f'color:{INK};line-height:1.3;">{title_html}</span></td></tr>'
        f'<tr><td style="font-size:15px;color:#374151;line-height:1.6;">{summary}</td></tr>'
        f"{link_html}"
        "</table>"
    )


def render_newsletter(
    *,
    title: str,
    subtitle: str,
    week_label: str,
    intro: str,
    items: list[dict],
    signature: str,
) -> str:
    """Assemble l'email complet et renvoie le HTML."""
    cards = "\n".join(_card(it) for it in items)
    intro_html = escape(intro)
    signature_html = escape(signature).replace("\n", "<br>")

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(title)}</title>
</head>
<body style="margin:0;padding:0;background:{BG};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{BG};padding:24px 12px;">
<tr><td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:600px;max-width:100%;background:#ffffff;border-radius:14px;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">

  <!-- En-tête -->
  <tr><td style="background:{BRAND};padding:28px 32px;">
    <div style="color:#ffffff;font-size:24px;font-weight:800;letter-spacing:.5px;">{escape(title)}</div>
    <div style="color:#aecbf0;font-size:14px;margin-top:4px;">{escape(subtitle)}</div>
    <div style="color:#ffffff;font-size:12px;margin-top:14px;text-transform:uppercase;letter-spacing:1px;border-top:2px solid {ACCENT};display:inline-block;padding-top:8px;">{escape(week_label)}</div>
  </td></tr>

  <!-- Intro -->
  <tr><td style="padding:26px 32px 8px;font-size:16px;color:{INK};line-height:1.6;">{intro_html}</td></tr>

  <!-- Événements -->
  <tr><td style="padding:20px 32px 4px;">
    {cards}
  </td></tr>

  <!-- Signature -->
  <tr><td style="padding:4px 32px 26px;font-size:15px;color:{INK};line-height:1.6;">{signature_html}</td></tr>

  <!-- Pied de page -->
  <tr><td style="background:#f7f9fc;padding:22px 32px;border-top:1px solid {BORDER};">
    <div style="color:{MUTED};font-size:12px;line-height:1.6;">
      <strong style="color:{BRAND};">Agenda Sabaudo</strong> — l'agenda des sorties de l'espace alpin occidental<br>
      Savoie · Piémont · Vallée d'Aoste · Nice<br>
      en collaboration avec <a href="https://culturasabauda.eu" style="color:{MUTED};">Cultura Sabauda</a>
      &nbsp;·&nbsp; <a href="{{{{ unsubscribe }}}}" style="color:{MUTED};">Se désabonner</a>
    </div>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>
"""
