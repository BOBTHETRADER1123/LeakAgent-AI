"""Run on an internet-connected computer. Python standard library only."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen, Request
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent / 'datasets'

def fetch(url, target, md5=None, kind=None):
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + '.part')
    try:
        print('Downloading:', target.name, flush=True)
        with urlopen(Request(url, headers={'User-Agent':'LeakLogicAcademic/1.0'}), timeout=120) as response, temp.open('wb') as out:
            shutil.copyfileobj(response, out)
        if md5:
            with temp.open('rb') as f:
                digest = hashlib.file_digest(f, 'md5').hexdigest()
            if digest.lower() != md5.lower():
                raise ValueError('Checksum mismatch')
        if kind == 'zip' and not zipfile.is_zipfile(temp):
            raise ValueError('Response is not a ZIP archive')
        if kind == 'rar':
            with temp.open('rb') as f:
                if not f.read(8).startswith(b'Rar!\x1a\x07'):
                    raise ValueError('Response is not a RAR archive')
        temp.replace(target)
        print('Saved:', target, flush=True)
    finally:
        temp.unlink(missing_ok=True)


def iit_bombay():
    fetch('https://zenodo.org/records/7162154/files/Supplementry%20information-2.rar?download=1', ROOT/'iit_bombay'/'Supplementry information-2.rar', md5='769380840daf14dd0e4f358394503554', kind='rar')


def borealis():
    api = 'https://borealisdata.ca/api/datasets/:persistentId/versions/1.0?persistentId=doi:10.5683/SP3/QA0YQM'
    with urlopen(Request(api, headers={'User-Agent':'LeakLogicAcademic/1.0'}), timeout=120) as response:
        metadata = json.load(response)['data']
    folder = ROOT/'delhi_bengaluru'
    folder.mkdir(exist_ok=True)
    (folder/'publisher_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    failures = []
    for item in metadata['files']:
        file = item['dataFile']
        file_id = file['id']
        # Numeric IDs prevent name collisions and unsafe paths.
        label = Path(file.get('originalFileName') or file['filename']).name
        target = folder/'original_files'/str(file_id)/label
        try:
            fetch(f'https://borealisdata.ca/api/access/datafile/{file_id}?format=original', target)
        except Exception as error:
            failures.append((str(file_id), str(error)))
    if failures:
        raise RuntimeError(f'{len(failures)} files failed: {failures}')

if __name__ == '__main__':
    failures = []
    for name, action in [('IIT Bombay', iit_bombay), ('Delhi-Bengaluru', borealis)]:
        try:
            action()
        except Exception as error:
            failures.append(name)
            print(name, 'FAILED:', error)
    if failures:
        print('Use the manual source links in README.md for:', ', '.join(failures))
        raise SystemExit(1)
    print('Downloads completed. Keep original publisher files unchanged.')
