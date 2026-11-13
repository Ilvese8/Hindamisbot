"""Krundi plaanijoonis (SVG) ja hinnavahemiku mõõtjoon.

Kujud on L-EST97 meetrites (maakatastri WFS ja ehitisregister), seega joonis on mõõtkavas:
krundi piir katastrikaardi magentaga, piiripunktid, servade pikkused, viirutatud hoone, põhjanool, mõõtkava.
"""
from __future__ import annotations

import html
import math

MAGENTA = "#C0185F"
TUSS = "#18222D"
MÕÕT = "#2B6F7E"
VÕRK = "#D6DBD4"

TEEMAD = {
    # hele: katastrikaardi värvid paberil
    "hele": dict(piir=MAGENTA, täide=MAGENTA, täide_op=".06", hoone=TUSS, viirutus=TUSS, võrk=VÕRK, koord="#8A958F",
                 mõõt=MÕÕT, punkt_täide="#FBFCFA", nool=TUSS, tunnus=MAGENTA, taust=None),
    # tume: navy taust, laimiroheline piir
    "tume": dict(piir="#D7FF6E", täide="#D7FF6E", täide_op=".07", hoone="#F2F7FB", viirutus="#F2F7FB",
                 võrk="rgba(255,255,255,.07)", koord="#7F96AB", mõõt="#9FD4F5", punkt_täide="#1E2B3A",
                 nool="#F2F7FB", tunnus="#D7FF6E", taust="#1E2B3A"),
}


def _nice(x: float) -> float:
    """Ümar samm (1, 2, 5 × 10ⁿ), mis on ≤ x."""
    if x <= 0:
        return 1
    p = 10 ** math.floor(math.log10(x))
    for k in (5, 2, 1):
        if k * p <= x:
            return k * p
    return p


def _ringid(kuju) -> list:
    return [r for r in (kuju or []) if r and len(r) >= 3]


