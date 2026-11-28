"""Match a plot footprint to the same 80 m illustrative road corridor as the map."""
from .paths import FLOOD_DIR
import json,math
from pathlib import Path
from functools import lru_cache
DATA=json.loads((FLOOD_DIR/'flood-map-context.geojson').read_text(encoding='utf-8'))
INDEX=[]
for feature in DATA['features']:
    pts=[p for line in feature['geometry']['coordinates'] for p in line]
    INDEX.append((feature,(min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts))))
RADIUS_METERS=80
def distance(p,a,b):
 dx,dy=b[0]-a[0],b[1]-a[1];length=dx*dx+dy*dy
 t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length)) if length else 0
 return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)
def inside(p,ring):
 hit=False
 for a,b in zip(ring,ring[1:]):
  if (a[1]>p[1])!=(b[1]>p[1]) and p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0]:hit=not hit
 return hit
def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def segment_distance(a,b,c,d):
 if cross(a,b,c)*cross(a,b,d)<0 and cross(c,d,a)*cross(c,d,b)<0:return 0
 return min(distance(a,c,d),distance(b,c,d),distance(c,a,b),distance(d,a,b))
@lru_cache(maxsize=10000)
def matches(encoded):
 geometry=json.loads(encoded);kind=geometry['type'];coords=geometry['coordinates']
 rings=[[coords]] if kind=='Point' else coords if kind=='Polygon' else [ring for polygon in coords for ring in polygon] if kind=='MultiPolygon' else []
 if not rings:return []
 points=[p for ring in rings for p in ring];lon,lat=points[0];sx=111320*math.cos(math.radians(lat));sy=111320
 project=lambda p:((p[0]-lon)*sx,(p[1]-lat)*sy)
 geo_box=(min(p[0] for p in points)-80/sx,min(p[1] for p in points)-80/sy,max(p[0] for p in points)+80/sx,max(p[1] for p in points)+80/sy)
 rings=[[project(p) for p in ring] for ring in rings];pts=[p for ring in rings for p in ring]
 box=(min(p[0] for p in pts)-80,min(p[1] for p in pts)-80,max(p[0] for p in pts)+80,max(p[1] for p in pts)+80)
 found={}
 for feature,bounds in INDEX:
  if bounds[2]<geo_box[0] or bounds[0]>geo_box[2] or bounds[3]<geo_box[1] or bounds[1]>geo_box[3]:continue
  best=float('inf')
  for line in feature['geometry']['coordinates']:
   for c,d in zip(line,line[1:]):
    c,d=project(c),project(d)
    if max(c[0],d[0])<box[0] or min(c[0],d[0])>box[2] or max(c[1],d[1])<box[1] or min(c[1],d[1])>box[3]:continue
    for ring in rings:
     if len(ring)==1:best=min(best,distance(ring[0],c,d));continue
     if inside(c,ring) or inside(d,ring):best=0;break
     best=min(best,min(segment_distance(a,b,c,d) for a,b in zip(ring,ring[1:])))
  if best<=RADIUS_METERS:
   for rid in feature['properties']['recordIds']:
    if rid not in found or best<found[rid]['distanceMeters']:found[rid]={'id':rid,'distanceMeters':round(best,1),'roadName':feature['properties']['roadName']}
 return list(found.values())
