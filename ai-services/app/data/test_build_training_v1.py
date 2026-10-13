import unittest
import json
from build_training_v1 import group_records, split_for, extra_checks


class TrainingV1Tests(unittest.TestCase):
    def row(self,key,title,**updates):
        row=dict(record_key=key,title=title,category='Nhà ở',area_sqm='100',price_million='5000',
                 district='',raw_json='{}',transaction_verified='True',geographic_scope_status='accepted_address',
                 title_money_evidence='[]',date_basis='source_update_not_first_post')
        row.update(updates);return row

    def test_transitive_bridge_and_locations(self):
        title='Bán nhà đẹp đường lớn gần biển trung tâm thành phố'
        rows=[self.row('a',title),self.row('b',title,district='Hải Châu'),self.row('c','Một tin khác')]
        groups,_=group_records(rows,[dict(left='b',right='c',rule='prior',title_similarity='1')])
        self.assertEqual(len(set(groups.values())),1)
        self.assertEqual(len({split_for(g) for g in groups.values()}),1)

    def test_similar_titles_across_districts(self):
        a=self.row('a','Bán nhà đẹp đường lớn gần biển trung tâm thành phố giá tốt')
        b=self.row('b','Bán nhà đẹp đường lớn gần biển trung tâm thành phố giá rẻ',area_sqm='100.5')
        groups,pairs=group_records([a,b],[])
        self.assertEqual(groups['a'],groups['b'])
        self.assertTrue(pairs)

    def test_update_date_is_not_missing_date(self):
        row=self.row('a','Bán nhà',raw_json=json.dumps(dict(date_needs_review=True)))
        self.assertEqual(extra_checks(row),[])

    def test_multiple_properties_and_price_mismatch(self):
        row=self.row('a','Một số căn nhà cần bán',raw_json=json.dumps(dict(price_raw='2 tỷ')))
        self.assertIn('multiple_properties_in_title',extra_checks(row))
        self.assertIn('price_raw_not_confirmed_total',extra_checks(row))


if __name__=='__main__':unittest.main()
