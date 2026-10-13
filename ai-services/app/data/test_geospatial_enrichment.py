"""Boundary checks: source pins must not silently become trainable property locations."""
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from geospatial_enrichment import (coordinate, distance, parse_osm, proximities,
                                   approved_review, query_for, covered)
import geospatial_enrichment as geo


class GeospatialTests(unittest.TestCase):
    def test_invalid_missing_and_zero_coordinates(self):
        for raw, expected in [({},'missing'), ({'latitude':16},'incomplete'),
            ({'latitude':'nan','longitude':108},'invalid'),
            ({'latitude':91,'longitude':108},'invalid'),
            ({'latitude':0,'longitude':0},'invalid_zero_zero')]:
            self.assertEqual(coordinate(raw), (None,expected))
        pair, state = coordinate({'latitude':'16.0','longitude':'108.2'})
        self.assertEqual(pair,(16,108.2))
        self.assertIn('unverified',state)

    def test_distance_in_metres_and_symmetric(self):
        self.assertEqual(distance((16,108),(16,108)),0)
        self.assertAlmostEqual(distance((0,0),(0,1)),111195.08,places=2)
        self.assertAlmostEqual(distance((16,108),(16.1,108.2)),
                               distance((16.1,108.2),(16,108)))

    def test_partial_osm_response_rejected(self):
        for data in ({'remark':'timeout','elements':[]}, {},
            {'elements':[{'type':'way','id':1,'tags':{'amenity':'school'}}]}):
            with self.assertRaises(ValueError):
                parse_osm(data)

    def test_osm_geometry_basis_and_typed_ids(self):
        data = {'elements':[
            {'type':'node','id':1,'lat':16,'lon':108,'tags':{'amenity':'school'}},
            {'type':'way','id':1,'center':{'lat':16.01,'lon':108.02},
             'tags':{'amenity':'hospital'}}]}
        pois = parse_osm(data)
        self.assertEqual([p['osm_id'] for p in pois],['node/1','way/1'])
        self.assertEqual(pois[1]['point_basis'],'bbox_center')
        self.assertEqual(pois[0]['ownership'],'unknown')
        data['elements'].append(data['elements'][0])
        with self.assertRaises(ValueError):
            parse_osm(data)

    def test_empty_map_is_missing_not_zero(self):
        values, status = proximities((16,108),[],[15.9,107.9,16.1,108.1])
        self.assertEqual(values['school_distance_m'],'')
        self.assertTrue(values['school_missing_within_3000m'])
        self.assertEqual(values['school_osm_id'],'')
        self.assertTrue(status.startswith('computed'))

    def test_search_radius_and_bbox_edge(self):
        bbox = [15.9,107.9,16.1,108.1]
        pois = [dict(kind='school',latitude=16.005,longitude=108,osm_id='node/1'),
                dict(kind='hospital',latitude=16.05,longitude=108,osm_id='node/2')]
        result, _ = proximities((16,108),pois,bbox)
        self.assertAlmostEqual(result['school_distance_m'],555.98,places=2)
        self.assertEqual(result['hospital_distance_m'],'')
        self.assertFalse(result['school_missing_within_3000m'])
        self.assertTrue(result['hospital_missing_within_3000m'])
        for pair in [(15.9,108),(16.2,108),(16,107.905)]:
            self.assertFalse(covered(pair,bbox))
            self.assertEqual(proximities(pair,pois,bbox)[0],{})

    def test_property_precision_evidence_and_reuse_all_required(self):
        row = dict(latitude='16',longitude='108',coordinate_origin='openstreetmap',
            precision='property',location_verified='True',reuse_for_ml_verified='True',
            evidence='Matched independent address survey evidence',reviewed_by='reviewer',
            reviewed_at='2026-10-12T13:00:00+07:00')
        self.assertTrue(approved_review(row))
        for field,value in [('precision','ward'),('location_verified','False'),
            ('reuse_for_ml_verified','False'),('evidence',''),('reviewed_by',''),
            ('reviewed_at','2026-10-12T13:00:00'),('coordinate_origin','google_maps'),
            ('coordinate_origin','listing_source_unverified')]:
            self.assertFalse(approved_review(dict(row,**{field:value})),(field,value))

    def test_query_scope_and_amenity_semantics(self):
        query = query_for([15.93,108.05,16.21,108.31])
        self.assertIn('nwr["amenity"="school"]',query)
        self.assertIn('nwr["leisure"="park"]',query)
        self.assertIn('out center;',query)
        for bbox in ([0,0,1,1],[15,107,17,108],[16,108,15,109]):
            with self.assertRaises(ValueError):
                query_for(bbox)

    def test_integration_unverified_pins_never_fill_training_features(self):
        # Synthetic fixtures only; no network or real model/label changes.
        with tempfile.TemporaryDirectory(dir=geo.BASE) as temporary:
            root = Path(temporary); audit = root/'audit'; osm = root/'osm'
            audit.mkdir(); osm.mkdir()
            rows = [dict(record_key='test:'+str(i),v3_cohort=split,pipeline_group='group:'+str(i),
                source='fixture',category='Nhà ở',pipeline_status='eligible',latitude='16',longitude='108')
                for i,split in enumerate(('train','validation','reserved'))]
            geo.write_csv(audit/'location_audit.csv',rows,list(rows[0]))
            geo.write_json(audit/'manifest.json',dict(input_sha256={},
                output_sha256={'location_audit.csv':geo.sha(audit/'location_audit.csv')}))
            geo.write_json(osm/'response.json',{'elements':[
                {'type':'node','id':1,'lat':16.005,'lon':108,'tags':{'amenity':'school'}}]})
            geo.write_json(osm/'metadata.json',dict(bbox=[15.9,107.9,16.1,108.1],
                response_sha256=geo.sha(osm/'response.json'),osm_base_timestamp='fixture'))
            review = dict(record_key='test:0',latitude='16',longitude='108',
                coordinate_origin='survey',precision='property',location_verified='True',
                reuse_for_ml_verified='True',evidence='synthetic fixture only',reviewed_by='test',
                reviewed_at='2026-10-12T13:00:00+07:00')
            geo.write_csv(root/'reviews.csv',[review],geo.REVIEW_FIELDS)
            with patch.object(geo,'OUT',root/'output'):
                output = geo.build_features(audit,osm,root/'reviews.csv')
                features = geo.read(output/'features.csv')
                preview = geo.read(output/'unverified_preview_DO_NOT_TRAIN.csv')
                self.assertEqual(len(features),2)  # reserved never enters features/preview
                self.assertEqual(features[0]['geospatial_ready'],'True')
                self.assertAlmostEqual(float(features[0]['school_distance_m']),555.98,places=2)
                self.assertEqual(features[1]['geospatial_ready'],'False')
                self.assertEqual(features[1]['school_distance_m'],'')
                self.assertEqual([r['record_key'] for r in preview],['test:1'])
                self.assertEqual(preview[0]['can_train'],'False')
                self.assertNotIn('price_million',features[0])
                self.assertEqual(geo.build_features(audit,osm,root/'reviews.csv'),output)
                # Altered audit data must fail before computing a new version.
                rows[0]['latitude']='15'
                geo.write_csv(audit/'location_audit.csv',rows,list(rows[0]))
                with self.assertRaises(ValueError):
                    geo.build_features(audit,osm,root/'reviews.csv')


if __name__ == '__main__':
    unittest.main()
