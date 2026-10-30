#!/usr/bin/env python3
"""Offline Apple Health XML/ZIP analysis. Python 3.10+, standard library only."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics as stats
import sys
import xml.etree.ElementTree as ET
import zipfile
from zoneinfo import ZoneInfo

Q = 'HKQuantityTypeIdentifier'
SLEEP = 'HKCategoryTypeIdentifierSleepAnalysis'
# id, label, canonical unit, aggregation, accepted units / conversion factors
SPECS = {
    Q+'RestingHeartRate': ('resting_hr', '静息心率', '次／分', 'median', {'count/min': 1}),
    Q+'HeartRate': ('heart_rate', '心率采样', '次／分', 'median', {'count/min': 1}),
    Q+'HeartRateVariabilitySDNN': ('hrv', '心率变异性 · SDNN', 'ms', 'median', {'ms': 1, 's': 1000}),
    Q+'HeartRateVariabilityRMSSD': ('hrv_rmssd', '心率变异性 · RMSSD', 'ms', 'median', {'ms': 1, 's': 1000}),
    Q+'OxygenSaturation': ('spo2', '血氧采样 · 日中位数', '％', 'median', {'%': 100}),
    Q+'RespiratoryRate': ('respiratory', '呼吸频率', '次／分', 'median', {'count/min': 1}),
    Q+'StepCount': ('steps', '记录步数', '步', 'sum', {'count': 1}),
    Q+'AppleExerciseTime': ('exercise', 'Apple 锻炼时间', '分钟', 'sum', {'min': 1, 's': 1/60}),
    Q+'ActiveEnergyBurned': ('active_energy', '活动能量', 'kcal', 'sum', {'kcal': 1, 'kJ': 1/4.184, 'Cal': 1}),
    Q+'DistanceWalkingRunning': ('distance', '步行与跑步距离', 'km', 'sum', {'km': 1, 'm': .001, 'mi': 1.609344}),
    Q+'BodyMass': ('weight', '体重 · 历史测量', 'kg', 'median', {'kg': 1, 'lb': .45359237}),
    Q+'Height': ('height', '身高 · 历史测量', 'cm', 'median', {'cm': 1, 'm': 100, 'in': 2.54, 'ft': 30.48}),
    Q+'VO2Max': ('vo2', '心肺适能估算', 'mL/kg/min', 'median', {'mL/min·kg': 1, 'ml/kg*min': 1, 'mL/kg/min': 1}),
    Q+'AppleSleepingWristTemperature': ('wrist_temp', '睡眠腕部皮肤温度', '℃', 'median', {'degC': 1, 'degF': 'fahrenheit'}),
    Q+'AppleSleepingBreathingDisturbances': ('breathing_disturbances', '睡眠呼吸紊乱 · 设备指标', 'count', 'median', {'count': 1}),
    Q+'WalkingHeartRateAverage': ('walking_hr', '步行平均心率', '次／分', 'median', {'count/min': 1}),
    Q+'TimeInDaylight': ('daylight', '记录日照时间', '分钟', 'sum', {'min': 1, 's': 1/60}),
    Q+'BasalEnergyBurned': ('basal_energy', '静息能量估算', 'kcal', 'sum', {'kcal': 1, 'kJ': 1/4.184}),
    Q+'FlightsClimbed': ('flights', '爬楼层数', '层', 'sum', {'count': 1}),
    Q+'AppleStandTime': ('stand_time', '站立时间', '分钟', 'sum', {'min': 1, 's': 1/60}),
    Q+'EnvironmentalAudioExposure': ('environment_audio', '环境声音采样', 'dBA', 'median', {'dBASPL': 1, 'dBA': 1}),
    Q+'HeadphoneAudioExposure': ('headphone_audio', '耳机声音采样', 'dBA', 'median', {'dBASPL': 1, 'dBA': 1}),
    Q+'EnvironmentalSoundReduction': ('sound_reduction', '环境降噪量', 'dB', 'median', {'dBASPL': 1, 'dB': 1}),
    Q+'WalkingDoubleSupportPercentage': ('double_support', '步行双支撑比例', '％', 'median', {'%': 100}),
    Q+'WalkingAsymmetryPercentage': ('walking_asymmetry', '步行不对称比例', '％', 'median', {'%': 100}),
    Q+'AppleWalkingSteadiness': ('walking_steadiness', '步行稳定性估算', '％', 'median', {'%': 100}),
    Q+'WalkingSpeed': ('walking_speed', '步行速度', 'km/h', 'median', {'km/hr': 1, 'm/s': 3.6, 'mi/hr': 1.609344}),
    Q+'WalkingStepLength': ('step_length', '步行步长', 'cm', 'median', {'cm': 1, 'm': 100, 'in': 2.54}),
    Q+'SixMinuteWalkTestDistance': ('six_min_walk', '六分钟步行距离估算', 'm', 'median', {'m': 1, 'km': 1000, 'ft': .3048}),
    Q+'StairAscentSpeed': ('stair_ascent', '上楼速度', 'm/s', 'median', {'m/s': 1, 'ft/s': .3048}),
    Q+'StairDescentSpeed': ('stair_descent', '下楼速度', 'm/s', 'median', {'m/s': 1, 'ft/s': .3048}),
    Q+'HeartRateRecoveryOneMinute': ('hr_recovery', '一分钟心率恢复', '次／分', 'median', {'count/min': 1}),
    Q+'PhysicalEffort': ('physical_effort', '身体用力程度估算', 'kcal/h/kg', 'median', {'kcal/hr·kg': 1}),
    Q+'EstimatedWorkoutEffortScore': ('workout_effort', '训练努力程度估算', '分', 'median', {'appleEffortScore': 1}),
    'HKDataTypeSleepDurationGoal': ('sleep_goal', '设置的睡眠目标', '小时', 'median', {'hr': 1, 'h': 1, 'min': 1/60}),
    'HKCategoryTypeIdentifierAppleStandHour': ('stand_hours', '站立达标小时', '小时', 'sum', {}),
    'HKCategoryTypeIdentifierMindfulSession': ('mindful', '正念记录时长', '分钟', 'sum', {}),
}
NOTES = {
    'spo2': '百分比按 HealthKit 的 0—1 比例转换。日中位数不是整夜连续血氧；最低值另图呈现。',
    'spo2_min': '每日最低离散采样点，不是低氧持续时长；先核实测量质量，不能仅据手表读数诊断。',
    'hrv': '仅 SDNN；与 RMSSD 分开。日中位数受采样时机与设备影响，不设通用健康阈值。',
    'hrv_rmssd': '仅 RMSSD；不与 SDNN 混合，不能根据单点诊断压力或疾病。',
    'heart_rate': '混合静息、运动等场景的采样中位数，不替代静息心率，不排除阵发性心律问题。',
    'wrist_temp': '腕部皮肤温度，不是核心体温，不能用作发热诊断。',
    'breathing_disturbances': '保留导出单位，不等同于临床 AHI，不套用 AHI 分级。',
    'vo2': '设备估算值；年龄、身体资料、药物和算法均可能影响估计，不作临床分级。',
    'exercise': 'Apple 识别的锻炼分钟，不等同于经验证的中高强度活动分钟。',
    'environment_audio': '声音采样的日中位数，不是时间加权等效声级，也不是全天听力剂量；不能用 dB 算术均值推断暴露风险。',
    'headphone_audio': '声音采样的日中位数，不代表全天收听时长或噪声剂量；不同来源分开，不据此排除听力问题。',
    'sound_reduction': '设备记录的降噪量，不是听力敏感度或听力损失。',
    'double_support': '设备步态估算，受步速、手机携带位置和场景影响；不据通用阈值诊断步态疾病。',
    'walking_asymmetry': '设备步态估算，不对单点作临床分级；与双支撑比例不同。',
    'walking_steadiness': '保留设备比例值，不把百分数解释成个人跌倒概率。',
    'six_min_walk': '设备估算，不替代标准化六分钟步行试验。',
    'hr_recovery': '设备测量情境可能不同，不套用临床运动试验阈值。',
    'physical_effort': '设备用力程度估算，不是训练总负荷或临床 MET 测试结果。',
    'workout_effort': '设备训练评分，不是综合健康评分；不直接换算为患病风险。',
    'sleep_goal': '用户设置的目标，不是实际睡眠测量，不前向填充到未记录日。',
    'stand_hours': '每小时至少一次站立达标的记录数，不代表连续站立了这些小时；同来源同小时取是否达标的最大值。',
    'mindful': '记录区间时长，不代表心理健康疗效或实际完成质量。',
}


def parse_time(value, tz=None):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError('Timestamp must include UTC offset')
    return result.astimezone(tz) if tz else result


class SafeReader:
    """Reject entity declarations without rejecting Apple's ordinary inline DTD."""
    def __init__(self, stream, limit):
        self.stream, self.limit, self.total, self.tail = stream, limit, 0, b''

    def read(self, size=-1):
        chunk = self.stream.read(size)
        self.total += len(chunk)
        if self.total > self.limit:
            raise ValueError('XML exceeds configured byte limit')
        probe = (self.tail + chunk).upper()
        if b'<!ENTITY' in probe or b'\x00' in chunk:
            raise ValueError('Entity declarations and UTF-16 XML are not supported')
        self.tail = probe[-16:]
        return chunk


