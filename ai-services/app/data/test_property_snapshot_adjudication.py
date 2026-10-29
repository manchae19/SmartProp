import copy
import hashlib
import unittest

import property_snapshot_adjudication as rules


def row(key='new:1', **changes):
    result=dict(record_key=key,description='Căn hộ. Diện tích: 55m². Giá bán: 2.500.000.000 VND.',
        title='Bán căn hộ 2PN',price_million=2500.,area_sqm=55.,rooms=2,
        review_codes=[rules.CORROBORATION],exclusion_codes=[],group_review_codes=['current_group_contains_unresolved_member'],
        overlay_group='g:'+key,location_feature='Sơn Trà',candidate_role='needs_source_review')
    result.update(changes)
    return result


class SourceAdjudicationTests(unittest.TestCase):
    def test_full_vnd_total_resolves_only_missing_corroboration(self):
        source=row(review_codes=[rules.CORROBORATION,'source_date_outside_pilot_window'])
        saved=copy.deepcopy(source);result=rules.scan(source)
        self.assertNotIn(rules.CORROBORATION,result['remaining_codes'])
        self.assertIn('source_date_outside_pilot_window',result['remaining_codes'])
        self.assertEqual(source,saved)
        self.assertEqual(result['resolved_codes_v2'][0]['code'],rules.CORROBORATION)

    def test_metadata_echo_does_not_prove_seller_price(self):
        result=rules.scan(row(description='Thông tin mô tả Bán căn hộ chung cư Sơn Trà, Đà Nẵng Căn hộ đẹp, diện tích: 55m². Giá : 2.500.000.000 VND Diện tích: 55.00 m2'))
        self.assertIn(rules.CORROBORATION,result['remaining_codes'])

    def test_price_after_contact_is_kept_with_exact_quote(self):
        result=rules.scan(row(description='Căn hộ. Diện tích: 55m². Liên hệ tư vấn. Giá bán: 2.500.000.000 VND.'))
        self.assertNotIn(rules.CORROBORATION,result['remaining_codes'])
        self.assertTrue(any(p['source_quote']=='2.500.000.000 VND' for p in result['source_proofs']))

    def test_unit_rental_and_funding_amounts_are_not_totals(self):
        for text in ['Giá thuê: 2.500.000.000 VND.', 'Giá bán: 2.500.000.000 VND/m².',
                     'Trả trước: 2.500.000.000 VND.', 'Giá từ 2.500.000.000 VND.']:
            with self.subTest(text=text):
                result=rules.scan(row(description='Căn hộ. Diện tích: 55m². '+text))
                self.assertIn(rules.CORROBORATION,result['remaining_codes'])

    def test_unrelated_park_area_never_proves_property_area(self):
        result=rules.scan(row(description='Căn hộ gần công viên diện tích: 55m². Giá bán: 2.500.000.000 VND.'))
        self.assertIn(rules.CORROBORATION,result['remaining_codes'])

    def test_wrong_or_multiple_total_keeps_unresolved(self):
        for text in ['Giá bán: 2.800.000.000 VND.', 'Giá bán: 2.500.000.000 VND. Giá bán: 2.800.000.000 VND.']:
            result=rules.scan(row(description='Căn hộ. Diện tích: 55m². '+text))
            self.assertIn(rules.CORROBORATION,result['remaining_codes'])

    def test_inventory_after_contact_excludes_previous_candidate(self):
        result=rules.scan(row(review_codes=[],description='Căn hộ diện tích 55m² giá 2,5 tỷ. Liên hệ 0900000000. Ngoài ra tôi còn giỏ hàng 5 căn khác.'))
        self.assertEqual(result['source_decision'],'exclude_single_apartment_dataset')
        self.assertIn('multiple_units_in_full_seller_text',result['remaining_codes'])

    def test_project_inventory_count_alone_does_not_exclude(self):
        result=rules.scan(row(review_codes=[],description='Căn hộ 55m², 2PN. Tổng dự án gồm 202 căn hộ.'))
        self.assertEqual(result['exclusions_v2'],[])

    def test_negated_inventory_is_not_excluded(self):
        result=rules.scan(row(description='Không bán giỏ hàng. Căn hộ. Diện tích: 55m². Giá bán: 2.500.000.000 VND.'))
        self.assertEqual(result['exclusions_v2'],[])

    def test_project_heading_is_not_proof_whole_building_is_sold(self):
        result=rules.scan(row(exclusion_codes=['whole_building_not_single_apartment'],
            description='Tòa căn hộ Ecolife. Mã căn: G03.A16. Diện tích: 55m². Giá bán: 2.500.000.000 VND.'))
        self.assertEqual(result['exclusions_v2'],[])
        self.assertIn('whole_building_scope_not_resolved',result['remaining_codes'])
        self.assertEqual(result['source_decision'],'needs_evidence')

    def test_explicit_whole_building_sale_retains_exclusion(self):
        result=rules.scan(row(exclusion_codes=['whole_building_not_single_apartment'],
            description='Bán nguyên tòa căn hộ gồm 10 căn cho thuê.'))
        self.assertIn('whole_building_not_single_apartment',result['exclusions_v2'])

    def test_future_bedroom_is_not_current_but_header_conflict_stays(self):
        result=rules.scan(row(rooms=2,title='Bán căn hộ 1PN+',description='Căn hộ thiết kế 1PN+, có thể cải tạo thành 2PN linh hoạt.'))
        self.assertIn('bedroom_pn_br_header_conflict',result['remaining_codes'])
        self.assertTrue(any(p['status']=='hypothetical' and p['value']==2 for p in result['source_proofs']))

    def test_english_br_conflict_is_not_lost(self):
        result=rules.scan(row(title='Bán căn hộ 2BR+',rooms=1))
        self.assertIn('bedroom_pn_br_header_conflict',result['remaining_codes'])

    def test_title_unit_price_disagreement_is_review_not_relabel(self):
        result=rules.scan(row(title='Bán căn hộ 2PN đơn giá 20 triệu/m2',review_codes=[]))
        self.assertIn('title_unit_price_disagrees_with_total_area',result['remaining_codes'])
        self.assertEqual(result['price_million'],2500)

    def test_future_handover_detected_after_contact(self):
        result=rules.scan(row(description='Căn hộ. Liên hệ xem. Bàn giao dự kiến quý II 2026, chưa nhận nhà.',review_codes=[]))
        self.assertIn('handover_or_construction_status_needs_review',result['remaining_codes'])


