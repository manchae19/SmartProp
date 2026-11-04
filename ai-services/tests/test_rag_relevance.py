"""Focused empty-search routing regression. Fixtures never enter live storage."""
import unittest
from unittest.mock import Mock
from app.rag.config import RagUnavailable
from app.rag.intent import asks_for_amenities, empty_search_answer
from app.rag.knowledge import document, digest
from app.rag.orchestrator import ChatOrchestrator
from app.rag.schemas import ChatRequest


class RelevanceTests(unittest.TestCase):
    def service(self):
        backend, repository, knowledge, retriever, model = [Mock() for _ in range(5)]
        self.doc = document('poi-evidence:fixture', 'Bằng chứng kiểm thử cô lập, không phải dữ liệu thật.',
            'http://127.0.0.1:8080/api/v1/amenities/fixture', 'UNIT', 'POI_EVIDENCE',
            {'areaId':'fixture','district':'Hải Châu','name':'Fixture','category':'HOSPITAL','attributionBasis':'TEST_ONLY'})
        knowledge.load.return_value = {'summary':{'catalogVersion':'UNIT'},'contentHash':'unit','documents':[self.doc]}
        backend.amenity_summary.return_value = {'catalogVersion':'UNIT'}
        backend.recommend.return_value = {'mode':'SAFE','method':'HEURISTIC_V1_1','topProperties':[],'eligibleCandidateCount':0,'topAreas':[],'warnings':[]}
        backend.settings.backend_url = 'http://127.0.0.1:8080'
        retriever.search.return_value = [self.doc]
        model.plan.return_value = '{"factIds":["f0"]}'
        return ChatOrchestrator(backend,repository,knowledge,retriever,model),backend,repository,retriever,model

    def test_budget_empty_skips_unrequested_poi_model_and_sql(self):
        service,backend,sql,retriever,model=self.service()
        result=service.chat(ChatRequest(question='Tôi có 2 tỷ, có bất động sản công khai phù hợp không?'))
        self.assertEqual(result.evidence['responseKind'],'NO_MATCHES')
        self.assertEqual(result.generationMode,'EVIDENCE_ONLY')
        self.assertEqual(result.citations,[]);self.assertEqual(result.evidence['retrievedSourceIds'],[])
        self.assertIn('2.000.000.000 đồng',result.answer);self.assertIn('nhà ở, căn hộ hay đất nền',result.answer)
        self.assertIn('không phải kết luận về toàn bộ thị trường',result.answer)
        self.assertEqual(result.evidence['recommendationSearch']['criteriaHash'],digest(result.evidence['criteria']))
        retriever.search.assert_not_called();model.answer.assert_not_called();model.plan.assert_not_called();sql.lookup.assert_not_called()
        self.assertEqual(backend.recommend.call_args.args[0]['budgetVnd'],'2000000000')

    def test_explicit_amenity_question_keeps_real_evidence_path_and_citations(self):
        service,backend,sql,retriever,model=self.service()
        result=service.chat(ChatRequest(question='Tôi có 2 tỷ, Hải Châu có bệnh viện nào?'))
        retriever.search.assert_called_once();model.plan.assert_called_once()
        self.assertEqual(result.citations[0].sourceId,self.doc['sourceId'])
        self.assertEqual(result.citations[0].contentHash,self.doc['contentHash'])
        self.assertNotIn('responseKind',result.evidence)

    def test_strict_no_results_does_not_fake_qwen_generation(self):
        service,_,_,retriever,model=self.service()
        with self.assertRaises(RagUnavailable):
            service.chat(ChatRequest(question='Tôi có 2 tỷ, tìm bất động sản.',requireGeneration=True))
        retriever.search.assert_not_called();model.answer.assert_not_called()

    def test_amenity_routing_does_not_confuse_rental_or_pronouns_with_market(self):
        for q in ['2 tỷ mua để cho thuê','Cho tôi biết có nhà 2 tỷ không?','Tôi có 2 tỷ cho gia đình','Thị trường có nhà 2 tỷ không?']:
            self.assertFalse(asks_for_amenities(q),q)
        for q in ['Hải Châu có bệnh viện nào?','2 tỷ gần trường nào?','gần chợ Cồn','gan cho Con','có tiện ích gì?','nhà gần siêu thị']:
            self.assertTrue(asks_for_amenities(q),q)

    def test_empty_answer_preserves_fractional_budget_and_district(self):
        result=empty_search_answer({'budgetVnd':'2000000000.05','district':'Hải Châu','ward':None})
        self.assertIn('2.000.000.000,05 đồng tại Hải Châu',result)

    def test_positive_property_path_still_crosschecks_sql_and_cites(self):
        service,backend,sql,retriever,model=self.service()
        backend.recommend.return_value['topProperties']=[{'id':'property:fixture','priceVnd':10,'areaSqm':2,'score':80,'district':'Hải Châu','ward':None,'source':{'kind':'PROPERTY','recordKey':'fixture'}}]
        sql.lookup.return_value=[{'id':'fixture','price':10,'area_sqm':2}]
        result=service.chat(ChatRequest(question='Tôi có 2 tỷ, tìm nhà.'))
        sql.lookup.assert_called_once();retriever.search.assert_called_once()
        self.assertTrue(any(c.sourceId=='recommendation:property:fixture' for c in result.citations))
        self.assertEqual(result.evidence['sql']['status'],'READ_ONLY_MATCHED')