@contextmanager
def open_export(path, max_bytes):
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            candidates = [i for i in archive.infolist() if i.filename.lower().endswith('.xml')
                          and Path(i.filename).name.lower() != 'export_cda.xml'
                          and not i.filename.startswith('__MACOSX/')]
            if len(candidates) != 1:
                raise ValueError('Expected exactly one main XML (excluding export_cda.xml)')
            info = candidates[0]
            if info.file_size > max_bytes:
                raise ValueError('ZIP member exceeds configured byte limit')
            with archive.open(info) as stream:
                yield SafeReader(stream, max_bytes)
    else:
        with path.open('rb') as stream:
            yield SafeReader(stream, max_bytes)


def seconds_between(start, end):
    return end.timestamp() - start.timestamp()


def union_intervals(intervals):
    merged = []
    for start, end in sorted(intervals, key=lambda pair: pair[0].timestamp()):
        if merged and start.timestamp() <= merged[-1][1].timestamp():
            merged[-1][1] = max(merged[-1][1], end, key=lambda dt: dt.timestamp())
        else:
            merged.append([start, end])
    return merged


def split_days(start, end, value):
    """Prorate cumulative samples crossing midnight; documented approximation."""
    duration = seconds_between(start, end)
    if duration <= 0:
        yield start.date().isoformat(), value
        return
    cursor = start
    while cursor < end:
        tomorrow = cursor.date() + timedelta(days=1)
        boundary = datetime.combine(tomorrow, datetime.min.time(), tzinfo=start.tzinfo)
        stop = min(boundary, end)
        yield cursor.date().isoformat(), value * (seconds_between(cursor, stop) / duration)
        cursor = stop


