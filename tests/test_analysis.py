"""Synthetic-only regression cases; never reads a personal export."""
import io
from pathlib import Path
import sys
import tempfile
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from analyze import (Q, SafeReader, aggregate_metric, analyze, parse_time,
                     select_source, sleep_metrics, split_days, union_intervals)
from make_demo import make_xml


class AnalysisTests(unittest.TestCase):
    def test_union_does_not_double_count(self):
        a = parse_time('2024-01-01T00:00:00+00:00')
        b = parse_time('2024-01-01T01:00:00+00:00')
        c = parse_time('2024-01-01T02:00:00+00:00')
        self.assertEqual(union_intervals([(a,b),(a,c),(b,c)]), [[a,c]])

    def test_midnight_split_preserves_total(self):
        a = parse_time('2024-01-01T23:30:00+00:00')
        b = parse_time('2024-01-02T00:30:00+00:00')
        self.assertEqual(list(split_days(a,b,100)), [('2024-01-01',50),('2024-01-02',50)])

    def test_dst_elapsed_time(self):
        tz = ZoneInfo('America/New_York')
        a = parse_time('2024-03-10T00:00:00-05:00', tz)
        b = parse_time('2024-03-11T01:00:00-04:00', tz)
        values = list(split_days(a,b,240))
        self.assertAlmostEqual(values[0][1],230)
        self.assertAlmostEqual(values[1][1],10)

    def test_source_does_not_sum_phone_and_watch(self):
        a = parse_time('2024-01-01T00:00:00+00:00')
        groups = {'Synthetic Phone': [(a,a,9000)], 'Synthetic Watch': [(a,a,5000)]}
        source = select_source(groups, {'Synthetic Phone':'Phone','Synthetic Watch':'Watch'})
        self.assertEqual(source, 'Synthetic Watch')
        m = aggregate_metric(Q+'StepCount',groups[source],'Watch 1')
        self.assertEqual(m['rows'][0]['value'],5000)

    def test_sleep_excludes_inbed_and_overlap(self):
        a = parse_time('2024-01-01T00:00:00+00:00')
        b = parse_time('2024-01-01T07:00:00+00:00')
        c = parse_time('2024-01-01T09:00:00+00:00')
        rows = [(a,b,'HKCategoryValueSleepAnalysisAsleepCore'),
                (a,b,'HKCategoryValueSleepAnalysisAsleepREM'),
                (a,c,'HKCategoryValueSleepAnalysisInBed')]
        metrics,_ = sleep_metrics(rows,'Watch 1')
        self.assertEqual(metrics[0]['rows'][0]['value'],7)

    def test_entities_and_size_limit(self):
        with self.assertRaises(ValueError):
            SafeReader(io.BytesIO(b'<!ENTITY bomb "bad">'),100).read()
        with self.assertRaises(ValueError):
            SafeReader(io.BytesIO(b'123456'),4).read()

    def test_fictional_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'export.xml'
            path.write_text(make_xml(),encoding='utf-8')
            d = analyze(path,'UTC')
        by_id = {m['id']:m for m in d['metrics']}
        self.assertEqual(len(by_id['sleep']['rows']),57)
        self.assertEqual(d['workouts']['count'],1)
        self.assertEqual(d['meta']['invalid'],0)
        self.assertTrue(any(r['value']==89 for r in by_id['spo2_min']['rows']))
        self.assertFalse(any(r['date']=='2024-01-14' for r in by_id['steps']['rows']))
        self.assertNotIn('Synthetic Watch',str(d))

    def test_oxygen_unit_not_guessed(self):
        xml = '''<HealthData><Record type="HKQuantityTypeIdentifierOxygenSaturation"
        sourceName="Synthetic Watch" unit="%" value="97"
        startDate="2024-01-01T00:00:00+00:00" endDate="2024-01-01T00:00:00+00:00"/></HealthData>'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'export.xml'
            path.write_text(xml)
            d = analyze(path,'UTC')
        self.assertEqual(d['meta']['invalid'],1)
        self.assertEqual(d['metrics'],[])


if __name__ == '__main__':
    unittest.main()
