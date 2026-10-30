from pathlib import Path
from lxml import html
import sys
sys.path.insert(0,'ai-services/app/data')
import collect_homedy_trial as c
sys.stdout.reconfigure(encoding='utf-8')
d=html.fromstring(Path('ai-services/app/data/data_raw/homedy/detail_sample.html').read_text(encoding='utf-8'))
h=d.xpath('//h1')[0];scope=next(a for a in h.iterancestors() if 'product-item' in (a.get('class') or '').split())
print('scope',len(scope.text_content()))
for item in scope.xpath('.//div['+c.cls('product-attributes--item')+']'):print('ATTR',item.text_content().strip())
for item in scope.xpath('.//div['+c.cls('product-info')+']/div'):print('INFO',c.text(item,'./p['+c.cls('lb-code')+']'),c.text(item,'./p['+c.cls('code')+']'))
