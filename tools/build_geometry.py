"""Génère assets/geometry.js : cellules (pièces) de l'arrangement de cercles « fleur de vie »,
cercles rotatifs, pas de rotation vérifié et permutation des cellules.
Usage : python tools/build_geometry.py [chemin_image_originale]"""
import math, json, sys, os
import numpy as np
from scipy import ndimage
from skimage import measure
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE, 'model.py')).read())  # -> circles, h, OX, OY

S = 2                       # sur-échantillonnage
X0, Y0, X1, Y1 = 0, 150, 1024, 845
W, H = (X1 - X0) * S, (Y1 - Y0) * S
ys, xs = np.mgrid[0:H, 0:W]
X = X0 + (xs + 0.5) / S
Y = Y0 + (ys + 0.5) / S
inside_any = np.zeros((H, W), bool)
for c in circles:
    if c[1] == 'grand':
        inside_any |= (X - c[2]) ** 2 + (Y - c[3]) ** 2 < c[4] ** 2
sig = np.zeros((H, W), np.int64)
for b, c in enumerate(circles):
    sig |= (((X - c[2]) ** 2 + (Y - c[3]) ** 2 < c[4] ** 2).astype(np.int64) << b)
sig[~inside_any] = -1

# image d'origine pour l'échantillonnage des couleurs
art = None
if len(sys.argv) > 1:
    art = np.array(Image.open(sys.argv[1]).convert('RGB')).astype(float)
K, TX, TY = 1.185, 86.0, 106.0
REFS = {'plain': (128, 92, 62), 'grey': (72, 52, 35), 'dark': (70, 31, 4), 'orange': (175, 100, 6)}
REF_KEYS = list(REFS)
SMALL = 500   # pièces plus petites : couleur = voisin majoritaire (éclats aux points de tangence)
# Corrections manuelles éventuelles : (x, y) en coordonnées plateau -> couleur
OVERRIDES = []

def sample_shade(m):
    """Couleur d'une pièce : médiane des pixels intérieurs de l'artwork (bord érodé,
    traits noirs et gravures exclus), puis référence la plus proche."""
    dt = ndimage.distance_transform_edt(m)
    for margin in (4 * S, 2.5 * S, 1.5 * S, 0.5):
        sel = dt > margin
        if sel.sum() >= 30: break
    sy, sx = np.nonzero(sel)
    if len(sx) > 20000:
        idx = np.random.default_rng(0).choice(len(sx), 20000, replace=False); sx, sy = sx[idx], sy[idx]
    px = (X0 + (sx + .5) / S) * K + TX; py = (Y0 + (sy + .5) / S) * K + TY
    rgb = art[py.astype(int), px.astype(int)]
    rgb = rgb[rgb.max(axis=1) > 40]
    if not len(rgb): return 'plain'
    return classify_median(np.median(rgb, axis=0))

def classify_median(med):
    """Règles calibrées sur les pièces à lettres (couleurs connues) :
    orange = rouge vif peu de bleu ; neutre = bois clair ; brun foncé = très peu de bleu ; sinon gris-brun."""
    r, g, b = med
    ratio = b / max(r, 1)
    if r >= 120 and ratio < 0.30: return 'orange'
    if r >= 105: return 'plain'
    if ratio < 0.34: return 'dark'
    return 'grey'