def plaan_svg(krunt: list | None, hoone: list | None, tunnus: str | None = None, keel: str = "et",
              w: int = 560, h: int = 460, teema: str = "hele") -> str | None:
    c = TEEMAD[teema]
    krunt, hoone = _ringid(krunt), _ringid(hoone)
    if not krunt and not hoone:
        return None
    pts = [p for r in (krunt or hoone) for p in r]
    minx, maxx = min(p[0] for p in pts), max(p[0] for p in pts)
    miny, maxy = min(p[1] for p in pts), max(p[1] for p in pts)
    bw, bh = max(maxx - minx, 1.0), max(maxy - miny, 1.0)
    marg = 58
    s = min((w - 2 * marg) / bw, (h - 2 * marg) / bh)
    ox = (w - bw * s) / 2
    oy = (h - bh * s) / 2

    def X(x):
        return ox + (x - minx) * s

    def Y(y):
        return h - (oy + (y - miny) * s)

    def tee(r):
        return "M" + " L".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in r) + " Z"

    osad = [f'<svg class="plaan" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="{"Krundi plaan" if keel == "et" else "Plot plan"}">',
            f'<defs><pattern id="viirutus-{teema}" width="6" height="6" patternUnits="userSpaceOnUse" '
            f'patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="{c["viirutus"]}" '
            f'stroke-width="1.4"/></pattern></defs>']
    if c["taust"]:
        osad.append(f'<rect width="{w}" height="{h}" fill="{c["taust"]}"/>')

    # Joonestusvõrk L-EST97 koordinaatidel (ümarad meetrid)
    samm = _nice(max(bw, bh) / 4)
    vx0 = math.floor((minx - (ox / s)) / samm) * samm
    vy0 = math.floor((miny - (oy / s)) / samm) * samm
    x = vx0
    while X(x) <= w:
        if X(x) >= 0:
            osad.append(f'<line x1="{X(x):.1f}" y1="0" x2="{X(x):.1f}" y2="{h}" stroke="{c["võrk"]}" stroke-width="1"/>')
            osad.append(f'<text x="{X(x) + 3:.1f}" y="13" class="koord" fill="{c["koord"]}">{x:,.0f}</text>'
                        .replace(",", " "))
        x += samm
    y = vy0
    while Y(y) >= 0:
        if Y(y) <= h:
            osad.append(f'<line x1="0" y1="{Y(y):.1f}" x2="{w}" y2="{Y(y):.1f}" stroke="{c["võrk"]}" stroke-width="1"/>')
            osad.append(f'<text x="4" y="{Y(y) - 4:.1f}" class="koord" fill="{c["koord"]}">{y:,.0f}</text>'
                        .replace(",", " "))
        y += samm

    # Krunt, piiripunktid ja servade pikkused
    for r in krunt:
        osad.append(f'<path d="{tee(r)}" fill="{c["täide"]}" fill-opacity="{c["täide_op"]}" stroke="none"/>')
        osad.append(f'<path class="piir" pathLength="1" d="{tee(r)}" fill="none" stroke="{c["piir"]}" '
                    f'stroke-width="2.4" stroke-linejoin="round"/>')
        ümbermõõt = sum(math.dist(r[i], r[(i + 1) % len(r)]) for i in range(len(r)))
        cx = sum(p[0] for p in r) / len(r)
        cy = sum(p[1] for p in r) / len(r)
        for i in range(len(r) - 1):
            (x1, y1), (x2, y2) = r[i], r[i + 1]
            pikkus = math.dist((x1, y1), (x2, y2))
            if pikkus < ümbermõõt * 0.07 or pikkus * s < 46:
                continue
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            nx, ny = (y2 - y1) / pikkus, -(x2 - x1) / pikkus           # normaal
            if (mx + nx - cx) ** 2 + (my + ny - cy) ** 2 < (mx - cx) ** 2 + (my - cy) ** 2:
                nx, ny = -nx, -ny                                       # väljapoole
            tx, ty = X(mx) + nx * 13, Y(my) - ny * 13
            nurk = math.degrees(math.atan2(-(y2 - y1), x2 - x1))
            if nurk > 90:
                nurk -= 180
            if nurk < -90:
                nurk += 180
            osad.append(f'<text class="mõõt" fill="{c["mõõt"]}" x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle" dominant-baseline="middle" '
                        f'transform="rotate({nurk:.1f} {tx:.1f} {ty:.1f})">{pikkus:.1f} m</text>')
        for px, py in r[:-1] if r[0] == r[-1] else r:
            osad.append(f'<circle class="punkt" cx="{X(px):.1f}" cy="{Y(py):.1f}" r="3.4" fill="{c["punkt_täide"]}" '
                        f'stroke="{c["piir"]}" stroke-width="1.8"/>')

    # Hoone
    for r in hoone:
        osad.append(f'<path class="hoone" d="{tee(r)}" fill="url(#viirutus-{teema})" stroke="{c["hoone"]}" '
                    f'stroke-width="1.6" stroke-linejoin="round"/>')

    # Põhjanool
    osad.append(f'<g transform="translate({w - 34},{38})"><path d="M0,-18 L7,8 L0,3 L-7,8 Z" fill="{c["nool"]}"/>'
                f'<text x="0" y="23" text-anchor="middle" class="n" fill="{c["nool"]}">N</text></g>')
    # Mõõtkava
    pikk = _nice(max(bw, bh) * 0.25)
    lp = pikk * s
    x0, y0 = 18, h - 22
    osad.append(f'<g class="skaala"><rect x="{x0}" y="{y0}" width="{lp / 2:.1f}" height="5" fill="{c["nool"]}"/>'
                f'<rect x="{x0 + lp / 2:.1f}" y="{y0}" width="{lp / 2:.1f}" height="5" fill="none" '
                f'stroke="{c["nool"]}" stroke-width="1"/>'
                f'<text x="{x0}" y="{y0 - 6}" class="koord" fill="{c["koord"]}">0</text>'
                f'<text x="{x0 + lp:.1f}" y="{y0 - 6}" class="koord" fill="{c["koord"]}" text-anchor="end">{pikk:g} m'
                f'</text></g>')
    if tunnus:
        osad.append(f'<text x="{w - 16}" y="{h - 16}" text-anchor="end" class="tunnus" fill="{c["tunnus"]}">'
                    f'{html.escape(tunnus)}</text>')
    osad.append("</svg>")
    return "".join(osad)


def mõõtjoon_svg(madal: float, väärtus: float, kõrge: float, w: int = 420, h: int = 58,
                 joon: str = MÕÕT, märk: str = MAGENTA) -> str:
    """Hinnavahemik joonestaja mõõtjoonena: abijooned, kaldkriipsud otstes, märk hinnangu kohal."""
    x0, x1 = 10, w - 10
    pos = x0 if kõrge == madal else x0 + (väärtus - madal) / (kõrge - madal) * (x1 - x0)
    y = 26
    MÕÕT, MAGENTA = joon, märk  # noqa: N806
    return (f'<svg class="mõõtjoon" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
            f'<line x1="{x0}" y1="8" x2="{x0}" y2="{y + 10}" stroke="{MÕÕT}" stroke-width="1"/>'
            f'<line x1="{x1}" y1="8" x2="{x1}" y2="{y + 10}" stroke="{MÕÕT}" stroke-width="1"/>'
            f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{MÕÕT}" stroke-width="1.4"/>'
            f'<line x1="{x0 - 5}" y1="{y + 5}" x2="{x0 + 5}" y2="{y - 5}" stroke="{MÕÕT}" stroke-width="2"/>'
            f'<line x1="{x1 - 5}" y1="{y + 5}" x2="{x1 + 5}" y2="{y - 5}" stroke="{MÕÕT}" stroke-width="2"/>'
            f'<path d="M{pos:.1f},{y - 3} l-6,-10 h12 Z" fill="{MAGENTA}"/>'
            f'<line x1="{pos:.1f}" y1="{y - 3}" x2="{pos:.1f}" y2="{y + 8}" stroke="{MAGENTA}" stroke-width="2"/>'
            f'</svg>')
