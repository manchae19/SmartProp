"""Prepare only missing/stale public RAG artifacts; never import datasets or write MySQL."""
import argparse,json,os,sys,shutil,tempfile
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.rag.config import Settings,RagUnavailable,GroundingError
from app.rag.knowledge import KnowledgeStore,build_corpus
from app.rag.tools import BackendTools
from app.rag.embedding import E5Embedding
from app.rag.index_store import IndexStore

def prepare(settings,force=False,check_only=False):
 path=Path(settings.corpus_path);backend=BackendTools(settings);temp_path=None
 try:
  refresh=force;reason='FORCED' if force else None
  try:
   corpus=KnowledgeStore(path).load()
   if backend.amenity_summary()['catalogVersion']!=corpus['summary']['catalogVersion']:refresh=True;reason='CATALOG_CHANGED'
  except (OSError,ValueError,GroundingError,RagUnavailable):refresh=True;reason='MISSING_STALE_OR_INVALID'
  if refresh:
   if check_only:raise RuntimeError('RAG_DATA_NEEDS_REFRESH: run ops/update-rag-data.ps1')
   path.parent.mkdir(parents=True,exist_ok=True)
   handle=tempfile.NamedTemporaryFile(dir=path.parent,prefix='.public-corpus-',suffix='.json',delete=False);temp_path=Path(handle.name);handle.close()
   corpus=build_corpus(backend,temp_path)
  store=IndexStore(settings.index_dir,E5Embedding(settings.e5_path,settings.e5_revision))
  try:_,manifest=store.load(corpus['documents']);index_action='REUSED'
  except (GroundingError,RagUnavailable):
   if check_only:raise RuntimeError('RAG_INDEX_NEEDS_PREPARATION: run ops/update-rag-data.ps1')
   manifest=store.build(corpus['documents']);store.load(corpus['documents']);index_action='BUILT'
  if refresh:
   if path.exists():
    backup=Path(__file__).resolve().parents[2]/'.local-run'/'backups'/'rag-corpus';backup.mkdir(parents=True,exist_ok=True)
    shutil.copy2(path,backup/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json'))
   os.replace(temp_path,path);temp_path=None
  return {'corpus':'REFRESHED' if refresh else 'REUSED','reason':reason,'index':index_action,'documents':len(corpus['documents']),'builtAt':corpus['builtAt'],'version':manifest['version']}
 finally:
  backend.close()
  if temp_path is not None:temp_path.unlink(missing_ok=True)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--force',action='store_true');parser.add_argument('--check-only',action='store_true');args=parser.parse_args()
 print(json.dumps(prepare(Settings.from_env(),args.force,args.check_only),ensure_ascii=False))