def digest_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def load_export(path, tz, max_bytes):
    records = defaultdict(lambda: defaultdict(list))
    inventory, issues = Counter(), Counter()
    source_inventory = defaultdict(dict)
    seen = set()
    devices, workouts, export_date = {}, [], None
    all_start, all_end = None, None
    with open_export(path, max_bytes) as stream:
        context = ET.iterparse(stream, events=('start', 'end'))
        _, root = next(context)
        if root.tag != 'HealthData':
            raise ValueError('Expected an Apple Health HealthData root')
        for event, elem in context:
            if event != 'end':
                continue
            a = elem.attrib
            if elem.tag == 'ExportDate':
                export_date = a.get('value')
            if elem.tag == 'Record':
                typ = a.get('type', 'unknown')
                inventory[typ] += 1
                source = a.get('sourceName', 'Unknown')
                device = a.get('device', '')
                watch_device = 'watch' in device.lower() or (
                    'apple' in source.lower() and 'watch' in source.lower()) or source.startswith('Synthetic Watch')
                family = 'Watch' if watch_device else (
                    'Phone' if 'iphone' in (source + device).lower() or source.startswith('Synthetic Phone') else 'Other')
                devices[source] = family
                summary = source_inventory[typ].setdefault(
                    source, {'records': 0, 'start': None, 'end': None})
                summary['records'] += 1
                try:
                    start = parse_time(a['startDate'], tz)
                    end = parse_time(a['endDate'], tz)
                    if end.timestamp() < start.timestamp():
                        raise ValueError('negative duration')
                    all_start = start if all_start is None else min(start, all_start)
                    all_end = end if all_end is None else max(end, all_end)
                    summary['start'] = start if summary['start'] is None else min(start, summary['start'])
                    summary['end'] = end if summary['end'] is None else max(end, summary['end'])
                except (ValueError, KeyError, OverflowError):
                    issues['invalid_timestamp'] += 1
                    elem.clear()
                    root.clear()
                    continue
                if typ in SPECS or typ == SLEEP:
                    key = '\x1f'.join([typ, source, start.isoformat(), end.isoformat(), a.get('value', ''), a.get('unit', '')])
                    h = hashlib.sha256(key.encode()).digest()
                    if h in seen:
                        issues['duplicates'] += 1
                    else:
                        seen.add(h)
                        if typ == SLEEP:
                            records[typ][source].append((start, end, a.get('value', '')))
                        else:
                            try:
                                if typ == 'HKCategoryTypeIdentifierMindfulSession':
                                    val, factor = seconds_between(start, end)/60, 1
                                elif typ == 'HKCategoryTypeIdentifierAppleStandHour':
                                    states = {'HKCategoryValueAppleStandHourStood': 1,
                                              'HKCategoryValueAppleStandHourIdle': 0,
                                              '0': 1, '1': 0}
                                    val, factor = states[a['value']], 1
                                else:
                                    factor = SPECS[typ][4][a.get('unit', '')]
                                    val = float(a['value'])
                                if not math.isfinite(val):
                                    raise ValueError('non-finite value')
                                if a.get('unit') == '%' and not 0 <= val <= 1:
                                    raise ValueError('HealthKit percentages must use fractional values')
                                val = (val - 32) * 5/9 if factor == 'fahrenheit' else val * factor
                                if val < 0 and typ != Q+'AppleSleepingWristTemperature':
                                    raise ValueError('negative value')
                                records[typ][source].append((start, end, val))
                            except (ValueError, KeyError, OverflowError):
                                issues['invalid_value_or_unit'] += 1
            elif elem.tag == 'Workout':
                try:
                    start, end = parse_time(a['startDate'], tz), parse_time(a['endDate'], tz)
                    minutes = float(a.get('duration', seconds_between(start, end)/60))
                    unit = a.get('durationUnit', 'min')
                    if unit not in ('min', 's', 'h'):
                        raise ValueError('unsupported workout duration unit')
                    minutes *= {'min': 1, 's': 1/60, 'h': 60}[unit]
                    if not math.isfinite(minutes) or minutes < 0 or end.timestamp() < start.timestamp():
                        raise ValueError('invalid workout')
                    w = (start.isoformat(), end.isoformat(), a.get('workoutActivityType', 'Unknown'), round(minutes, 5))
                    if w not in workouts:
                        workouts.append(w)
                except (ValueError, KeyError):
                    issues['invalid_workout'] += 1
            elif elem.tag == 'ActivitySummary':
                issues['activity_summary_rows'] += 1
            if elem.tag in ('Record', 'Workout', 'ActivitySummary', 'ExportDate', 'Me', 'ClinicalRecord'):
                elem.clear()
                root.clear()
    if not inventory:
        raise ValueError('No health records found')
    alias = {}
    family_count = Counter()
    for source, family in devices.items():
        family_count[family] += 1
        alias[source] = f'{family} {family_count[family]}'
    return records, inventory, issues, alias, devices, workouts, export_date, all_start, all_end, source_inventory


