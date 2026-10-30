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
from cross import robust_z, sleep_regularity


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

    def test_baseline_ignores_recent_days_and_needs_history(self):
        series = {f'2024-01-{d:02d}': 60.0 + (d % 3) * .5 for d in range(1, 21)}
        series['2024-01-21'] = 70.0
        z = robust_z(series, 1.5, 1)
        self.assertNotIn('2024-01-10', z)          # fewer than 14 baseline days
        self.assertTrue(z['2024-01-21']['flag'])
        self.assertFalse(z['2024-01-20']['flag'])
        # A drop is not flagged when only increases are of interest.
        series['2024-01-21'] = 50.0
        self.assertFalse(robust_z(series, 1.5, 1)['2024-01-21']['flag'])

    def test_sleep_regularity_identical_and_shifted(self):
        nights, spans = [], []
        for d, shift in ((1, 0), (2, 0), (3, 3)):
            bed = parse_time(f'2024-01-{d:02d}T{1+shift:02d}:00:00+00:00')
            wake = parse_time(f'2024-01-{d:02d}T{8+shift:02d}:00:00+00:00')
            nights.append({'date': bed.date().isoformat(), 'bedtime': bed.isoformat(), 'wake': wake.isoformat()})
            spans.append((bed, wake))
        sri = {r['date']: r['value'] for r in sleep_regularity(nights, spans)}
        self.assertEqual(sri['2024-01-02'], 100)
        # 3 h later: 3 h asleep-vs-awake mismatch at each end, 6 h of 24 in total.
        self.assertAlmostEqual(sri['2024-01-03'], 200 * (1 - 6/24) - 100)

    def test_cross_signals_in_fictional_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'export.xml'
            path.write_text(make_xml(), encoding='utf-8')
            d = analyze(path, 'UTC')
        cross = d['cross']
        self.assertEqual([(e['start'], e['end']) for e in cross['episodes']], [('2024-02-10', '2024-02-12')])
        self.assertFalse(any(x['count'] >= 2 for x in cross['days'] if x['date'] < '2024-02-10'))
        joint = [n['date'] for n in cross['nights'] if n['flags'] >= 2]
        self.assertEqual(joint, ['2024-01-23'])
        ids = {m['id'] for m in d['metrics']}
        self.assertTrue({'spo2_sleep_min', 'respiratory_sleep', 'sleep_midpoint', 'sri', 'wear_hours'} <= ids)
        self.assertNotIn('Synthetic Watch', str(d))

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
