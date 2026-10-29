import hashlib
import json
import unittest

import source_asset_features as feature


class SourceFeaturesTests(unittest.TestCase):
    def sources(self, text):
        return [dict(kind='original_collected_title', text=text, sha256=hashlib.sha256(text.encode()).hexdigest())]

    def test_streets_preserve_source_only_and_refuse_nearby_or_multiple(self):
        self.assertEqual(feature.street_claim('  Đường  Võ Văn Kiệt  ')[0], 'vo van kiet')
        self.assertEqual(feature.street_claim('Đường 2/9')[0], '2/9')
        self.assertEqual(feature.street_claim('Đường Cách Mạng Tháng Tám')[0], 'cach mang thang tam')
        for raw in ['Gần đường Võ Văn Kiệt', 'Đường A, đường B', 'Kiệt 4m', 'Chưa rõ', '',
                    'Le Duan 3 ty', 'Ha Huy Tap 0901234567', 'Le Duan lien he 0901234567',
                    '[Le Duan]', 'Le <Duan>']:
            self.assertFalse(feature.street_claim(raw)[0])

    def test_width_land_area_conflicts_and_street_name_do_not_become_alley(self):
        v, p = feature.extract_claims('Đất nền', self.sources('Đất thổ cư 80m2; đất ngang 5m; kiệt 3.5m'), 100)
        self.assertEqual(v['residential_area_sqm_claim'], 80)
        self.assertEqual(v['parcel_width_m_claim'], 5)
        self.assertEqual(v['alley_width_m_claim'], 3.5)
        v, p = feature.extract_claims('Nhà ở', self.sources('Nhà Võ Văn Kiệt 6m'), 100)
        self.assertEqual(v['alley_width_m_claim'], '')
        v, p = feature.extract_claims('Đất nền', self.sources('Đất thổ cư 80m2; đất thổ cư 90m2; gần đất ngang 5m'), 100)
        self.assertEqual(v['residential_area_sqm_claim'], '')
        self.assertEqual(v['parcel_width_m_claim'], '')
        self.assertTrue(any(r['status']=='conflict_keep_missing' for r in p))
        for text in ['Đất ngang 5m hoặc 7m', 'Đất ở 50m2 hoặc 70m2', 'Lô đất 100m2 đường đất rộng 6m',
                     'Lô đất 100m2 đường đất ngang 6m', 'Lô đất 100m2 đường đất có chiều ngang 6m']:
            v, _ = feature.extract_claims('Đất nền', self.sources(text), 100)
            self.assertEqual(v['residential_area_sqm_claim'], '')
            self.assertEqual(v['parcel_width_m_claim'], '')

    def test_original_join_never_reads_later_description_or_price_text_as_x(self):
        row = dict(category='Nhà ở', area_sqm=100)
        raw = json.dumps(dict(title='Nhà kiệt 3m', street='Đường Hà Huy Tập', description='kiệt 9m', price_raw='3 tỷ'))
        origin = dict(title='Nhà kiệt 3m', raw_json=raw, description='kiệt 8m')
        v, p = feature.original_features(row, origin)
        self.assertEqual(v['alley_width_m_claim'], 3)
        self.assertNotIn('price_raw', v)
        self.assertTrue(all(r['source_kind'] != 'description' for r in p))

    def test_street_vocabulary_is_fit_only_and_unknown_preserves_width(self):
        fit = [dict(record_key=str(i), location_feature='Sơn Trà', ward_source='', rooms='', category='Nhà ở', area_sqm=100) for i in range(3)]
        held = dict(fit[0], record_key='held')
        base = {r['record_key']: dict(rooms_completed='', floors_claim='', access_claim='', house_subtype_claim='') for r in [*fit, held]}
        extras = {r['record_key']: dict.fromkeys(feature.FIELDS, '') for r in [*fit, held]}
        for r in fit: extras[r['record_key']]['street_key']='ha huy tap'
        extras['held']['street_key']='held only'
        spec = feature.feature_spec(fit, base, extras, 'Nhà ở', 'source_enriched')
        self.assertEqual(spec['streets'], ['Sơn Trà|ha huy tap'])
        matrix = feature.encode([held], base, extras, spec)
        self.assertEqual(matrix.shape[1], len(spec['feature_names']))
        self.assertEqual(matrix[0,spec['feature_names'].index('street_unseen_or_rare')], 1)


if __name__=='__main__': unittest.main()
