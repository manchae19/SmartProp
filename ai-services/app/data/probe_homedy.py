from urllib.request import Request,urlopen
from urllib.error import HTTPError
from pathlib import Path
from lxml import html
P=Path(__file__).resolve().parent/'data_raw'/'homedy';P.mkdir(parents=True,exist_ok=True)
for name,url in [('robots.txt','https://homedy.com/robots.txt'),('listing.html','https://homedy.com/ban-nha-rieng-da-nang')]:
    try:
        with urlopen(Request(url,headers={'User-Agent':'SmartProp-Research/1.0'}),timeout=30) as r:data=r.read()
        (P/name).write_bytes(data)
        if name=='robots.txt':print(data.decode('utf-8','replace')[:18000])
        else:
            doc=html.fromstring(data)
            links=doc.xpath('//a[contains(@href,"-es") or contains(@href,"dieu-khoan") or contains(@href,"quy-che")]')
            for a in links[:25]:print(html.tostring(a,encoding='unicode')[:1200])
            print('scripts',[(s.get('type'),s.get('id')) for s in doc.xpath('//script')])
    except HTTPError as e:print(name,e.code)
