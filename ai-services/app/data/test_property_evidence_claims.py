import hashlib
import unittest
from property_evidence_claims import extract, APARTMENT


def source(text, kind='verified_detail_body'):
    return dict(text=text, kind=kind, sha256=hashlib.sha256(text.encode()).hexdigest())


class PropertyClaimTests(unittest.TestCase):
    def test_nearby_relation_after_attribute_does_not_describe_property_access(self):
        values, _ = extract('Nhà ở', [source('Kiệt ô tô cách nhà 50m, nhà nằm trong kiệt đi bộ.')])
        self.assertEqual(values['car_access_claim'], '')
        values, _ = extract('Nhà ở', [source('Kiệt rộng 3m ở gần nhà.')])
        self.assertEqual(values['alley_width_m_claim'], '')

    def test_postfix_negation_and_pending_certificate_are_not_positive_claims(self):
        for text in ['Sổ hồng chưa có.', 'Sổ hồng đang chờ cấp.']:
            values, _ = extract('Nhà ở', [source(text)])
            self.assertEqual(values['legal_document_claim'], 'certificate_not_available_claimed')
        values, _ = extract('Nhà ở', [source('Nội thất cơ bản chưa có.')])
        self.assertEqual(values['interior_claim'], '')

    def test_word_ranges_or_alternatives_do_not_become_exact_width(self):
        for text in ['Kiệt rộng 3m đến 5m.', 'Kiệt rộng 3m hoặc 5m.']:
            values, _ = extract('Nhà ở', [source(text)])
            self.assertEqual(values['alley_width_m_claim'], '')

    def test_alley_width_is_not_land_width_or_distance(self):
        good, proof = extract('Nhà ở', [source('Nhà kiệt rộng 3,5m, ngang đất 5m.')])
        self.assertEqual(good['alley_width_m_claim'], 3.5)
        self.assertEqual(proof[0]['source_quote'], 'Nhà kiệt rộng 3,5m')
        for text in ['Ngang đất 5m, mặt tiền 6m.', 'Nhà cách kiệt 5m.', 'Đường 7m gần nhà.', 'Kiệt 3m–5m.', 'Kiệt 3-4m.', 'Kiệt 3m trở lên.']:
            with self.subTest(text=text):
                values, _ = extract('Nhà ở', [source(text)])
                self.assertEqual(values['alley_width_m_claim'], '')

    def test_car_access_is_a_literal_claim_not_nearby_or_garage(self):
        for text in ['Nhà kiệt ô tô.', 'Ô tô vào tận nhà.']:
            values, _ = extract('Nhà ở', [source(text)])
            self.assertEqual(values['car_access_claim'], 'yes')
        for text in ['Nhà gần kiệt ô tô.', 'Cách hẻm ô tô 50m.', 'Nhà có gara ô tô.']:
            values, _ = extract('Nhà ở', [source(text)])
            self.assertEqual(values['car_access_claim'], '')
        values, _ = extract('Nhà ở', [source('Ô tô không vào được.')])
        self.assertEqual(values['car_access_claim'], 'no')

    def test_unit_floor_is_not_building_storeys_room_id_or_range(self):
        values, _ = extract(APARTMENT, [source('Căn hộ tầng 12, tòa nhà 30 tầng.')])
        self.assertEqual(values['apartment_floor_claim'], 12)
        for text in ['Tòa nhà 30 tầng.', 'Quy mô tầng 30.', 'Căn 1205.', 'Căn hộ tầng 12–13.']:
            values, _ = extract(APARTMENT, [source(text)])
            self.assertEqual(values['apartment_floor_claim'], '')
        values, _ = extract('Nhà ở', [source('Nhà tầng 3.')])
        self.assertEqual(values['apartment_floor_claim'], '')
        values, _ = extract(APARTMENT, [source('Không phải tầng 10.')])
        self.assertEqual(values['apartment_floor_claim'], '')

    def test_future_and_nearby_claims_are_missing(self):
        for text in ['Dự kiến bàn giao năm 2026.', 'Sẽ bàn giao 2026.', 'Đã bàn giao 2027.', 'Gần chung cư bàn giao năm 2020.']:
            values, _ = extract(APARTMENT, [source(text)])
            self.assertEqual(values['handover_year_claim'], '')
        values, _ = extract(APARTMENT, [source('Đã bàn giao năm 2020.')])
        self.assertEqual(values['handover_year_claim'], 2020)
        values, _ = extract(APARTMENT, [source('Đã bàn giao năm 2020.')], observed_year=None)
        self.assertEqual(values['handover_year_claim'], '')

    def test_conflicting_title_and_body_remain_missing_with_both_quotes(self):
        values, proof = extract(APARTMENT, [source('Căn hộ tầng 10.', 'collected_title'), source('Căn hộ tầng 12.')])
        self.assertEqual(values['apartment_floor_claim'], '')
        self.assertIn('apartment_floor_claim', values['conflict_fields'])
        self.assertEqual({p['status'] for p in proof}, {'conflict_keep_missing'})

    def test_interior_claim_does_not_infer_completeness_from_quality_or_gift(self):
        for text in ['Nội thất cao cấp.', 'Tặng nội thất.']:
            values, _ = extract('Nhà ở', [source(text)])
            self.assertEqual(values['interior_claim'], '')
        values, _ = extract('Nhà ở', [source('Nhà full nội thất cao cấp.')])
        self.assertEqual(values['interior_claim'], 'full')
        values, _ = extract(APARTMENT, [source('Chưa có nội thất.')])
        self.assertEqual(values['interior_claim'], 'empty')

    def test_legal_claim_is_not_proof_and_structured_conflict_stays_missing(self):
        values, _ = extract('Nhà ở', [source('Sổ hồng riêng', 'structured_legal_status')])
        self.assertEqual(values['legal_document_claim'], 'certificate_claimed')
        values, proof = extract('Nhà ở', [source('Sổ hồng riêng', 'structured_legal_status'), source('Đang chờ cấp sổ hồng.')])
        self.assertEqual(values['legal_document_claim'], '')
        self.assertIn('legal_document_claim', values['conflict_fields'])
        self.assertTrue(all(p['source_sha256'] for p in proof))

    def test_names_always_require_identity_review(self):
        values, proof = extract(APARTMENT, [source('Dự án: Example Residence; Block A, tầng 10.')])
        self.assertNotIn('project_name', values)
        names = [p for p in proof if p['field'] in ['project_name', 'building_name']]
        self.assertEqual({p['status'] for p in names}, {'needs_name_review'})
        self.assertEqual({p['value'] for p in names}, {'Example Residence', 'A'})

    def test_inventory_and_broker_footer_not_used_as_property_features(self):
        values, proof = extract(APARTMENT, [source('Giỏ hàng căn hộ tầng 10, full nội thất.')])
        self.assertEqual(values['apartment_floor_claim'], '')
        self.assertEqual(values['interior_claim'], '')
        values, proof = extract('Nhà ở', [source('Nhà đẹp. Liên hệ môi giới nhà kiệt ô tô 5m.')])
        self.assertEqual(values['car_access_claim'], '')
        self.assertEqual(values['alley_width_m_claim'], '')


if __name__ == '__main__':
    unittest.main()
