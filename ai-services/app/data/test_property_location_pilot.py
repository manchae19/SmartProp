import unittest
import review_property_location_pilot as review


class PropertyLocationTests(unittest.TestCase):
    def test_alley_match_never_verifies_a_house(self):
        row=dict(search_street='Kiệt 196 Âu Cơ',clue_kind='alley_identifier')
        result=dict(lat='16.1',lon='108.15',display_name='Kiệt 196 Âu Cơ, Đà Nẵng, Việt Nam',
            address={'road':'Kiệt 196 Âu Cơ','country_code':'vn','house_number':'123'})
        actual=review.classification(row,result)
        self.assertEqual(actual['precision'],'alley_reference')
        for field in ['location_verified','exact_house_number_verified','model_feature_approved','reuse_for_ml_verified']:
            self.assertFalse(actual[field])

    def test_same_name_hoi_an_outside_envelope_remains_unresolved(self):
        row=dict(search_street='Âu Cơ',clue_kind='frontage_claim')
        result=dict(lat='15.8884162',lon='108.3797484',display_name='Âu Cơ, Hội An, Đà Nẵng, Việt Nam',
            address={'road':'Âu Cơ','country_code':'vn'})
        self.assertEqual(review.classification(row,result)['precision'],'unresolved_candidate')

    def test_narrower_lookup_uses_alley_identifier_not_width(self):
        clues={r[0]:r for r in review.CLUES}
        self.assertEqual(clues['135139247'][4],'Kiệt 196 Âu Cơ')
        for sid in ['135149346','135170423','135092070','135136720','134126599','135164017']:
            self.assertEqual(clues[sid][4],'')

    def test_title_spelling_not_rewritten_as_verified_address(self):
        clue={r[0]:r for r in review.CLUES}['134925160']
        self.assertIn('Trường Chính',clue[2])
        self.assertIn('Trường Chinh',clue[4])
        self.assertEqual(len({r[0] for r in review.CLUES}),20)


if __name__=='__main__':
    unittest.main()