def select_source(groups, devices, requested=None, prefer_watch=True):
    if requested:
        if requested not in groups:
            raise ValueError('Requested source is not present for metric')
        return requested
    # Select ONE source for the entire metric. No silent phone/watch stitching.
    return max(groups, key=lambda s: (prefer_watch and devices.get(s) == 'Watch',
               len({r[0].date() for r in groups[s]}), len(groups[s]), s))


def aggregate_metric(typ, rows, source):
    mid, label, unit, kind, _ = SPECS[typ]
    buckets = defaultdict(list)
    if mid == 'stand_hours':
        hours = {}
        for start, end, value in rows:
            key = start.replace(minute=0, second=0, microsecond=0)
            hours[key] = max(hours.get(key, 0), value)
        rows = [(t, t, v) for t, v in hours.items()]
    elif mid == 'mindful':
        rows = [(s, e, seconds_between(s, e)/60)
                for s, e in union_intervals([(s, e) for s, e, _ in rows])]
    for start, end, value in rows:
        if kind == 'sum':
            for day, val in split_days(start, end, value):
                buckets[day].append(val)
        else:
            buckets[start.date().isoformat()].append(value)
    daily = []
    for day, values in sorted(buckets.items()):
        val = sum(values) if kind == 'sum' else stats.median(values)
        daily.append({'date': day, 'value': round(val, 4), 'n': len(values),
                      'min': round(min(values), 4), 'max': round(max(values), 4), 'source': source})
    note = NOTES.get(mid, '') + (' 单一来源按日累加；跨午夜按区间时长比例分摊。n 为当日参与记录数，跨日合计可重复计数同一记录。记录首日与导出日可能不完整；不证明全天佩戴。' if kind == 'sum' else ' 单一来源按日取采样中位数。')
    return {'id': mid, 'label': label, 'unit': unit, 'kind': kind, 'note': note.strip(), 'rows': daily}


