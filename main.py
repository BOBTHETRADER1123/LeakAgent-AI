from contextlib import closing
import sqlite3
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from models import DiagnosisRequest
from agents import diagnose
from detection import analyze_rows
from detection_models import DetectionRequest, SpatialDetectionRequest
from spatial_detection import analyze_spatial_rows

ROOT=Path(__file__).resolve().parent
app=FastAPI(title='LeakLogic AI 4.4 - spatial pipeline leakage screening backend')

@app.get('/health')
def health():
    return {'status':'ok'}

@app.get('/nagpur')
def nagpur():
    import csv
    with (ROOT/'datasets/nagpur/measurements_si.csv').open(newline='',encoding='utf-8-sig') as f:
        return {'evidence':'published field measurements, no verified leak labels','rows':list(csv.DictReader(f))}

@app.post('/detect')
def detect_possible_leak(request: DetectionRequest):
    return analyze_rows(request.rows)

@app.post('/spatial-detect')
def spatial_detect(request: SpatialDetectionRequest):
    try:
        report = analyze_spatial_rows(request.rows, request.pipe_length_m)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    with closing(sqlite3.connect(ROOT/'incidents.db')) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS spatial_reports (id INTEGER PRIMARY KEY, created TEXT DEFAULT CURRENT_TIMESTAMP, pipe_length_m REAL, report TEXT)')
        db.execute('INSERT INTO spatial_reports(pipe_length_m, report) VALUES (?, ?)', (request.pipe_length_m, json.dumps(report)))
    return report

@app.post('/diagnose')
def diagnostic(request:DiagnosisRequest):
    report=diagnose(request.readings)
    with closing(sqlite3.connect(ROOT/'incidents.db')) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY, created TEXT DEFAULT CURRENT_TIMESTAMP, report TEXT)')
        db.execute('INSERT INTO reports(report) VALUES (?)',(json.dumps(report),))
    return report
