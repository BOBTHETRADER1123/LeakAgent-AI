"""Conservative importer for the public BattLeDIM wide-format CSV files.

Keeps SCADA sensor series and leakage-demand series separate. It does not
invent pipe chainage, pair arbitrary sensors, or claim that a statistical
outlier is a confirmed leak.
"""
from __future__ import annotations
import csv
import io
import math
from collections import defaultdict
from statistics import median, pstdev


def parse_wide_csv(content: bytes, filename: str, data_kind: str, year: str):
    """Parse BattLeDIM wide CSVs, including semicolon-delimited decimal-comma files."""
    try:
        text = content.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValueError(f'{filename}: expected a UTF-8 CSV file') from exc
    if not text.strip():
        raise ValueError(f'{filename}: CSV file is empty')

    # BattLeDIM SCADA exports use semicolons between fields and commas as
    # decimal separators. Other ordinary comma-delimited CSVs remain supported.
    first_line = text.splitlines()[0]
    # Use the header row to choose the separator: decimal commas occur in data rows.
    if first_line.count(';') > first_line.count(','):
        delimiter = ';'
    elif first_line.count('\\t') > first_line.count(','):
        delimiter = '\\t'
    else:
        delimiter = ','

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError(f'{filename}: CSV header row is missing')
    fields = [str(x).strip() for x in reader.fieldnames]
    time_col = next((x for x in fields if x.lower() in {'timestamp','datetime','date_time','time','date'}), fields[0])
    sensor_cols = [x for x in fields if x != time_col]
    if not sensor_cols:
        raise ValueError(f'{filename}: no sensor columns found. Detected delimiter: {delimiter!r}; headers: {fields[:8]}')

    records = []
    skipped = 0
    for row in reader:
        stamp = (row.get(time_col) or '').strip()
        if not stamp:
            skipped += 1
            continue
        for sensor in sensor_cols:
            raw = (row.get(sensor) or '').strip()
            if raw == '':
                continue
            # Decimal comma is used in semicolon-delimited BattLeDIM exports.
            if delimiter == ';':
                raw = raw.replace(',', '.')
            try:
                value = float(raw)
            except ValueError:
                skipped += 1
                continue
            if not math.isfinite(value):
                skipped += 1
                continue
            records.append({'dataset':'BattLeDIM','year':str(year),'kind':data_kind,
                            'timestamp':stamp,'sensor_id':sensor,'value':value,
                            'source_file':filename})
    if not records:
        raise ValueError(f'{filename}: no numeric sensor observations found')
    return {'records':records,'time_column':time_col,'sensor_count':len(sensor_cols),
            'row_count':len({r['timestamp'] for r in records}),'skipped_values':skipped,
            'first_timestamp':min(r['timestamp'] for r in records),
            'last_timestamp':max(r['timestamp'] for r in records)}


def compare_sensor_baselines(training_records, evaluation_records, threshold=3.0):
    """Compare per-sensor 2019 values to 2018 distribution; screening only."""
    base=defaultdict(list)
    for r in training_records:
        base[(r['kind'],r['sensor_id'])].append(r['value'])
    out=[]
    for r in evaluation_records:
        vals=base.get((r['kind'],r['sensor_id']))
        if not vals:
            continue
        centre=median(vals)
        scale=pstdev(vals)
        if scale <= 1e-12:
            continue
        z=(r['value']-centre)/scale
        if abs(z) >= threshold:
            out.append({'kind':r['kind'],'sensor_id':r['sensor_id'],'timestamp':r['timestamp'],
                        'evaluation_value':r['value'],'historical_median':centre,
                        'historical_std_dev':scale,'z_score':round(z,3),
                        'screening_flag':'STATISTICAL ANOMALY — investigate, not confirmed leak'})
    return out


def extract_reference_leak_events(leakage_records, interval_minutes=5, epsilon=1e-9):
    """Extract contiguous positive leak-outflow periods from BattLeDIM reference series.

    Each leakage-reference sensor column represents a pipe/link series. A period is
    considered active only when its published leakage outflow is > epsilon. This is
    reference-data parsing, not model detection.
    """
    from datetime import datetime, timedelta
    grouped = defaultdict(list)
    for row in leakage_records:
        try:
            stamp = datetime.fromisoformat(str(row['timestamp']).strip())
            value = float(row['value'])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(value):
            grouped[(str(row.get('year', '')), str(row.get('sensor_id', '')))].append((stamp, value))

    events = []
    step = timedelta(minutes=interval_minutes)
    for (year, pipe_id), series in sorted(grouped.items()):
        series.sort(key=lambda item: item[0])
        active = []
        def finish():
            if not active:
                return
            vals = [v for _, v in active]
            events.append({
                'year': year, 'pipe_id': pipe_id,
                'start': active[0][0].strftime('%Y-%m-%d %H:%M:%S'),
                'end': active[-1][0].strftime('%Y-%m-%d %H:%M:%S'),
                'duration_minutes': len(active) * interval_minutes,
                'active_samples': len(active),
                'peak_leak_outflow_m3_h': round(max(vals), 6),
                'approx_leak_volume_m3': round(sum(vals) * interval_minutes / 60.0, 6),
                'reference': 'BattLeDIM leakage outflow series (> 0 m³/h)'
            })
        for stamp, value in series:
            if value > epsilon:
                if active and stamp - active[-1][0] != step:
                    finish()
                    active = []
                active.append((stamp, value))
            elif active:
                finish()
                active = []
        finish()
    return events