class GroupAdjudicationTests(unittest.TestCase):
    def test_explicit_unit_code_links_same_project_and_area(self):
        a=row(description='Căn hộ The Meridian. Mã căn: M2-14-17. Diện tích: 55m2.')
        b=row('new:2',description='The Meridian. Căn M2-14-17, diện tích: 55m2.')
        links=rules.explicit_unit_links([a,b])
        self.assertEqual(len(links),1)
        self.assertEqual(links[0]['unit_code'],'m2-14-17')
        b['description']=b['description'].replace('The Meridian','Dự án khác')
        self.assertEqual(rules.explicit_unit_links([a,b]),[])

    def test_incomplete_masked_or_different_area_codes_do_not_link(self):
        for text,area in [('Mã căn: M2-XX-17',55),('Mã căn: M2-14',55),('Mã căn: M2-14-17',75)]:
            a=row(description='The Meridian. Mã căn: M2-14-17.')
            b=row('new:2',description='The Meridian. '+text,area_sqm=area)
            self.assertEqual(rules.explicit_unit_links([a,b]),[])

    def test_group_dedup_reserves_one_fresh_member(self):
        rows=[rules.scan(row(k)) for k in ['new:1','new:2']]
        links=[dict(left='new:1',right='new:2')]
        results=rules.adjudicate_groups(rows,links,set(),set())
        self.assertEqual([r['dataset_role'] for r in results],['fresh_evaluation_reserved','suppressed_duplicate'])
        self.assertFalse(any(r['training_allowed'] for r in results))

    def test_protected_noncurrent_bridge_blocks_entire_merge(self):
        a=rules.scan(row(group_review_codes=['linked_to_protected_or_prior_batch']))
        b=rules.scan(row('new:2'))
        results=rules.adjudicate_groups([a,b],[dict(left='new:1',right='new:2')],set(),set())
        self.assertTrue(all(r['dataset_role']=='quarantine' for r in results))

    def test_historical_component_without_current_historical_id_is_not_fresh(self):
        a=rules.scan(row())
        result=rules.adjudicate_groups([a],[],set(),{'old:1'},{a['overlay_group']})[0]
        self.assertEqual(result['dataset_role'],'historical_linked_candidate')

    def test_unresolved_member_blocks_good_member(self):
        a=rules.scan(row());b=rules.scan(row('new:2',review_codes=['masked_price_requires_review']))
        result=rules.adjudicate_groups([a,b],[dict(left='new:1',right='new:2')],set(),set())
        self.assertTrue(all(r['dataset_role']=='quarantine' for r in result))

    def test_price_conflict_on_new_link_blocks_group(self):
        a=rules.scan(row(review_codes=[]));b=rules.scan(row('new:2',price_million=5000,review_codes=[]))
        result=rules.adjudicate_groups([a,b],[dict(left='new:1',right='new:2')],set(),set())
        self.assertTrue(all('current_group_price_million_conflict' in r['group_codes_v2'] for r in result))

    def test_complete_graph_retains_bridge_and_is_order_independent(self):
        keys={'old:1','old:2','new:1'}
        links=[dict(left='old:1',right='old:2'),dict(left='old:2',right='new:1')]
        expected='property_candidate:'+hashlib.sha256('|'.join(sorted(keys)).encode()).hexdigest()[:20]
        self.assertEqual(rules.component_members(keys,links),{expected:keys})
        self.assertEqual(rules.component_members(keys,list(reversed(links))),{expected:keys})
        with self.assertRaisesRegex(ValueError,'Unknown graph endpoint'):
            rules.component_members({'old:1'},links)


if __name__=='__main__':unittest.main()
