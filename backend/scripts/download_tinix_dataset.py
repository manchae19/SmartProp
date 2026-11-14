"""Download immutable original TiniX Parquet shards to the research workspace.
No Hugging Face token, account, MySQL access or full-dataset RAM load required.
"""
import hashlib,json
from pathlib import Path
import requests
import pyarrow.parquet as pq
from tinix_dataset import OUT,DATASET,REVISION,LICENSE,save
def main():
    OUT.mkdir(parents=True,exist_ok=True);cache=OUT/'parquet';cache.mkdir(exist_ok=True);s=requests.Session()
    r=s.get(f'https://huggingface.co/api/datasets/{DATASET}/revision/{REVISION}',timeout=60);r.raise_for_status();meta=r.json()
    if meta['sha']!=REVISION or meta['cardData']['license']!=LICENSE:raise RuntimeError('Unexpected dataset revision/license')
    save('metadata.json',meta)
    r=s.get(f'https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/README.md',timeout=60);r.raise_for_status();(OUT/'card.md').write_text(r.text,encoding='utf8')
    r=s.get(f'https://huggingface.co/api/datasets/{DATASET}/tree/{REVISION}',timeout=60);r.raise_for_status();tree=r.json();save('tree.json',tree)
    inventory=[]
    for item in sorted(tree,key=lambda x:x['path']):
        name=item['path']
        if not name.endswith('.parquet'):continue
        if not __import__('re').fullmatch(r'shard_\d{4}[.]parquet',name):raise RuntimeError('Unexpected shard path')
        path=cache/name;expected=item.get('lfs',{}).get('oid');size=item['size']
        if not expected:raise RuntimeError('Missing immutable LFS checksum')
        if not path.exists():
            with s.get(f'https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/{name}',stream=True,timeout=(30,120)) as r:
                r.raise_for_status()
                with path.with_suffix('.part').open('wb') as f:
                    for chunk in r.iter_content(2**20):f.write(chunk)
            path.with_suffix('.part').replace(path)
        h=hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda:f.read(2**20),b''):h.update(chunk)
        if path.stat().st_size!=size or h.hexdigest()!=expected:raise RuntimeError('Shard checksum mismatch:'+name)
        p=pq.ParquetFile(path);inventory.append(dict(path=name,sha256=h.hexdigest(),bytes=size,rows=p.metadata.num_rows,schema=str(p.schema_arrow)))
        print(f'VERIFIED {name}: {p.metadata.num_rows} rows',flush=True)
    save('download-manifest.json',dict(dataset=DATASET,revision=REVISION,license=LICENSE,files=inventory))
if __name__=='__main__':main()