def sleep_metrics(rows, source):
    stage_names = {'HKCategoryValueSleepAnalysisAsleepCore', 'HKCategoryValueSleepAnalysisAsleepDeep',
                   'HKCategoryValueSleepAnalysisAsleepREM', '3', '4', '5'}
    unspecified = {'HKCategoryValueSleepAnalysisAsleep', 'HKCategoryValueSleepAnalysisAsleepUnspecified', '1'}
    staged = [(s, e) for s, e, v in rows if v in stage_names]
    simple = [(s, e) for s, e, v in rows if v in unspecified]
    # Prefer staged sleep if available; unspecified remains a separate metric.
    use = staged or simple
    if not use:
        return [], []
    merged = union_intervals(use)
    episodes = []
    for start, end in merged:
        if episodes and seconds_between(episodes[-1][-1][1], start) <= 90*60:
            episodes[-1].append((start, end))
        else:
            episodes.append([(start, end)])
    by_day = defaultdict(list)
    for episode in episodes:
        by_day[episode[-1][1].date().isoformat()].append(episode)
    daily = []
    main_intervals = []
    for day, candidates in sorted(by_day.items()):
        longest = max(candidates, key=lambda ep: sum(seconds_between(s, e) for s,e in ep))
        hours = sum(seconds_between(s, e) for s,e in longest)/3600
        if hours > 24:
            continue
        main_intervals.extend(longest)
        daily.append({'date': day, 'value': round(hours, 5), 'n': len(longest), 'min': round(hours, 5),
                      'max': round(hours, 5), 'source': source, 'bedtime': longest[0][0].isoformat(),
                      'wake': longest[-1][1].isoformat()})
    result = [{'id': 'sleep', 'label': '主睡眠 · 实睡时长', 'unit': '小时', 'kind': 'sum',
               'note': '按醒来日期归属；相邻片段间隔不超过 90 分钟组成一次睡眠，每日取实睡最长的一次。优先分期区间取并集，不含清醒、卧床或额外午睡；不是每日总睡眠，n 为实睡并集片段数。', 'rows': daily}]
    if staged and simple:
        simple_buckets = defaultdict(list)
        for start, end in union_intervals(simple):
            # Remove intersections with staged sleep before counting unspecified.
            pieces = [(start, end)]
            for a, b in merged:
                remaining = []
                for c, d in pieces:
                    if b <= c or a >= d:
                        remaining.append((c,d))
                    else:
                        if c < a: remaining.append((c,a))
                        if b < d: remaining.append((b,d))
                pieces = remaining
            for a,b in pieces:
                for day,hours in split_days(a,b,seconds_between(a, b)/3600):
                    simple_buckets[day].append(hours)
        naps = [{'date': d, 'value': round(sum(v),5), 'n': len(v), 'min': round(sum(v),5),
                 'max': round(sum(v),5), 'source': source} for d,v in sorted(simple_buckets.items())]
        result.append({'id': 'sleep_unspecified', 'label': '额外未分期睡眠', 'unit': '小时', 'kind': 'sum',
                       'note': '未分期睡眠区间并集，扣除与分期睡眠重叠；可能包含午睡，不自动等同于午睡。', 'rows': naps})
    # 分期仅描述主睡眠窗口内的记录，不用深睡比例诊断疾病。
    if staged:
        phases = [
            ('sleep_core', '核心睡眠记录', {'HKCategoryValueSleepAnalysisAsleepCore', '3'}),
            ('sleep_deep', '深睡记录', {'HKCategoryValueSleepAnalysisAsleepDeep', '4'}),
            ('sleep_rem', 'REM 睡眠记录', {'HKCategoryValueSleepAnalysisAsleepREM', '5'}),
            ('sleep_awake', '主睡眠窗口内清醒记录', {'HKCategoryValueSleepAnalysisAwake', '2'}),
        ]
        for mid, label, names in phases:
            phase_rows = []
            intervals = [(s, e) for s, e, v in rows if v in names]
            for night in daily:
                begin, stop = parse_time(night['bedtime']), parse_time(night['wake'])
                overlap = [(max(s, begin), min(e, stop)) for s, e in intervals
                           if s < stop and e > begin]
                merged_phase = union_intervals(overlap)
                if not merged_phase:
                    continue
                hours = sum(seconds_between(s, e) for s, e in merged_phase)/3600
                phase_rows.append({'date': night['date'], 'value': round(hours, 5),
                                   'n': len(merged_phase), 'min': round(hours, 5),
                                   'max': round(hours, 5), 'source': source})
            result.append({'id': mid, 'label': label, 'unit': '小时', 'kind': 'sum',
                           'note': '主睡眠窗口内该分期记录取并集；没有该分期记录不补零。各分期单独求并集，矛盾重叠时不可直接相加；不依据分期时长诊断睡眠质量。',
                           'rows': phase_rows})
    return result, main_intervals


def mean(values):
    return stats.mean(values) if values else None


