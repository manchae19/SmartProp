import importlib.util
from pathlib import Path
p=Path('ai-services/app/data/collect_homedy_trial.py')
s=importlib.util.spec_from_file_location('collector',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
assert m.parse_price('4,5 Tỷ')==4500000000
assert m.parse_price('4,6 Triệu')==4600000
assert m.parse_price('Thỏa thuận') is None
assert m.parse_price('60 Triệu/m2') is None
assert m.numeric('126,7')==126.7
base=p.parent/'data_raw/homedy'
links=m.listing_links((base/'listing.html').read_bytes())
r=m.parse_detail((base/'detail_sample.html').read_bytes(),links[0],m.now())
assert r['source_listing_id']=='3222595' and r['price_vnd']==4500000000 and r['area_sqm']==72
assert r['latitude'] is None and r['longitude'] is None
assert r['image_url']
print('PASS: price units, negotiated/per-m2 handling, sample detail scope/ID, missing coordinates, image metadata')
