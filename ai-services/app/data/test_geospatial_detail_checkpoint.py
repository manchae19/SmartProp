import unittest

from finalize_geospatial_detail_attempt import checkpoint


class DetailCheckpointTests(unittest.TestCase):
    def queue(self):
        return [dict(record_key='chotot:'+str(i),source='chotot',
            detail_url=f'https://nha.chotot.com/{i}.htm',v3_cohort='train',
            pipeline_group='group:'+str(i),priority='1' if i<30 else '2') for i in range(80)]

    def test_one_block_does_not_become_eighty_http_failures(self):
        queue = self.queue()
        probes = {'chotot:0':dict(requested_url=queue[0]['detail_url'],state='blocked',http_status=403)}
        rows = checkpoint(queue,probes)
        self.assertEqual(sum(r['individually_requested'] for r in rows),1)
        self.assertEqual(sum(r['http_status']==403 for r in rows),1)
        self.assertEqual(sum(r['state']=='not_requested_source_access_blocked' for r in rows),79)
        self.assertTrue(all(r['http_status']=='' for r in rows[1:]))
        self.assertTrue(all(not r['source_identity_verified'] and not r['detail_description_available'] for r in rows))

    def test_available_or_missing_ad_does_not_mark_other_ads_blocked(self):
        queue = self.queue()
        for code,state in [(200,'downloaded_not_identity_verified'),(404,'unavailable')]:
            rows = checkpoint(queue,{'chotot:0':dict(requested_url=queue[0]['detail_url'],state=state,http_status=code)})
            self.assertEqual(rows[1]['state'],'not_requested_pending')
            self.assertFalse(rows[0]['source_identity_verified'])

    def test_repeated_ids_wrong_url_or_unknown_probe_rejected(self):
        queue = self.queue()
        with self.assertRaises(ValueError):
            checkpoint(queue,{'chotot:0':dict(requested_url='https://nha.chotot.com/1.htm',state='blocked',http_status=403)})
        with self.assertRaises(ValueError):
            checkpoint(queue,{'chotot:100':dict(requested_url='https://nha.chotot.com/100.htm',state='blocked',http_status=403)})
        queue[-1] = queue[0]
        with self.assertRaises(ValueError):
            checkpoint(queue,{})


if __name__=='__main__':
    unittest.main()
