"""Spatial screening between pipeline monitoring stations.

This module analyzes measured intervals between adjacent stations. It stores
millimetre-based chainage coordinates as integers, but never fabricates a
measurement at every millimetre. Actual localization is bounded by sensor
spacing and measurement quality.
"""
from collections import defaultdict
from math import hypot, isfinite, floor, ceil

REQUIRED = {
    'pipe_id', 'cycle_id', 'timestamp', 'station_id', 'distance_m',
    'flow_l_s', 'meter_sigma_l_s', 'known_withdrawal_l_s',
    'full_pipe_flag', 'stable_window_verified'
}


def _bool(v):
    return v if isinstance(v, bool) else str(v).strip().lower() in {'1','true','yes','y'}


def _num(row, key, default=0.0):
    try:
        value = float(row.get(key, default) or default)
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be numeric")
    if not isfinite(value):
        raise ValueError(f"{key} must be finite")
    return value


def analyze_spatial_rows(rows, pipe_length_m=None):
    if not rows:
        raise ValueError('Upload at least two monitoring-station rows.')
    missing = REQUIRED - set(rows[0])
    if missing:
        raise ValueError('Missing required CSV columns: ' + ', '.join(sorted(missing)))
    grouped = defaultdict(list)
    pipes = defaultdict(list)
    for idx, row in enumerate(rows, 2):
        pipe = str(row.get('pipe_id','')).strip()
        cycle = str(row.get('cycle_id','')).strip()
        stamp = str(row.get('timestamp','')).strip()
        station = str(row.get('station_id','')).strip()
        if not all((pipe, cycle, stamp, station)):
            raise ValueError(f'CSV row {idx}: pipe_id, cycle_id, timestamp and station_id are required')
        distance = _num(row,'distance_m')
        flow = _num(row,'flow_l_s')
        sigma = _num(row,'meter_sigma_l_s')
        withdrawal = _num(row,'known_withdrawal_l_s')
        if distance < 0 or flow < 0 or sigma <= 0 or withdrawal < 0:
            raise ValueError(f'CSV row {idx}: distance/flow/withdrawal must be non-negative and meter uncertainty positive')
        if pipe_length_m is not None and distance > float(pipe_length_m):
            raise ValueError(f'CSV row {idx}: station lies beyond declared pipe length')
        item = dict(pipe_id=pipe, cycle_id=cycle, timestamp=stamp, station_id=station,
                    distance_m=distance, flow_l_s=flow, meter_sigma_l_s=sigma,
                    known_withdrawal_l_s=withdrawal,
                    full_pipe=_bool(row.get('full_pipe_flag')), stable=_bool(row.get('stable_window_verified')))
        grouped[(pipe,cycle,stamp)].append(item)
        pipes[pipe].append(distance)

    interval_rows = []
    for (pipe, cycle, stamp), stations in sorted(grouped.items()):
        stations.sort(key=lambda x:x['distance_m'])
        for left, right in zip(stations, stations[1:]):
            if right['distance_m'] <= left['distance_m']:
                raise ValueError(f"Pipe {pipe}, cycle {cycle}: station distances must be unique and increasing")
            eligible = left['full_pipe'] and right['full_pipe'] and left['stable'] and right['stable']
            residual = left['flow_l_s'] - right['flow_l_s'] - right['known_withdrawal_l_s']
            sigma = hypot(left['meter_sigma_l_s'], right['meter_sigma_l_s'])
            z = residual / sigma
            flagged = eligible and z > 3.0
            start_mm = int(round(left['distance_m'] * 1000))
            end_mm = int(round(right['distance_m'] * 1000))
            interval_rows.append({
                'pipe_id':pipe,'cycle_id':cycle,'timestamp':stamp,
                'upstream_station':left['station_id'],'downstream_station':right['station_id'],
                'start_m':left['distance_m'],'end_m':right['distance_m'],
                'start_mm':start_mm,'end_mm':end_mm,'interval_length_m':round(right['distance_m']-left['distance_m'],3),
                'upstream_flow_l_s':left['flow_l_s'],'downstream_flow_l_s':right['flow_l_s'],
                'known_withdrawal_l_s':right['known_withdrawal_l_s'],
                'unexplained_flow_l_s':round(residual,6),'combined_meter_sigma_l_s':round(sigma,6),
                'z_score':round(z,3),'eligible':eligible,'possible_leak_signal':bool(flagged),
                'location_resolution_limit_m':round(right['distance_m']-left['distance_m'],3),
                'location_statement':f"Possible leak somewhere between {left['distance_m']:.3f} m and {right['distance_m']:.3f} m; exact position not resolved by these two stations."
            })

    by_interval = defaultdict(list)
    for r in interval_rows:
        if r['eligible']:
            key=(r['pipe_id'],r['upstream_station'],r['downstream_station'],r['start_mm'],r['end_mm'])
            by_interval[key].append(r)
    summaries=[]
    for key, vals in sorted(by_interval.items()):
        flagged_cycles=sorted({v['cycle_id'] for v in vals if v['possible_leak_signal']})
        summaries.append({
            'pipe_id':key[0],'upstream_station':key[1],'downstream_station':key[2],
            'start_m':key[3]/1000,'end_m':key[4]/1000,'start_mm':key[3],'end_mm':key[4],
            'sensor_interval_m':(key[4]-key[3])/1000,'flagged_cycles':len(flagged_cycles),
            'flagged_cycle_ids':flagged_cycles,
            'status':'POSSIBLE LEAK — inspect this interval' if len(flagged_cycles)>=2 else 'SINGLE-CYCLE ANOMALY — repeat measurement' if flagged_cycles else 'NO QUALIFYING SIGNAL',
            'estimated_unexplained_flow_l_s':round(sum(v['unexplained_flow_l_s'] for v in vals if v['possible_leak_signal'])/len([v for v in vals if v['possible_leak_signal']]),6) if flagged_cycles else None,
            'actual_localization_resolution_m':(key[4]-key[3])/1000,
            'millimetre_coordinate_reference':'Coordinates are encoded in integer millimetres; this is not proof of 1 mm physical detection accuracy.'
        })
    total_length = float(pipe_length_m) if pipe_length_m is not None else max((max(v)-min(v) for v in pipes.values() if v), default=0.0)
    return {
        'status':'SPATIAL SCREENING COMPLETE', 'pipe_length_m':total_length,
        'monitoring_stations':sum(len(v) for v in grouped.values()),
        'measurement_groups':len(grouped),'intervals_analyzed':len(interval_rows),
        'possible_leak_intervals':sum(1 for x in summaries if x['flagged_cycles']>=2),
        'coordinate_system':'chainage from pipe start; integer millimetre coordinates',
        'requested_example_scale': '200 km = 200,000,000,000 millimetre coordinate positions; not materialized as rows.',
        'interval_results':interval_rows,'location_summary':summaries,
        'limitations':[
            'A leak can only be bracketed between monitoring stations with this flow-balance method.',
            'Actual localization resolution is limited by sensor spacing, sensor accuracy, timing synchronization and hydraulic conditions.',
            '1 mm coordinate representation does not mean 1 mm detection accuracy.',
            'To narrow a flagged interval, add intermediate flow/pressure monitoring stations or use a validated transient/acoustic distributed sensing method.',
            'Unmetered withdrawals, storage changes, bypasses, pump changes, air and meter bias can mimic leakage.',
            'A possible leak signal is not confirmation; inspect and verify in the field.'
        ]
    }
