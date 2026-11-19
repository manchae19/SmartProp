"""Extractive document answers with fresh reviewed sources, never property/legal certification."""
import re
from .config import GroundingError,RagUnavailable
from .document_store import conflicts
from .market import DISTRICTS
from .intent import fold
from .schemas import Citation
from .validator import validate_generated_answer
from .diagnostics import event

class DocumentAdvisor:
    def __init__(self,store,retriever,llm):self.store,self.retriever,self.llm=store,retriever,llm
    def reply(self,question,topic,district=None):
        base={'properties':[],'citations':[],'generation_mode':'EVIDENCE_ONLY','retrieval_mode':'TOOL_EVIDENCE_ONLY',
              'limitations':['Trích đoạn tài liệu không xác nhận pháp lý/quy hoạch của một căn nhà hoặc thửa đất cụ thể.']}
        def unavailable(kind,answer,status):
            return {**base,'answer':answer,'responseKind':kind,'extra':{'toolResult':{'name':'knowledge','status':status},'knowledgeTopic':topic}}
        q=fold(question)
        districts=[d for d in DISTRICTS if fold(d) in q]
        if len(districts)>1:return unavailable('CLARIFICATION_REQUIRED','Bạn muốn đối chiếu tài liệu cho khu vực nào trước?','NEEDS_CLARIFICATION')
        try:
            documents,expired=self.store.select(topic,districts[0] if districts else district)
        except RagUnavailable:
            return unavailable('KNOWLEDGE_SOURCE_UNAVAILABLE','Chưa có kho tài liệu đã duyệt cho câu hỏi này. Bạn có thể bổ sung nguồn chính thức; tôi không dùng tin rao để thay thế bằng chứng pháp lý/quy hoạch.','INSUFFICIENT_DATA')
        except (GroundingError,ValueError,KeyError,TypeError):
            return unavailable('KNOWLEDGE_SOURCE_UNAVAILABLE','Kho tài liệu không vượt qua kiểm tra nguồn và toàn vẹn dữ liệu; chưa thể dùng để trả lời.','INVALID_EVIDENCE')
        if not documents:
            return unavailable('STALE_KNOWLEDGE_DATA' if expired else 'INSUFFICIENT_KNOWLEDGE_EVIDENCE',
                               'Tài liệu phù hợp đã quá hạn rà soát; cần cập nhật nguồn trước khi sử dụng.' if expired else 'Chưa có tài liệu đã duyệt phù hợp chủ đề và phạm vi này.','STALE_DATA' if expired else 'INSUFFICIENT_DATA')
        try:hits=self.retriever.search(question,documents,k=4)
        except (RagUnavailable,GroundingError):
            return unavailable('KNOWLEDGE_SOURCE_UNAVAILABLE','Chưa truy xuất được tài liệu; đây là lỗi nguồn, không phải kết luận không có quy định hoặc thông tin.','SOURCE_UNAVAILABLE')
        if not hits:return unavailable('INSUFFICIENT_KNOWLEDGE_EVIDENCE','Chưa tìm thấy đoạn tài liệu đủ liên quan để trả lời câu hỏi này.','INSUFFICIENT_DATA')
        keys={d['metadata'].get('claimKey') for d in hits if d['metadata'].get('claimKey')}
        conflicting=conflicts([d for d in documents if d['metadata'].get('claimKey') in keys])
        if conflicting:
            # Ensure both structured assertions are exposed even when top-k favored one source.
            hits=[d for d in documents if d['metadata'].get('claimKey') in conflicting][:4]
        citations=[Citation(sourceId=d['sourceId'],url=d['url'],version=d['version'],contentHash=d['contentHash'],scope='PUBLIC',kind='SOURCE_DOCUMENT',title=d['metadata']['title']) for d in hits]
        sources=[{'sourceId':d['sourceId'],'url':d['url'],'version':d['version'],'title':d['metadata']['title'],
                  **{k:d['metadata'][k] for k in ('publisher','publishedAt','retrievedAt','validUntil','jurisdiction')}} for d in hits]
        extra={'documents':sources,'knowledgeTopic':topic,'toolResult':{'name':'knowledge','status':'CONFLICTING_EVIDENCE' if conflicting else 'OK'},
               'hybridRetrieval':{'method':hits[0].get('retrievalMethod','BM25_ONLY_DENSE_UNAVAILABLE'),'sourceIds':[d['sourceId'] for d in hits],'expiredExcluded':expired,'conflictingClaims':conflicting}}
        if conflicting:
            return {**base,'answer':'Các nguồn có khẳng định được gắn cùng mã đối chiếu nhưng nội dung khác nhau. Chưa thể chọn kết luận; hãy đối chiếu văn bản gốc và hiệu lực từng nguồn.','responseKind':'KNOWLEDGE_SOURCE_CONFLICT','citations':citations,'extra':extra}
        facts={'f'+str(i):{'text':d['text'],'sourceId':d['sourceId']} for i,d in enumerate(hits[:3])}
        selected=list(facts.values());generation={'accepted':False,'reason':'EXTRACTIVE_DOCUMENT_FALLBACK'}
        mode='EVIDENCE_ONLY'
        try:
            if getattr(self.llm,'output_kind',None)=='grounded_answer':
                generated=self.llm.answer(question,facts)
                sentences=validate_generated_answer(generated.raw,facts,[])
                selected=sentences;generation={**generated.metrics,'accepted':True,'sentences':sentences};mode='QWEN_GROUNDED_ANSWER'
        except (RagUnavailable,GroundingError):pass
        used={s['sourceId'] for s in selected}
        citations=[c for c in citations if c.sourceId in used];extra['documents']=[s for s in sources if s['sourceId'] in used]
        extra['generation']=generation
        event('document_retrieval',status='OK',count=len(citations),method=extra['hybridRetrieval']['method'])
        answer='Các trích đoạn từ tài liệu đã duyệt; hãy kiểm tra ngày ban hành và nguồn gốc trước khi áp dụng:\n'+'\n'.join(s['text'] for s in selected)
        return {**base,'answer':answer,'responseKind':'KNOWLEDGE_EVIDENCE','citations':citations,'extra':extra,'generation_mode':mode,
                'retrieval_mode':'E5_FAISS' if extra['hybridRetrieval']['method']=='BM25_E5_RRF' else 'TOOL_EVIDENCE_ONLY'}
