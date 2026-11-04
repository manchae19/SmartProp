import argparse,json
from pathlib import Path
from .index import OldIndex,DATA,ROOT
from .pipeline import Pipeline
from .sources import SOURCES

def main():
    parser=argparse.ArgumentParser(description='SmartProp V2: new IDs only, small private pilot, no DB writes')
    parser.add_argument('--max-new',type=int,default=40);parser.add_argument('--max-pages',type=int,default=2)
    parser.add_argument('--delay',type=float,default=3);parser.add_argument('--sources',nargs='+',choices=list(SOURCES),default=list(SOURCES))
    parser.add_argument('--export-only',action='store_true',help='Re-export cached V2 observations; no website requests')
    parser.add_argument('--output',type=Path,default=DATA/'data_raw/smart_crawler_v2/pilot_001')
    args=parser.parse_args()
    out=args.output.resolve();allowed=(DATA/'data_raw/smart_crawler_v2').resolve()
    if not out.is_relative_to(allowed):raise ValueError('Output must stay in the new V2 dataset directory')
    index=OldIndex.load();client,sql,before,metadata=index.add_mysql_readonly()
    runner=Pipeline(out,index,args.max_new,args.max_pages,args.delay)
    if not args.export_only:
        for source in args.sources:
            if runner.new_count>=runner.max_new and SOURCES[source].policy=='BOUNDED_INTERNAL_RESEARCH':continue
            runner.run_source(source)
    summary=runner.export();after=client.query(sql)
    metadata.update(checksums_before=before,checksums_after=after,unchanged=before==after)
    (out/'mysql-readonly-preflight.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf8')
    (out/'old-index-input-manifest.json').write_text(json.dumps(index.inputs,ensure_ascii=False,indent=2),encoding='utf8')
    if before!=after:raise RuntimeError('MySQL source changed during pilot; inspect before any further work')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