def make_findings(data, selected, sleep_intervals, end_date):
    by_id = {m['id']: m for m in data['metrics']}
    findings = []
    def add(level, title, body, metric=None):
        findings.append({'level': level, 'title': title, 'body': body, 'metric': metric})
    oxygen = selected.get('spo2', [])
    if oxygen:
        low = [(s,v) for s,e,v in oxygen if v < 90]
        below95 = sum(v < 95 for s,e,v in oxygen)
        if low:
            asleep = sum(any(a <= t < b for a,b in sleep_intervals) for t,v in low)
            events = '；'.join(f'{s:%m-%d %H:%M}，{v:g}％' for s,v in low[:20])
            add('attention', '优先核实：反复出现血氧低读数',
                f'【个人观察】所选来源共 {len(oxygen):,} 次采样，最低 {min(v for s,e,v in oxygen):g}％；低于 90％ 共 {len(low)} 次，涉及 {len({s.date() for s,v in low})} 个日期，其中 {asleep} 次落在所识别主睡眠片段内。低于 95％ 共 {below95} 次。这些是采样点计数，不是低氧时间占比。低值时间（报告时区）为：{events}。'
                '【行动】先核实佩戴和测量质量，可用正规指夹式血氧仪复测；若反复低值或伴打鼾、憋醒、明显白天嗜睡，咨询呼吸科／睡眠门诊。历史手表低值不能直接作为急诊诊断；当前严重呼吸困难、胸痛或意识异常时立即就医。', 'spo2_min')
        else:
            add('info', '血氧：未检出本规则标记的低值', f'所选来源 {len(oxygen):,} 次采样未出现低于 90％ 的值。不代表连续夜间监测正常，也不能排除睡眠呼吸问题。', 'spo2')
    sleep = by_id.get('sleep', {}).get('rows', [])
    if sleep:
        recent = [r for r in sleep if r['date'] >= (end_date-timedelta(days=89)).isoformat()]
        if recent:
            vals = [r['value'] for r in recent]
            under = sum(v<7 for v in vals)
            add('attention' if under/len(vals) >= .25 else 'info', '睡眠：先看时长与规律，不给深睡打分',
                f'截至数据末日最近 90 天内，记录 {len(vals)} 次主睡眠，平均 {mean(vals):.2f} 小时，范围 {min(vals):.2f}—{max(vals):.2f} 小时，{under} 次不足 7 小时。主睡眠排除午睡，不等于每日总睡眠。7 小时仅作为成人教育性参考，年龄未知时不作年龄适配判断；手表分期不能用于诊断深睡不足。', 'sleep')
    rhr = by_id.get('resting_hr', {}).get('rows', [])
    recent = [r for r in rhr if r['date'] >= (end_date-timedelta(days=29)).isoformat()]
    if recent:
        vals = [r['value'] for r in recent]
        add('info', '静息心率：观察个人基线', f'最近 30 天有 {len(vals)} 个记录日，日值均值 {mean(vals):.1f} 次／分，范围 {min(vals):g}—{max(vals):g}。不把运动或睡眠时的心率极值混入静息心率结论；有症状时不能用总体均值替代临床评估。', 'resting_hr')
    for mid in ('weight','height'):
        metric = by_id.get(mid)
        if metric and metric['rows']:
            last = metric['rows'][-1]
            age = (end_date-datetime.fromisoformat(last['date']).date()).days
            if age > 180:
                add('quality', f'{metric["label"]}已经过期', f'最近一条为 {last["date"]}，{last["value"]:g} {metric["unit"]}，距数据末日 {age} 天。只是历史测量，不代表当前状态；不据此计算当前 BMI 或评价当前体重。', mid)
    steps = by_id.get('steps', {}).get('rows', [])
    if len(steps)>2:
        start = max(steps[0]['date'], (end_date-timedelta(days=89)).isoformat())
        complete = [r for r in steps if start < r['date'] < end_date.isoformat()]
        if complete:
            vals = [r['value'] for r in complete]
            add('info', '活动：记录少不一定等于活动少', f'最近 90 天内排除所选来源起始日及数据末日，有 {len(vals)} 个记录日，平均 {mean(vals):,.0f} 步，{sum(v<2000 for v in vals)} 日少于 2,000 步。2,000 步只是描述性分组，不是医疗阈值。没有全天佩戴证据；缺失日期不当作零，不把手机与手表相加。', 'steps')
    if by_id.get('breathing_disturbances'):
        add('quality','呼吸紊乱低数值不能排除睡眠呼吸暂停', '设备呼吸紊乱指标不等于临床 AHI；未见通知记录也不证明没有疾病或通知功能已经开启。结合症状、设备适用范围与规范睡眠监测判断。','breathing_disturbances')
    return findings


