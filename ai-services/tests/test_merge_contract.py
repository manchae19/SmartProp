"""Integration regressions for the Backend-Huy/main reconciliation; no external services."""
import os
import sys
import unittest
from unittest.mock import Mock, patch
from pydantic import ValidationError
from fastapi import HTTPException
from app.rag.config import Settings, GroundingError
from app.rag.schemas import ChatRequest
from app.rag.tools import PublishedPropertyRepository
from app.rag.personalization import apply_area
from app.api.valuation_v1_3 import verify_internal_read, verify_internal_admin


class MergeContractTests(unittest.TestCase):
    def test_only_real_uuid_property_ids_are_accepted(self):
        uid='ABCDEF00-0000-4000-8000-000000000001'
        self.assertEqual(ChatRequest(question='giá căn này',propertyId=uid).propertyId,uid)
        with self.assertRaises(ValidationError):
            ChatRequest(question='giá căn này',propertyId='-'*36)

    def test_impossible_area_range_is_rejected(self):
        for fields in [dict(minAreaSqm=90,maxAreaSqm=80),dict(minAreaSqm=80,maxAreaSqm=80,minAreaExclusive=True)]:
            with self.subTest(fields=fields), self.assertRaises(ValidationError):
                ChatRequest(question='tìm nhà',**fields)

    def test_new_upper_area_bound_replaces_old_lower_bound(self):
        criteria={'minAreaSqm':'100','minAreaExclusive':True}
        apply_area(criteria,'Tìm nhà dưới 80m²')
        self.assertNotIn('minAreaSqm',criteria)
        self.assertEqual(criteria['maxAreaSqm'],'80')
        self.assertTrue(criteria['maxAreaExclusive'])

    def test_sql_uses_configured_target_and_read_only_views(self):
        settings=Settings(sql_enabled=True,sql_port=13317,sql_database='smartprop_test',
                          db_user='test_reader',db_password='fixture-only',sql_use_views=True)
        cursor=Mock();cursor.fetchone.return_value={'db':'smartprop_test','port':13317,'read_only':1}
        cursor.fetchall.return_value=[]
        connection=Mock();connection.cursor.return_value.__enter__=Mock(return_value=cursor)
        connection.cursor.return_value.__exit__=Mock(return_value=False)
        connect=Mock();connect.return_value.__enter__=Mock(return_value=connection)
        connect.return_value.__exit__=Mock(return_value=False)
        driver=Mock(connect=connect,cursors=Mock(DictCursor=object))
        with patch.dict(sys.modules,{'pymysql':driver}):
            self.assertEqual(PublishedPropertyRepository(settings).lookup(['listing-1']),[])
        self.assertEqual(connect.call_args.kwargs['port'],13317)
        self.assertEqual(connect.call_args.kwargs['database'],'smartprop_test')
        self.assertEqual(connect.call_args.kwargs['init_command'],'SET SESSION TRANSACTION READ ONLY')
        self.assertIn('FROM rag_public_properties',cursor.execute.call_args.args[0])
        connection.rollback.assert_called_once()

    def test_no_internal_default_or_admin_fallback(self):
        with patch.dict(os.environ,{'SMARTPROP_INTERNAL_KEY':'','SMARTPROP_INTERNAL_ADMIN_KEY':''}):
            with self.assertRaises(HTTPException) as failure:
                verify_internal_read('previous-default-key')
            self.assertEqual(failure.exception.status_code,503)
        with patch.dict(os.environ,{'SMARTPROP_INTERNAL_KEY':'r'*48,'SMARTPROP_INTERNAL_ADMIN_KEY':'a'*48}):
            self.assertTrue(verify_internal_read('r'*48))
            with self.assertRaises(HTTPException) as failure:
                verify_internal_admin('r'*48)
            self.assertEqual(failure.exception.status_code,403)
            self.assertTrue(verify_internal_admin('a'*48))

    def test_preview_requires_explicit_rollout(self):
        from app.api.valuation import predict_v1_3_preview
        with patch.dict(os.environ,{'SMARTPROP_V1_3_PREVIEW_ENABLED':'false'}):
            with self.assertRaises(HTTPException) as failure:
                predict_v1_3_preview(None,Mock())
            self.assertEqual(failure.exception.status_code,503)

if __name__=='__main__':unittest.main()
