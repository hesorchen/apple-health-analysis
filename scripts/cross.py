"""Cross-signal observations built only from the default-source records.

Every comparison is against the same person's own recent baseline. No age, sex
or population cut-off is used, and nothing here is a diagnosis: the output says
which signals moved together on which days, plus the caveats needed to read it.
Python 3.10+, standard library only.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import defaultdict
from datetime import date, datetime, time, timedelta
import statistics as stats

# Baseline: the 28 days ending 2 days before the day being judged, so a
# multi-day change is not absorbed into its own baseline at once.
BASE_DAYS, BASE_GAP, BASE_MIN, Z = 28, 2, 14, 2.0
# Smallest robust spread per signal, so a very flat baseline cannot turn
# ordinary measurement noise into a flag.
FLOOR = {'resting_hr': 1.5, 'hrv': 4.0, 'respiratory': 0.4, 'wrist_temp': 0.15,
         'sleep': 0.33, 'breathing': 1.0}
# id, label, direction that is flagged (+1 above baseline, -1 below, 0 either way)
SIGNALS = [('resting_hr', '静息心率', 1), ('hrv', '心率变异性', -1),
           ('respiratory', '睡眠呼吸频率', 1), ('wrist_temp', '睡眠腕温', 1),
           ('sleep', '主睡眠时长', 0)]
LOW_SPO2 = 90
GAIT_SPEED_MEANINGFUL = 0.36  # km/h = 0.1 m/s
TREND = [  # id, label, direction researchers watch for decline (+1: lower is the change of interest)
    ('vo2', '心肺适能估算', 1), ('walking_hr', '步行平均心率', -1), ('walking_speed', '步行速度', 1),
    ('step_length', '步行步长', 1), ('double_support', '步行双支撑比例', -1),
    ('walking_asymmetry', '步行不对称比例', -1), ('walking_steadiness', '步行稳定性估算', 1),
    ('six_min_walk', '六分钟步行距离估算', 1)]


def robust_z(series, floor, direction):
    """series: {iso date: value}. Returns {iso date: {value, baseline, z, flag}}."""
    days = sorted(series)
    keys = [date.fromisoformat(d) for d in days]
    out = {}
    for i, day in enumerate(keys):
        lo = bisect_left(keys, day - timedelta(days=BASE_DAYS + BASE_GAP))
        hi = bisect_left(keys, day - timedelta(days=BASE_GAP))
        ref = [series[days[j]] for j in range(lo, hi)]
        if len(ref) < BASE_MIN:
            continue
        med = stats.median(ref)
        scale = max(1.4826 * stats.median(abs(v - med) for v in ref), floor)
        value = series[days[i]]
        z = (value - med) / scale
        flag = abs(z) >= Z if direction == 0 else z * direction >= Z
        out[days[i]] = {'value': round(value, 3), 'baseline': round(med, 3), 'z': round(z, 2), 'flag': flag}
    return out


class Samples:
    """Raw (start, end, value) samples indexed by start time for window lookups."""
    def __init__(self, rows):
        self.rows = sorted(rows or [], key=lambda r: r[0])
        self.starts = [r[0].timestamp() for r in self.rows]

    def between(self, a, b):
        i, j = bisect_left(self.starts, a.timestamp()), bisect_right(self.starts, b.timestamp())
        return [self.rows[k][2] for k in range(i, j)]


def clock_hours(moment):
    """Local clock time as hours, with evening shown as negative (23:30 -> -0.5)."""
    h = moment.hour + moment.minute / 60 + moment.second / 3600
    return h - 24 if h >= 18 else h


def overlap(a, b):
    """Total overlap in seconds between two sorted, non-overlapping interval lists."""
    i = j = 0
    total = 0.0
    while i < len(a) and j < len(b):
        lo, hi = max(a[i][0], b[j][0]), min(a[i][1], b[j][1])
        if hi > lo:
            total += hi - lo
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return total


def sleep_regularity(nights, intervals):
    """Approximate Sleep Regularity Index per wake date.

    SRI = 200 x P(same asleep/awake state 24 h apart) - 100, compared over two
    consecutive noon-to-noon windows that both contain a main sleep. Only main
    sleep is counted (naps count as awake), so this is an approximation.
    """
    spans = sorted((s.timestamp(), e.timestamp()) for s, e in intervals)
    starts = [s for s, _ in spans]
    by_date = {n['date']: n for n in nights}

    def asleep(window_start):
        lo, hi = window_start, window_start + 86400
        k = max(0, bisect_left(starts, lo) - 1)
        out = []
        while k < len(spans) and spans[k][0] < hi:
            a, b = max(spans[k][0], lo), min(spans[k][1], hi)
            if b > a:
                out.append((a - lo, b - lo))
            k += 1
        return out

    rows = []
    for day in sorted(by_date):
        prev = (date.fromisoformat(day) - timedelta(days=1)).isoformat()
        if prev not in by_date:
            continue
        tz = datetime.fromisoformat(by_date[day]['wake']).tzinfo
        noon = datetime.combine(date.fromisoformat(prev) - timedelta(days=1), time(12), tz).timestamp()
        a, b = asleep(noon), asleep(noon + 86400)
        differ = sum(y - x for x, y in a) + sum(y - x for x, y in b) - 2 * overlap(a, b)
        rows.append({'date': day, 'value': round(200 * (1 - differ / 86400) - 100, 2)})
    return rows


def window(rows, lo, hi):
    return [r['value'] for r in rows if lo <= r['date'] <= hi]


def build_cross(by_id, selected, sleep_rows, sleep_intervals, end_date):
    """Return (cross summary, derived daily metrics) for the default sources."""
    spo2, resp = Samples(selected.get('spo2')), Samples(selected.get('respiratory'))
    breathing, temp = Samples(selected.get('breathing_disturbances')), Samples(selected.get('wrist_temp'))
    heart = Samples(selected.get('heart_rate'))
    nights = []
    for r in sleep_rows:
        if 'bedtime' not in r:
            continue
        bed, wake = datetime.fromisoformat(r['bedtime']), datetime.fromisoformat(r['wake'])
        oxygen = spo2.between(bed, wake)
        rates = resp.between(bed, wake)
        # Apple writes one breathing / wrist-temperature value per sleep session; its
        # timestamp may sit slightly outside the asleep span, so allow two hours.
        pad = timedelta(hours=2)
        dist, warm = breathing.between(bed - pad, wake + pad), temp.between(bed - pad, wake + pad)
        mid = bed + (wake - bed) / 2
        nights.append({'date': r['date'], 'bedtime': r['bedtime'], 'wake': r['wake'],
                       'midpoint': round(clock_hours(mid), 3), 'sleep': r['value'],
                       'spo2_n': len(oxygen), 'spo2_min': min(oxygen) if oxygen else None,
                       'spo2_low': sum(v < LOW_SPO2 for v in oxygen),
                       'respiratory': round(stats.median(rates), 2) if rates else None,
                       'breathing': round(max(dist), 2) if dist else None,
                       'wrist_temp': round(stats.median(warm), 3) if warm else None})

    def series(mid):
        night = {n['date']: n[mid] for n in nights if n.get(mid) is not None}
        if night:
            return night
        return {row['date']: row['value'] for row in by_id.get(mid, {}).get('rows', [])}

    scores = {mid: robust_z(series(mid), FLOOR[mid], direction) for mid, _, direction in SIGNALS}
    breathing_z = robust_z({n['date']: n['breathing'] for n in nights if n['breathing'] is not None},
                           FLOOR['breathing'], 1)
    days = []
    for day in sorted(set().union(*scores.values())):
        signals = {mid: scores[mid][day] for mid in scores if day in scores[mid]}
        days.append({'date': day, 'signals': signals, 'count': sum(s['flag'] for s in signals.values())})
    episodes = []
    for d in (x for x in days if x['count'] >= 2):
        flagged = {mid for mid, s in d['signals'].items() if s['flag']}
        if episodes and (date.fromisoformat(d['date']) - date.fromisoformat(episodes[-1]['end'])).days <= 2:
            episodes[-1].update(end=d['date'], days=episodes[-1]['days'] + 1,
                                signals=sorted(set(episodes[-1]['signals']) | flagged))
        else:
            episodes.append({'start': d['date'], 'end': d['date'], 'days': 1, 'signals': sorted(flagged)})
    for n in nights:
        rz, bz = scores['respiratory'].get(n['date']), breathing_z.get(n['date'])
        n['respiratory_z'] = rz['z'] if rz and n['respiratory'] is not None else None
        n['breathing_z'] = bz['z'] if bz else None
        items = [n['spo2_low'] > 0, bool(bz and bz['flag']), bool(rz and rz['flag'] and n['respiratory'] is not None)]
        n['flags'] = sum(items)

    wear = defaultdict(set)
    for start, _, _ in heart.rows:
        wear[start.date().isoformat()].add(start.hour)
    derived = []

    def add(mid, label, unit, kind, rows, note, fmt=None):
        if rows:
            m = {'id': mid, 'label': label, 'unit': unit, 'kind': kind, 'note': note, 'rows': rows, 'derived': True}
            if fmt:
                m['format'] = fmt
            derived.append(m)
    row = lambda d, v, n=1: {'date': d, 'value': v, 'n': n, 'min': v, 'max': v}
    add('spo2_sleep_min', '睡眠中最低血氧采样', '％', 'min',
        [row(n['date'], n['spo2_min'], n['spo2_n']) for n in nights if n['spo2_min'] is not None],
        '主睡眠窗口（入睡到醒来）内血氧采样的最低值，按醒来日期归属。采样稀疏，不是整夜连续监测，也不能换算低氧时长或 ODI。')
    add('respiratory_sleep', '睡眠中呼吸频率', '次／分', 'median',
        [row(n['date'], n['respiratory']) for n in nights if n['respiratory'] is not None],
        '主睡眠窗口内呼吸频率采样的中位数，按醒来日期归属；用于和自己的基线比较，不套用通用阈值。')
    add('sleep_midpoint', '主睡眠中点', '时刻', 'median',
        [row(n['date'], n['midpoint']) for n in nights],
        '入睡与醒来的中间时刻（报告时区），反映作息时间位置；不是睡眠质量评分。', 'clock')
    add('sri', '睡眠规律指数 · 近似', 'SRI', 'median', sleep_regularity(nights, sleep_intervals),
        '相邻两天同一时刻都处于睡着或都醒着的概率换算到 -100—100（100 = 完全一致）。只用主睡眠、午睡算作清醒，是对研究中 SRI 的近似，数值不能与研究队列直接比较。')
    add('wear_hours', '心率采样覆盖', '小时', 'sum',
        [row(d, len(h), len(h)) for d, h in sorted(wear.items())],
        '当天出现过心率采样的小时数，用来粗略判断手表是否佩戴；不是精确佩戴时长。')
    for m in derived:
        for r in m['rows']:
            r['source'] = None
    cross = {'params': {'baseline_days': BASE_DAYS, 'baseline_gap': BASE_GAP, 'baseline_min': BASE_MIN,
                        'z': Z, 'low_spo2': LOW_SPO2},
             'signals': [{'id': mid, 'label': label, 'direction': d} for mid, label, d in SIGNALS
                         if scores[mid]],
             'days': days, 'episodes': episodes, 'nights': nights}
    return cross, derived


def median_or_none(values, minimum):
    return stats.median(values) if len(values) >= minimum else None


def cross_findings(cross, by_id, end_date, add):
    """Append fixed-range cross findings through analyze.make_findings' add()."""
    end = end_date.isoformat()
    label = {s['id']: s['label'] for s in cross['signals']}
    episodes = cross['episodes']
    if episodes:
        last = episodes[-1]
        recent = (end_date - date.fromisoformat(last['end'])).days <= 14
        names = '、'.join(label.get(s, s) for s in last['signals'])
        add('attention' if recent else 'info',
            '近期多项信号同时偏离个人基线' if recent else '多项信号同时偏离个人基线的日子',
            f'【个人观察】共 {len(episodes)} 段日期中，有 2 项及以上信号同时明显偏离自己的近期基线；最近一段为 {last["start"]} — {last["end"]}，涉及{names}。'
            f'基线取当天前第 3—30 天的中位数，偏离按稳健离散度计算，至少 {Z:g} 倍才计入。'
            '研究发现静息心率、呼吸频率、睡眠等相对个人基线的同时变化常出现在感染、发热或应激前后，但饮酒、旅行与时差、高强度训练、作息变化、压力和生理周期也会造成同样变化。'
            '【行动】回想这几天是否有上述原因；如同时有发热、咳嗽、明显乏力等不适，按常规就医或检测，不要只凭本报告判断。', 'resting_hr')
    nights = [n for n in cross['nights'] if n['date'] >= (end_date - timedelta(days=89)).isoformat()]
    with_oxygen = [n for n in nights if n['spo2_n']]
    joint = [n for n in nights if n['flags'] >= 2]
    if joint:
        dates = '、'.join(n['date'] for n in joint[-10:])
        add('attention', '同一晚出现血氧低读数和呼吸指标偏高',
            f'【个人观察】最近 90 天有 {len(joint)} 晚同时出现两项及以上：睡眠中血氧采样低于 {LOW_SPO2}％、设备呼吸紊乱高于个人基线、睡眠呼吸频率高于个人基线。日期（醒来日）：{dates}。'
            '手表血氧只是稀疏采样，读数常偏高或偏低；设备呼吸紊乱也不是临床 AHI。'
            '【行动】若同时有打鼾、被人发现憋气、晨起头痛或明显白天嗜睡，咨询睡眠门诊或呼吸科，必要时做规范睡眠监测；Apple 自己的睡眠呼吸暂停通知按 30 天窗口评估，未收到通知不能排除。', 'spo2_sleep_min')
    elif with_oxygen:
        add('info', '夜间血氧与呼吸：没有同一晚多项同时偏离',
            f'最近 90 天有 {len(with_oxygen)} 晚在睡眠中有血氧采样，未出现血氧低读数与呼吸指标偏高同时发生的夜晚。采样稀疏，不能排除睡眠呼吸问题。', 'spo2_sleep_min')
    sleep_rows = [n for n in cross['nights'] if n['date'] >= (end_date - timedelta(days=89)).isoformat()]
    if len(sleep_rows) >= 14:
        mids = [n['midpoint'] for n in sleep_rows]
        beds = [clock_hours(datetime.fromisoformat(n['bedtime'])) for n in sleep_rows]
        free = [n['midpoint'] for n in sleep_rows if date.fromisoformat(n['date']).weekday() >= 5]
        work = [n['midpoint'] for n in sleep_rows if date.fromisoformat(n['date']).weekday() < 5]
        sri = [r['value'] for r in by_id.get('sri', {}).get('rows', []) if r['date'] >= sleep_rows[0]['date']]
        jet = f'周六、周日醒来的夜晚比其他夜晚的睡眠中点平均{"晚" if stats.mean(free) >= stats.mean(work) else "早"} {abs(stats.mean(free)-stats.mean(work))*60:.0f} 分钟；' if len(free) >= 4 and len(work) >= 4 else ''
        sri_text = f'近似睡眠规律指数平均 {stats.mean(sri):.0f}（{len(sri)} 对相邻夜）；' if len(sri) >= 7 else ''
        add('info', '睡眠规律：时间点的波动',
            f'最近 90 天 {len(sleep_rows)} 晚主睡眠，入睡时间的标准差 {stats.pstdev(beds)*60:.0f} 分钟，睡眠中点的标准差 {stats.pstdev(mids)*60:.0f} 分钟；{jet}{sri_text}'
            '英国生物银行的加速度计研究发现，睡眠规律性对全因死亡风险的预测力强于睡眠时长。本报告只与自己比较，不设合格线；轮班、跨时区和照护婴儿会让这些数值失真。', 'sri')
    trends = trend_table(by_id, end_date)
    speed = trends.get('walking_speed')
    gait = [t for k, t in trends.items() if k not in ('vo2', 'walking_hr') and t['adverse']]
    if speed and speed['delta'] <= -GAIT_SPEED_MEANINGFUL and speed['recent30'] is not None and speed['recent30'] <= speed['before'] - GAIT_SPEED_MEANINGFUL:
        others = '、'.join(t['label'] for t in gait if t['id'] != 'walking_speed') or '其他步态指标未见同向变化'
        add('attention' if len(gait) >= 3 else 'info', '步行速度相对个人基线持续下降',
            f'【个人观察】最近 90 天步行速度中位数 {speed["recent"]:.2f} km/h，前 90 天 {speed["before"]:.2f} km/h，下降 {-speed["delta"]:.2f} km/h，最近 30 天仍低于前期；同向变化的步态指标：{others}。'
            '老年人研究中步速每差 0.1 m/s（0.36 km/h）与生存率有关；手机携带位置、行走场景和受伤都会影响估算。'
            '【行动】若伴随乏力、疼痛、气短或跌倒，咨询医生；否则先排查携带方式变化，继续观察。', 'walking_speed')
    fit = [trends[k] for k in ('vo2', 'walking_hr', 'walking_speed') if k in trends]
    if fit:
        parts = '；'.join(f'{t["label"]} {t["before"]:.1f} → {t["recent"]:.1f}' for t in fit)
        hint = ''
        hr, sp = trends.get('walking_hr'), trends.get('walking_speed')
        if hr and sp and hr['delta'] <= -2 and sp['delta'] > -0.1:
            hint = '步速未下降而步行心率降低，与心肺适能提高的方向一致；'
        add('info', '体能趋势：只看自己的变化',
            f'前 90 天与最近 90 天的中位数：{parts}。{hint}手表心肺适能是估算，验证研究中平均低于实验室测量约 6 mL/kg/min，因此只看变化，不做等级划分。', 'vo2')


def trend_table(by_id, end_date):
    """Median of the previous 90 days vs the most recent 90 days, per trend metric."""
    recent_lo = (end_date - timedelta(days=89)).isoformat()
    before_lo = (end_date - timedelta(days=179)).isoformat()
    before_hi = (end_date - timedelta(days=90)).isoformat()
    last30 = (end_date - timedelta(days=29)).isoformat()
    out = {}
    for mid, label, direction in TREND:
        rows = by_id.get(mid, {}).get('rows', [])
        need = 3 if mid == 'vo2' else 10
        recent = median_or_none(window(rows, recent_lo, end_date.isoformat()), need)
        before = median_or_none(window(rows, before_lo, before_hi), need)
        if recent is None or before is None:
            continue
        ref = window(rows, before_lo, before_hi)
        spread = 1.4826 * stats.median(abs(v - before) for v in ref)
        delta = recent - before
        out[mid] = {'id': mid, 'label': label, 'recent': recent, 'before': before, 'delta': delta,
                    'recent30': median_or_none(window(rows, last30, end_date.isoformat()), 5),
                    'adverse': spread > 0 and -delta * direction >= spread}
    return out
