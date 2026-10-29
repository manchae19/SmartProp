import unittest
from verify_property_expansion import edge_multiset


class UndirectedReplayTests(unittest.TestCase):
    def test_order_and_direction_are_not_semantic_changes(self):
        edges=[dict(left='a',right='b',rule='same_body',title_similarity=.99),
               dict(left='b',right='c',rule='same_title',title_similarity=1.0)]
        reversed_edges=[dict(e,left=e['right'],right=e['left']) for e in reversed(edges)]
        self.assertEqual(edge_multiset(edges),edge_multiset(reversed_edges))

    def test_edge_multiplicity_rules_and_scores_are_preserved(self):
        edge=dict(left='a',right='b',rule='same_body',title_similarity=.99)
        original=edge_multiset([edge])
        self.assertNotEqual(original,edge_multiset([edge,edge]))
        self.assertNotEqual(original,edge_multiset([dict(edge,rule='different')]))
        self.assertNotEqual(original,edge_multiset([dict(edge,title_similarity=.5)]))


if __name__=='__main__':unittest.main()
