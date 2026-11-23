import unittest
from battledim_importer import parse_wide_csv, compare_sensor_baselines, extract_reference_leak_events

class BattLeDIMImporterTests(unittest.TestCase):
    def test_wide_csv_to_long_records(self):
        raw=b'timestamp,N1,N2\n2018-01-01 00:00,10,20\n2018-01-01 00:05,11,21\n'
        result=parse_wide_csv(raw,'2018_SCADA_Pressures.csv','pressure','2018')
        self.assertEqual(result['sensor_count'],2)
        self.assertEqual(result['row_count'],2)
        self.assertEqual(len(result['records']),4)
        self.assertEqual(result['records'][0]['kind'],'pressure')

    def test_statistical_deviation_is_not_labelled_as_confirmed_leak(self):
        train=[{'kind':'pressure','sensor_id':'N1','value':v} for v in [10,11,9,10,11,9]]
        test=[{'kind':'pressure','sensor_id':'N1','timestamp':'2019-01-01 00:00','value':30}]
        out=compare_sensor_baselines(train,test)
        self.assertEqual(len(out),1)
        self.assertIn('not confirmed leak',out[0]['screening_flag'])

    def test_rejects_missing_numeric_observations(self):
        with self.assertRaises(ValueError):
            parse_wide_csv(b'timestamp,N1\n2018-01-01,abc\n','bad.csv','pressure','2018')



    def test_reference_leak_series_extracts_contiguous_periods(self):
        rows = [
            {'year':'2018','sensor_id':'p1','timestamp':'2018-01-01 00:00:00','value':0.0},
            {'year':'2018','sensor_id':'p1','timestamp':'2018-01-01 00:05:00','value':1.0},
            {'year':'2018','sensor_id':'p1','timestamp':'2018-01-01 00:10:00','value':2.0},
            {'year':'2018','sensor_id':'p1','timestamp':'2018-01-01 00:15:00','value':0.0},
            {'year':'2018','sensor_id':'p1','timestamp':'2018-01-01 00:20:00','value':3.0},
        ]
        events = extract_reference_leak_events(rows)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]['active_samples'], 2)
        self.assertEqual(events[0]['peak_leak_outflow_m3_h'], 2.0)
        self.assertEqual(events[0]['approx_leak_volume_m3'], 0.25)
        self.assertEqual(events[1]['start'], '2018-01-01 00:20:00')

    def test_battledim_semicolon_decimal_comma_format(self):
        raw = b'Timestamp;n1;n4\n2018-01-01 00:00:00;28,92;33,87\n'
        result = parse_wide_csv(raw, '2018_SCADA_Pressures.csv', 'pressure', '2018')
        self.assertEqual(result['sensor_count'], 2)
        self.assertEqual(result['records'][0]['value'], 28.92)
        self.assertEqual(result['records'][1]['value'], 33.87)

if __name__=='__main__': unittest.main()