cells = []
cell_masks = []
for s in np.unique(sig):
    if s < 0: continue
    lab, n = ndimage.label(sig == s)
    for k in range(1, n + 1):
        m = lab == k
        area = m.sum() / S / S
        if area < 8: continue
        yy, xx = np.nonzero(m)
        cx = X0 + (xx.mean() + 0.5) / S; cy = Y0 + (yy.mean() + 0.5) / S
        # point d'étiquette : centre de gravité si dans la cellule, sinon max de distance au bord
        ix, iy = int((cx - X0) * S), int((cy - Y0) * S)
        if 0 <= iy < H and 0 <= ix < W and m[iy, ix]:
            lx, ly = cx, cy
        else:
            dt = ndimage.distance_transform_edt(m)
            j = np.argmax(dt); lx = X0 + (j % W + 0.5) / S; ly = Y0 + (j // W + 0.5) / S
        pad = np.pad(m, 1).astype(float)
        conts = measure.find_contours(pad, 0.5)
        parts = []
        for ct in conts:
            if len(ct) < 6: continue
            ap = measure.approximate_polygon(ct, tolerance=0.45)
            pts = [(round(X0 + (p[1] - 1 + 0.5) / S, 1), round(Y0 + (p[0] - 1 + 0.5) / S, 1)) for p in ap]
            parts.append('M' + ' '.join(f'{a},{b}' for a, b in pts) + 'Z')
        shade = 'plain'; forced = False
        if art is not None:
            shade = sample_shade(m)
        for (ox, oy, sh) in OVERRIDES:
            jx, jy = int((ox - X0) * S), int((oy - Y0) * S)
            if 0 <= jy < H and 0 <= jx < W and m[jy, jx]: shade = sh; forced = True
        cell_masks.append(m)
        cells.append(dict(cx=round(cx, 2), cy=round(cy, 2), lx=round(lx, 1), ly=round(ly, 1), area=round(area, 1), d=''.join(parts), shade=shade, sig=int(s), forced=forced))

# petites pièces : couleur du voisin avec le plus long contact (hors autres petites pièces)
lab_img = np.full((H, W), -1, np.int32)
for i, m in enumerate(cell_masks): lab_img[m] = i
for i, (c, m) in enumerate(zip(cells, cell_masks)):
    if c['area'] >= SMALL or c.get('forced'): continue
    ring = ndimage.binary_dilation(m, iterations=3 * S) & ~m
    ids, cnt = np.unique(lab_img[ring], return_counts=True)
    votes = {}
    for j, n in zip(ids, cnt):
        if j < 0 or cells[j]['area'] < SMALL: continue
        votes[cells[j]['shade']] = votes.get(cells[j]['shade'], 0) + n
    if votes: c['shade'] = max(votes, key=votes.get)
for c in cells: c.pop('forced', None)
cells.sort(key=lambda c: (round(c['cy'] / 10), c['cx']))
for i, c in enumerate(cells): c['id'] = i
print('cellules :', len(cells))

def rot(x, y, cx, cy, deg):
    a = math.radians(deg); dx, dy = x - cx, y - cy
    return cx + dx * math.cos(a) - dy * math.sin(a), cy + dx * math.sin(a) + dy * math.cos(a)

# Cercles moyens (rouges, bleus, central) : la géométrie n'a qu'une symétrie d'ordre 2, mais le jeu les fait
# tourner par 90°. On construit un pas de 90° « au plus proche » : chaque paire échangée par le demi-tour
# est associée à une autre paire en 4-cycle (couplage de poids minimal), de sorte que 2 pas = demi-tour exact
# et 4 pas = identité. Les pièces atterrissent dans l'emplacement le plus proche (formes parfois différentes).
FORCE90 = ('rouge', 'bleu', 'centre')
def force90(mem, p180, ccx, ccy):
    import networkx as nx
    byid = {m['id']: m for m in mem}
    def cost(a, b):
        x, y = rot(byid[a]['cx'], byid[a]['cy'], ccx, ccy, 90)
        return math.hypot(byid[b]['cx'] - x, byid[b]['cy'] - y)
    pairs, seen, perm = [], set(), {}
    for m in mem:
        a = m['id']
        if p180[a] == a: perm[a] = a; continue
        if a in seen: continue
        pairs.append((a, p180[a])); seen |= {a, p180[a]}
    g, orient = nx.Graph(), {}
    for i, (a, a2) in enumerate(pairs):
        for j in range(i + 1, len(pairs)):
            b, b2 = pairs[j]
            o1 = cost(a, b) + cost(b, a2) + cost(a2, b2) + cost(b2, a)
            o2 = cost(a, b2) + cost(b2, a2) + cost(a2, b) + cost(b, a)
            orient[(i, j)] = o1 <= o2; g.add_edge(i, j, weight=-min(o1, o2))
    for i, j in nx.max_weight_matching(g, maxcardinality=True):
        i, j = min(i, j), max(i, j); (a, a2), (b, b2) = pairs[i], pairs[j]
        if not orient[(i, j)]: b, b2 = b2, b
        perm.update({a: b, b: a2, a2: b2, b2: a})
    bad = sum(1 for a, b in perm.items() if cost(a, b) > 2.0 or abs(byid[a]['area'] - byid[b]['area']) > 0.06 * byid[a]['area'] + 3)
    return perm, bad

out_circles = []
report = []
for c in circles:
    cid, fam, ccx, ccy, r, rotatable = c
    if not rotatable: continue
    mem = [cl for cl in cells if math.hypot(cl['cx'] - ccx, cl['cy'] - ccy) < r]
    step, perm, worst = None, None, None
    for st in (90, 180):
        ok = True; pm = {}; w = 0
        for cl in mem:
            x, y = rot(cl['cx'], cl['cy'], ccx, ccy, st)
            best = min(mem, key=lambda o: (o['cx'] - x) ** 2 + (o['cy'] - y) ** 2)
            d = math.hypot(best['cx'] - x, best['cy'] - y)
            w = max(w, d)
            if d > 2.0 or abs(best['area'] - cl['area']) > 0.06 * cl['area'] + 3:
                ok = False; break
            pm[cl['id']] = best['id']
        if ok and len(set(pm.values())) == len(pm):
            step, perm, worst = st, pm, w; break
    approx = 0
    if step == 180 and fam in FORCE90:
        perm, approx = force90(mem, perm, ccx, ccy); step = 90
    report.append((cid, fam, len(mem), step, worst, approx))
    out_circles.append(dict(id=cid, family=fam, cx=ccx, cy=ccy, r=round(r, 3), step=step,
                            members=[m['id'] for m in mem], perm=[[a, b] for a, b in (perm or {}).items()],
                            **({'approx': approx} if approx else {})))
for r_ in report: print(r_)
arcs = [dict(id=c[0], family=c[1], cx=c[2], cy=c[3], r=c[4]) for c in circles if not c[5]]
for c in cells: del c['sig']
geo = dict(h=h, origin=[OX, OY], art=dict(k=K, tx=TX, ty=TY), circles=out_circles, arcs=arcs, cells=cells)
dst = os.path.join(HERE, '..', 'assets', 'geometry.js')
with open(dst, 'w') as f:
    f.write('// Généré par tools/build_geometry.py — ne pas éditer à la main.\nwindow.GEOMETRY = ' + json.dumps(geo, separators=(',', ':')) + ';\n')
print('écrit', dst, os.path.getsize(dst), 'octets')
