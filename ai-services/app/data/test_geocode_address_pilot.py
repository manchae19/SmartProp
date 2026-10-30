"""Safety and checkpoint tests using synthetic responses, no live requests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import geocode_address_pilot as pilot
from training_v3_common import write_csv


class AddressPilotTests(unittest.TestCase):
    def row(self, key='chotot:1'):
        row = dict(record_key=key, street_raw='Đường Phạm Hùng', ward_raw='Phường Hòa Xuân',
            district_raw='Quận Cẩm Lệ', priority='1', address_query='Đường Phạm Hùng, Đà Nẵng',
            google_maps_url='https://www.google.com/maps/search/?api=1&query=address')
        params = pilot.query_params(row)
        row.update(query_id=pilot.digest(params), params_json=json.dumps(params))
        return row

    def result(self, road='Phạm Hùng', country='vn'):
        return dict(lat='16.01', lon='108.20', display_name='Phạm Hùng, Đà Nẵng, Việt Nam',
                    address={'road':road, 'country_code':country, 'house_number':'123'}, osm_id=1, osm_type='way')

    def test_returned_house_number_cannot_invent_verified_property(self):
        assessment = pilot.assess(self.row(), self.result())
        self.assertEqual(assessment['precision'], 'street_reference')
        self.assertFalse(assessment['location_verified'])
        self.assertFalse(assessment['model_feature_approved'])

    def test_wrong_road_or_country_is_unresolved(self):
        for result in [self.result(road='Võ Chí Công'), self.result(country='us')]:
            self.assertEqual(pilot.assess(self.row(), result)['precision'], 'unresolved_candidate')

    def test_query_excludes_sensitive_and_label_fields(self):
        row = self.row()
        row.update(title='Nhà giá 4 tỷ, điện thoại...', latitude='16.04', price_million='4000')
        params = pilot.query_params(row)
        self.assertEqual(set(params), {'street', 'city', 'countrycodes', 'format', 'addressdetails', 'limit', 'accept-language'})
        self.assertEqual(params['street'], 'Phạm Hùng')

    def test_reject_nonfinite_geocoder_response(self):
        result = self.result()
        result['lat'] = 'NaN'
        with self.assertRaises(ValueError):
            pilot.validate_results([result])

    def test_single_failed_query_does_not_become_80_http_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = self.row()
            duplicate = self.row('chotot:2')
            other = self.row('chotot:3')
            other['street_raw'] = 'Đường Võ Chí Công'
            params = pilot.query_params(other)
            other.update(query_id=pilot.digest(params), params_json=json.dumps(params))
            queue = [row, duplicate, other]
            write_csv(root/'queue.csv', queue, list(row))
            pilot.save(pilot.cache_path(root, pilot.ENDPOINT, row['query_id']), dict(
                endpoint=pilot.ENDPOINT, params=json.loads(row['params_json']), state='service_error', http_status=403))
            _, summary = pilot.report(root, pilot.ENDPOINT, queue)
            self.assertEqual(summary['unique_queries_attempted'], 1)
            self.assertEqual(summary['states'], {'service_error':2, 'not_requested':1})
            self.assertEqual(summary['approved_model_features'], 0)
            with patch.object(pilot, 'urlopen', side_effect=AssertionError('No request during resume/report')):
                pilot.report(root, pilot.ENDPOINT, queue)

    def test_cache_tampering_rejected(self):
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = self.row()
            body = json.dumps([self.result()])
            value = dict(endpoint=pilot.ENDPOINT, params=json.loads(row['params_json']), state='ok',
                response_body_utf8=body, response_sha256=hashlib.sha256(body.encode()).hexdigest(), results=[self.result()])
            path = pilot.cache_path(root, pilot.ENDPOINT, row['query_id'])
            pilot.save(path, value)
            self.assertEqual(pilot.cached(root, pilot.ENDPOINT, row)['state'], 'ok')
            value['results'][0]['lat'] = '0'
            pilot.save(path, value)
            with self.assertRaises(ValueError):
                pilot.cached(root, pilot.ENDPOINT, row)


if __name__ == '__main__':
    unittest.main()
