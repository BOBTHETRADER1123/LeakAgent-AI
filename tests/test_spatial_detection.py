import unittest
from spatial_detection import analyze_spatial_rows

class SpatialDetectionTests(unittest.TestCase):
    def rows(self):
        out=[]
        for cycle in ('C1','C2'):
            for station,dist,flow in [('S0',0,100),('S1',1000,100),('S2',2000,90),('S3',3000,90)]:
                out.append({'pipe_id':'P1','cycle_id':cycle,'timestamp':cycle+'T09:00:00',
                    'station_id':station,'distance_m':dist,'flow_l_s':flow,'meter_sigma_l_s':0.5,
                    'known_withdrawal_l_s':0,'full_pipe_flag':'true','stable_window_verified':'true'})
        return out

    def test_repeated_anomaly_brackets_interval(self):
        r=analyze_spatial_rows(self.rows(),3000)
        flagged=[x for x in r['location_summary'] if x['flagged_cycles']>=2]
        self.assertEqual(len(flagged),1)
        self.assertEqual((flagged[0]['start_m'],flagged[0]['end_m']),(1000,2000))
        self.assertEqual(flagged[0]['actual_localization_resolution_m'],1000)

    def test_mm_coordinate_reference_does_not_claim_mm_accuracy(self):
        r=analyze_spatial_rows(self.rows(),3000)
        self.assertEqual(r['location_summary'][0]['start_mm'],0)
        self.assertIn('not proof',r['location_summary'][0]['millimetre_coordinate_reference'])

    def test_missing_columns_rejected(self):
        with self.assertRaises(ValueError):
            analyze_spatial_rows([{'pipe_id':'P'}])

if __name__=='__main__': unittest.main()
