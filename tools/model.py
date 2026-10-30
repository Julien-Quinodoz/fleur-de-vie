import math
h=167.5; OX,OY=343,497
def P(i,j): return (OX+i*h, OY+j*h)
circles=[]  # (id, family, cx, cy, r, rotatable)
circles.append(('G','grand',*P(0,0),2*h,True))
circles.append(('D','grand',*P(2,0),2*h,True))
for n,(i,j) in {'TL':(-1,-1),'TC':(1,-1),'TR':(3,-1),'BL':(-1,1),'BC':(1,1),'BR':(3,1)}.items():
  circles.append(('d'+n,'disque',*P(i,j),(2-math.sqrt(2))*h,True))
for n,(i,j) in {'rG-haut':(0,-1),'rG-bas':(0,1),'rD-haut':(2,-1),'rD-bas':(2,1)}.items():
  circles.append((n,'rouge',*P(i,j),h,True))
for n,(i,j) in {'bG':(-1,0),'bD':(3,0)}.items():
  circles.append((n,'bleu',*P(i,j),h,True))
circles.append(('mC','centre',*P(1,0),h,True))
# non-rotatable arcs
used={(0,-1),(0,1),(2,-1),(2,1),(-1,0),(3,0),(1,0)}
for i in range(-3,6):
  for j in range(-3,4):
    if (i+j)%2 and (i,j) not in used:
      d=min(math.hypot(i,j),math.hypot(i-2,j))
      if d<3-1e-9: circles.append((f'a{i},{j}','arc-h',*P(i,j),h,False))
for i in range(-2,5,2):
  for j in range(-2,3,2):
    if (i,j) in [(0,0),(2,0)]: continue
    d=min(math.hypot(i,j),math.hypot(i-2,j))
    if d<4-1e-9: circles.append((f'A{i},{j}','arc-R',*P(i,j),2*h,False))
# Arcs de symétrie (absents de l'artwork) : pour que CHAQUE cercle rotatif (grands, disques, moyens,
# latéraux, central) ait un découpage intérieur invariant par 90°, le motif doit être invariant par
# rotation de 90° autour de tout point du réseau. Une rotation autour d'un point (impair+pair) échange
# les points (pair,pair) et (impair,impair) : il faut donc aussi des cercles de rayon 2h aux points
# (impair,impair) et des cercles de rayon « disque » aux points (pair,pair). Les 24 sont nécessaires
# (retirer n'importe lequel casse l'exactitude d'au moins un cercle).
def _meets_board(cx, cy, r):
  return any(math.hypot(cx-gx, cy-gy) < 2*h + r - 1e-6 for gx, gy in (P(0,0), P(2,0)))
for i in range(-3,6):
  for j in range(-3,4):
    if i%2 and j%2 and _meets_board(*P(i,j), 2*h) and math.hypot(*[a-b for a,b in zip(P(i,j),P(0,0))])>1e-9:
      circles.append((f'S{i},{j}','arc-sym',*P(i,j),2*h,False))
    if not i%2 and not j%2 and _meets_board(*P(i,j), (2-math.sqrt(2))*h):
      circles.append((f's{i},{j}','arc-sym',*P(i,j),(2-math.sqrt(2))*h,False))
