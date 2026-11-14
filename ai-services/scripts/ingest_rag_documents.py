"""Reviewed document intake. Default dry-run; --write atomically replaces the document snapshot."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.rag.ingestion import intake,write_corpus

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--report',type=Path)
    parser.add_argument('--fetch-urls',action='store_true')
    parser.add_argument('--write',action='store_true')
    parser.add_argument('--allow-empty',action='store_true',help='Explicitly remove every document from this snapshot')
    args=parser.parse_args()
    corpus,report=intake(args.manifest,args.fetch_urls)
    report['dryRun']=not args.write
    if args.output.resolve()==args.manifest.resolve():parser.error('Output must not overwrite manifest')
    if args.report and args.report.resolve() in (args.output.resolve(),args.manifest.resolve()):parser.error('Report path conflicts with input/output')
    inputs={(args.manifest.parent/s['path']).resolve() for s in json.loads(args.manifest.read_text(encoding='utf-8-sig')).get('sources',[]) if isinstance(s,dict) and s.get('path')}
    if args.output.suffix.lower()!='.json' or args.output.resolve() in inputs or args.report and args.report.resolve() in inputs:parser.error('Output/report must not overwrite source documents')
    if args.write:write_corpus(corpus,report,args.output,args.allow_empty)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))
    return 2 if report['blocked'] else 0
if __name__=='__main__':raise SystemExit(main())
