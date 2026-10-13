from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urljoin
from lxml import html
P=Path('ai-services/app/data/data_raw/homedy')
d=html.fromstring((P/'listing.html').read_text(encoding='utf-8'))
u=urljoin('https://homedy.com/',d.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," product-item ")]//a[contains(@href,"-es")]/@href')[0])
with urlopen(Request(u,headers={'User-Agent':'SmartProp-Research/1.0'}),timeout=30) as r:(P/'detail_sample.html').write_bytes(r.read())
print(u)