def analyze(path, timezone_name=None, config=None, max_bytes=2_000_000_000):
    config = config or {}
    tz = ZoneInfo(timezone_name) if timezone_name else None
    parsed = load_export(path, tz, max_bytes)
    records, inventory, issues, aliases, devices, workouts, exported, first, last, source_inventory = parsed
    export_dt = parse_time(exported, tz) if exported else last
    end_date = min(last.date(), export_dt.date())
    metrics, selected, source_choices, quality = [], {}, {}, []
    sleep_intervals = []
    for typ, groups in records.items():
        if not groups:
            continue
        mid = 'sleep' if typ == SLEEP else SPECS[typ][0]
        chosen = select_source(groups, devices, config.get('sources', {}).get(mid),
                               prefer_watch=mid != 'headphone_audio')
        rows = groups[chosen]
        selected[mid] = rows
        source_choices[mid] = {'selected': aliases[chosen], 'available': [aliases[s] for s in groups],
                               'records': len(rows), 'first': min(r[0] for r in rows).isoformat(),
                               'last': max(r[1] for r in rows).isoformat()}
        if len(groups)>1:
            quality.append(f'{mid} 有 {len(groups)} 个来源，默认采用 {aliases[chosen]}；其他来源已独立聚合，可切换查看，不自动拼接或相加。')
        variants = {}
        for source, source_rows in groups.items():
            if typ == SLEEP:
                built, intervals = sleep_metrics(source_rows, aliases[source])
                if source == chosen:
                    sleep_intervals = intervals
            else:
                metric = aggregate_metric(typ, source_rows, aliases[source])
                built = [metric]
                if mid == 'spo2':
                    built.append({'id': 'spo2_min', 'label': '血氧采样 · 每日最低值',
                                  'unit': '％', 'kind': 'min', 'note': NOTES['spo2_min'],
                                  'rows': [{**r, 'value': r['min']} for r in metric['rows']]})
            variants[aliases[source]] = {m['id']: m for m in built}
        ids = dict.fromkeys(m_id for group in variants.values() for m_id in group)
        for m_id in ids:
            template = next(group[m_id] for group in variants.values() if m_id in group)
            primary = variants[aliases[chosen]].get(m_id, {**template, 'rows': []})
            metrics.append({**primary, 'default_source': aliases[chosen],
                            'source_series': {alias: group[m_id]['rows'] if m_id in group else []
                                              for alias, group in variants.items()}})
    order = ['sleep','spo2_min','spo2','resting_hr','hrv','hrv_rmssd','respiratory','steps','exercise','active_energy','vo2','heart_rate']
    metrics.sort(key=lambda m: order.index(m['id']) if m['id'] in order else len(order))
    by_type = defaultdict(lambda: [0,0.0])
    for s,e,typ,minutes in workouts:
        by_type[typ][0] += 1
        by_type[typ][1] += minutes
    workout_days = defaultdict(list)
    for start, stop, typ, minutes in workouts:
        workout_days[parse_time(start).date().isoformat()].append(minutes)
    for mid, label, unit in [('workout_minutes', '训练记录时长', '分钟'),
                              ('workout_sessions', '训练记录次数', '次')]:
        daily = []
        for date, values in sorted(workout_days.items()):
            value = sum(values) if mid == 'workout_minutes' else len(values)
            daily.append({'date': date, 'value': round(value, 4), 'n': len(values),
                          'min': round(value, 4), 'max': round(value, 4), 'source': 'Workout'})
        if daily:
            metrics.append({'id': mid, 'label': label, 'unit': unit, 'kind': 'sum',
                            'rows': daily, 'default_source': 'Workout',
                            'source_series': {'Workout': daily},
                            'note': 'Workout 训练记录，按开始日期归属；不是全天运动总量。不与 Apple 锻炼分钟相加，未记录日不补零。'})
    coverage_items = []
    for typ, count in inventory.most_common():
        mid = 'sleep' if typ == SLEEP else SPECS[typ][0] if typ in SPECS else None
        choice = source_choices.get(mid, {})
        groups = records.get(typ, {})
        processed = sum(len(values) for values in groups.values())
        label = '睡眠分析记录' if typ == SLEEP else SPECS[typ][1] if typ in SPECS else typ
        available = []
        for source, summary in source_inventory[typ].items():
            available.append({'source': aliases[source], 'records': summary['records'],
                              'start': summary['start'].isoformat() if summary['start'] else None,
                              'end': summary['end'].isoformat() if summary['end'] else None})
        coverage_items.append({'type': typ, 'label': label,
                               'status': 'analyzed' if processed else 'inventory_only',
                               'total_records': count, 'processed_records': processed,
                               'selected_records': choice.get('records', 0),
                               'selected_source': choice.get('selected'),
                               'available_sources': available,
                               'reason': ('各来源已独立处理；默认图表采用一个来源。睡眠清醒／卧床记录按口径排除，不把读取数称为医学覆盖率。'
                                          if typ == SLEEP else '已按指标口径汇总；各来源可分别查看，不代表完成临床评估。')
                                         if processed else '未实现该类型分析，或没有可解释的有效记录；仅列目录，不推断健康意义。'})
    coverage = {'total_records': sum(inventory.values()),
                'supported_records': sum(v for k, v in inventory.items() if k in SPECS or k == SLEEP),
                'processed_records': sum(i['processed_records'] for i in coverage_items),
                'selected_records': sum(i['selected_records'] for i in coverage_items),
                'analyzed_types': sum(i['status'] == 'analyzed' for i in coverage_items),
                'total_types': len(inventory), 'items': coverage_items}
    quality += [
        '各来源分别聚合；默认优先手表，再比较覆盖日期；耳机声音直接优先覆盖日期。切换来源不是拼接或相加，并非复现健康 App 的内部优先级合并。',
        '仅对所支持指标按类型、来源、起止时间、原始值、单位去除完全重复；重叠的不同累计样本仍可能重复计量，不声称重建了 Apple 的融合结果。',
        '未知类型只做目录计数，不生成未经定义的医学判断。所有来源名称替换为通用别名；不读取路线 GPS、出生日期、性别或个人姓名。',
        '累计记录跨午夜按时间比例分摊，假设区间均匀；心率、血氧等离散值按采样开始日归属，不进行时间插值。',
        '图中只有已记录日；无数据不是零。数据首尾日可能不完整，样本数不是全天佩戴时长。',
        '主睡眠按最长会话识别，不适合直接推断轮班、分段睡眠或临床睡眠效率；分期优先可能忽略无分期日期，必要时检查原始记录。',
        f'另有 {issues["activity_summary_rows"]:,} 条 ActivitySummary，只计数，不叠加到原始 Record。',
        '分析是消费级设备观察性汇总，不提供诊断、处方或健康总分。当前急性症状优先就医，不等待报告。',
    ]
    data = {'schema_version': 1,
            'meta': {'generated_at': datetime.now(timezone.utc).isoformat(), 'export_date': exported or '未提供',
                     'start': first.date().isoformat(), 'end': end_date.isoformat(),
                     'timezone': timezone_name or '保留记录自带 UTC 偏移；跨时区比较需谨慎',
                     'records': sum(inventory.values()), 'duplicates': issues['duplicates'],
                     'invalid': issues['invalid_timestamp']+issues['invalid_value_or_unit']+issues['invalid_workout'],
                     'source_policy': '全来源独立聚合；默认优先 Watch，再比较日期覆盖；耳机声音优先覆盖；不拼接或相加',
                     'input_sha256': digest_file(path)},
            'metrics': metrics, 'quality': quality, 'source_choices': source_choices, 'coverage': coverage,
            'inventory': [{'type': k, 'count': v} for k,v in inventory.most_common()],
            'workouts': {'count': len(workouts), 'minutes': round(sum(w[3] for w in workouts),2),
                         'by_type': [{'type': k, 'count': v[0], 'minutes': round(v[1],2)} for k,v in by_type.items()]},
            'sources': config.get('references', []), 'issues': dict(issues)}
    core_dates = [r['date'] for m in metrics if m['id'] in ('sleep', 'resting_hr', 'spo2')
                  for r in m['rows'] if r['date'] >= (end_date-timedelta(days=89)).isoformat()]
    data['meta']['focus_start'] = min(core_dates) if core_dates else max(first.date(), end_date-timedelta(days=29)).isoformat()
    data['findings'] = make_findings(data, selected, sleep_intervals, end_date)
    if not data['sources']:
        data['quality'].append('未附本次核验的外部参考资料；数值分组仅供描述，不构成已核验的临床阈值或个体建议。')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='Apple Health export ZIP or XML')
    parser.add_argument('--output-dir', type=Path, required=True, help='Private directory outside the skill tree')
    parser.add_argument('--timezone', help='IANA zone; default preserves each sample offset')
    parser.add_argument('--config', type=Path, help='Optional private JSON: sources overrides and references')
    parser.add_argument('--max-xml-mb', type=int, default=2000)
    parser.add_argument('--analyze-only', action='store_true')
    args = parser.parse_args()
    base = Path(__file__).resolve().parents[1]
    out = args.output_dir.expanduser().resolve()
    if out == base or base in out.parents:
        parser.error('Outputs must be outside the skill directory')
    if args.max_xml_mb <= 0:
        parser.error('--max-xml-mb must be positive')
    config = json.loads(args.config.read_text()) if args.config else {}
    data = analyze(args.input.expanduser(), args.timezone, config, args.max_xml_mb*1_000_000)
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name, text in [('analysis.json', json.dumps(data, ensure_ascii=False, indent=2))]:
        target = out / name
        if target.is_symlink():
            raise ValueError('Refusing symlink output')
        target.write_text(text, encoding='utf-8')
        target.chmod(0o600)
    if not args.analyze_only:
        from render import render_report
        target = out / 'report.html'
        if target.is_symlink():
            raise ValueError('Refusing symlink output')
        target.write_text(render_report(data), encoding='utf-8')
        target.chmod(0o600)
    print(json.dumps({'status': 'ok', 'records': data['meta']['records'], 'metrics': len(data['metrics']),
                      'output_dir': str(out)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
