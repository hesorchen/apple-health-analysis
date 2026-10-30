#!/usr/bin/env python3
"""Create explicitly fictional Apple Health XML; no user data is read."""
import argparse
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import xml.etree.ElementTree as ET


def make_xml():
    root = ET.Element('HealthData', locale='en_US')
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    stamp = lambda dt: dt.strftime('%Y-%m-%d %H:%M:%S %z')
    ET.SubElement(root, 'ExportDate', value=stamp(start + timedelta(days=60)))

    def record(typ, begin, end, value, unit=None, source='Synthetic Watch'):
        attrs = {'type': typ, 'sourceName': source, 'startDate': stamp(begin),
                 'endDate': stamp(end), 'value': str(value)}
        if unit: attrs['unit'] = unit
        ET.SubElement(root, 'Record', **attrs)

    for day in range(60):
        if day in (13, 14, 35):
            continue  # 明确的缺失，不能补零。
        base = start + timedelta(days=day)
        # 周六、周日醒来的夜晚晚睡 75 分钟，其余夜晚小幅波动；用于睡眠规律展示。
        late = 1.25 if day % 7 in (5, 6) else 0
        s = base + timedelta(hours=.6 + late + .25 * math.sin(day * 1.3))
        hours = 7.4 + .7 * math.sin(day * .4)
        wake = s + timedelta(hours=hours)
        record('HKCategoryTypeIdentifierSleepAnalysis', s, wake,
               'HKCategoryValueSleepAnalysisAsleepCore')
        # 第 40—42 天构造一段多项信号同时偏离个人基线的虚构日子。
        episode = day in (40, 41, 42)
        for typ, val, unit, t in [
            ('RespiratoryRate', round(15 + .4*math.sin(day*.2) + (3 if episode else 0), 1), 'count/min', s+timedelta(hours=2)),
            ('AppleSleepingWristTemperature', round(34.6 + .08*math.sin(day*.5) + (.7 if episode else 0), 2), 'degC', s),
            ('AppleSleepingBreathingDisturbances', 18 if day == 22 else 4 + day % 3, 'count', s),
        ]:
            record('HKQuantityTypeIdentifier'+typ, t, t, val, unit)
        worn = range(9, 13) if day == 30 else [h for h in range(24) if h != 8]
        for h in worn:
            t = base + timedelta(hours=h, minutes=10)
            record('HKQuantityTypeIdentifierHeartRate', t, t, 60 + (h*7 + day) % 35, 'count/min')
        steps = 1200 if day == 30 else 1500 if day == 50 else 6000+(day*631)%5000
        for typ, val, unit in [
            ('RestingHeartRate', round(63 + 1.5*math.sin(day*.3) + (9 if episode else 0), 1), 'count/min'),
            ('HeartRateVariabilitySDNN', round(44+4*math.sin(day*.2) - (18 if episode else 0), 1), 'ms'),
            ('WalkingHeartRateAverage', round(104 - .1*day + 2*math.sin(day*.7), 1), 'count/min'),
            ('StepCount', steps, 'count'),
            ('AppleExerciseTime', 15+(day*7)%40, 'min'),
            ('ActiveEnergyBurned', 200+(day*17)%180, 'kcal'),
        ]:
            record('HKQuantityTypeIdentifier'+typ, base+timedelta(hours=9),
                   base+timedelta(hours=20), val, unit)
        if day % 7 == 3:
            t = base + timedelta(hours=18)
            record('HKQuantityTypeIdentifierVO2Max', t, t, round(40 + .04*day, 1), 'mL/min·kg')
        for h in (2,4,6):
            oxygen = .97 if (day+h)%3 else .96
            if day == 22 and h == 4: oxygen = .89
            t = base + timedelta(hours=h)
            record('HKQuantityTypeIdentifierOxygenSaturation', t, t, oxygen, '%')
        record('HKQuantityTypeIdentifierStepCount', base+timedelta(hours=9),
               base+timedelta(hours=20), 9000, 'count', 'Synthetic Phone')

        # 纯公式合成步态估算，不模拟任何个人或临床测试结果。
        walk = base + timedelta(hours=12)
        for typ, val, unit in [
            ('WalkingSpeed', round(1.2 + .1 * math.sin(day * .2), 2), 'm/s'),
            ('WalkingStepLength', round(65 + 4 * math.sin(day * .2), 1), 'cm'),
            ('WalkingDoubleSupportPercentage', .28 + .02 * math.sin(day * .3), '%'),
            ('WalkingAsymmetryPercentage', .02 + .01 * math.sin(day * .3), '%'),
            ('SixMinuteWalkTestDistance', round(460 + 20 * math.sin(day * .2)), 'm'),
        ]:
            record('HKQuantityTypeIdentifier' + typ, walk,
                   walk + timedelta(minutes=10), val, unit, 'Synthetic Phone')

        # 每日多条声音采样供日中位数展示；不代表 Leq 或听力剂量。
        for hour in (10, 16, 19):
            t = base + timedelta(hours=hour)
            for typ, val, source in [
                ('EnvironmentalAudioExposure', 52 + (day + hour) % 15,
                 'Synthetic Watch'),
                ('HeadphoneAudioExposure', 60 + (day * 2 + hour) % 12,
                 'Synthetic Phone'),
            ]:
                record('HKQuantityTypeIdentifier' + typ, t,
                       t + timedelta(minutes=5), val, 'dBASPL', source)
        # 稀疏 Watch 耳机记录：默认来源应优先覆盖更广的 Phone。
        if day % 7 == 0:
            record('HKQuantityTypeIdentifierHeadphoneAudioExposure', walk,
                   walk + timedelta(minutes=5), 64, 'dBASPL')

        record('HKQuantityTypeIdentifierAppleStandTime', base+timedelta(hours=9),
               base+timedelta(hours=20), 70 + day % 30, 'min')
        for hour in range(9, 18 + day % 3):
            t = base + timedelta(hours=hour)
            record('HKCategoryTypeIdentifierAppleStandHour', t,
                   t + timedelta(hours=1), 'HKCategoryValueAppleStandHourStood')
        # 同小时另一条非完全重复达标记录，不应增加达标小时数。
        record('HKCategoryTypeIdentifierAppleStandHour', base+timedelta(hours=9, minutes=5),
               base+timedelta(hours=9, minutes=55), 'HKCategoryValueAppleStandHourStood')
    ET.SubElement(root, 'Workout', workoutActivityType='HKWorkoutActivityTypeWalking',
                  startDate=stamp(start+timedelta(hours=12)),
                  endDate=stamp(start+timedelta(hours=12,minutes=30)), duration='30', durationUnit='min')
    return ET.tostring(root, encoding='unicode', xml_declaration=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--report', type=Path, help='Optional synthetic HTML preview destination')
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(make_xml(), encoding='utf-8')
    if args.report:
        from analyze import analyze
        from render import render_report
        data = analyze(args.output, 'UTC')
        data['meta']['synthetic'] = True
        data['quality'].insert(0, '完全虚构示例：所有数据由固定公式生成，不来自任何个人。')
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(render_report(data), encoding='utf-8')
    print('Created fictional fixture; no personal input was read.')
