"""Small local RAG library: SQLite + cosine similarity. No FAISS."""
import csv
import hashlib
import json
import math
import sqlite3
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
DB = ROOT / 'rag_index.db'


def chunks(text, size=900, overlap=150):
    text = ' '.join(text.split())
    for start in range(0, len(text), size - overlap):
        part = text[start:start + size]
        if part:
            yield part
        if start + size >= len(text):
            break


def get_embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL, device='cpu', trust_remote_code=False)


def cosine(a, b):
    if len(a) != len(b):
        raise ValueError('Embedding dimensions differ; rebuild the index.')
    norm = math.sqrt(sum(v*v for v in a) * sum(v*v for v in b))
    return sum(x*y for x, y in zip(a, b)) / norm if norm else 0.0


class Library:
    def __init__(self, embedder=None, path=DB):
        self.embedder = embedder
        self.path = path
        with closing(sqlite3.connect(path)) as db, db:
            db.execute('''CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY, title TEXT, location TEXT, kind TEXT,
                source_url TEXT, text TEXT, model TEXT, vector TEXT)''')

    def add(self, title, data, kind, source_url=''):
        # data is a list of (page/row locator, text) pairs.
        rows = []
        for location, text in data:
            for part in chunks(text):
                uid = hashlib.sha256(json.dumps([title, location, kind, source_url, part, MODEL]).encode()).hexdigest()
                rows.append((uid, title, location, kind, source_url, part, MODEL))
        with closing(sqlite3.connect(self.path)) as db, db:
            existing = {r[0] for r in db.execute('SELECT id FROM chunks')}
            rows = [r for r in rows if r[0] not in existing]
            if not rows:
                return 0
            for start in range(0, len(rows), 32):
                batch = rows[start:start+32]
                vectors = self.embedder.encode([r[5] for r in batch], normalize_embeddings=True)
                db.executemany('INSERT OR IGNORE INTO chunks VALUES (?,?,?,?,?,?,?,?)',
                               [(*r, json.dumps([float(x) for x in v])) for r,v in zip(batch,vectors)])
        return len(rows)

    def add_pdf(self, raw, title):
        import fitz
        if len(raw) > 100*1024*1024:
            raise ValueError('PDF exceeds 100 MB.')
        with fitz.open(stream=raw, filetype='pdf') as pdf:
            if pdf.needs_pass:
                raise ValueError('Use an unlocked PDF.')
            data = [(f'page {i}', p.get_text(sort=True)) for i,p in enumerate(pdf,1)]
        skipped = [loc for loc,text in data if len(text.strip()) < 25]
        data = [(loc,text) for loc,text in data if len(text.strip()) >= 25]
        if not data:
            raise ValueError('No searchable text. OCR your authorized PDF first.')
        return self.add(title,data,'document / not field evidence'), skipped

    def sources(self):
        with closing(sqlite3.connect(self.path)) as db:
            return db.execute('SELECT title, kind, COUNT(*) FROM chunks GROUP BY title,kind').fetchall()

    def search(self, query, k=5):
        q = [float(x) for x in self.embedder.encode([query],normalize_embeddings=True)[0]]
        results = []
        with closing(sqlite3.connect(self.path)) as db:
            for title,loc,kind,url,text,v in db.execute('SELECT title,location,kind,source_url,text,vector FROM chunks WHERE model=?',(MODEL,)):
                results.append(dict(title=title,location=loc,kind=kind,url=url,text=text,score=cosine(q,json.loads(v))))
        return sorted(results,key=lambda r:r['score'],reverse=True)[:k]


def seed(lib):
    total = 0
    for path in sorted((ROOT/'documents').rglob('*.pdf')):
        count, skipped = lib.add_pdf(path.read_bytes(),path.relative_to(ROOT/'documents').as_posix())
        total += count
        print(path.name, count, 'new chunks; skipped', skipped)
    for rel, kind, url in [('datasets/nagpur/README.md','source notes','https://doi.org/10.1007/s13201-018-0672-3'),('datasets/DATA_GUIDE.md','source guide',''),('sources.csv','source manifest / not raw observations','')]:
        path=ROOT/rel
        total+=lib.add(rel,[('file',path.read_text(encoding='utf-8'))],kind,url)
    path=ROOT/'datasets/nagpur/measurements_si.csv'
    with path.open(encoding='utf-8-sig',newline='') as f:
        for i,row in enumerate(csv.DictReader(f),2):
            text='Nagpur published hourly measurement (not leak-labelled). '+ '; '.join(f'{k}: {v or "unknown"}' for k,v in row.items())
            total+=lib.add('Nagpur Table 1 normalized measurements',[(f'CSV row {i}',text)],'published field measurement; unknown leak status','https://doi.org/10.1007/s13201-018-0672-3')
    return total
