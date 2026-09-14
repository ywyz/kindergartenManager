"""Measure unchanged synthetic fixtures with installed Windows LibreOffice."""
import hashlib
import json
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUNDLE = ROOT.parent / 'wp-a-simsun-20260909/samples'
OFFICE = Path('C:/Program Files/LibreOffice/program/soffice.com')
POPPLER = Path('C:/Users/yw980/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin')
PROFILE = Path(tempfile.mkdtemp(prefix='wp-a-lo-validation-'))
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def now():
    return datetime.now(UTC).isoformat()
def run(args):
    p = subprocess.run([str(a) for a in args], capture_output=True, timeout=90, check=False)
    record = {'command': [str(a) for a in args], 'exit_code': p.returncode,
              'stdout': p.stdout.decode('utf-8', errors='replace'),
              'stderr': p.stderr.decode('utf-8', errors='replace')}
    if p.returncode:
        raise RuntimeError(record)
    return record

record = {'started_at_utc': now(), 'platform': 'Windows',
          'profile': str(PROFILE), 'mode': 'headless PDF export, no native preview observation',
          'version': run([OFFICE, '--version']),
          'version_ini': (OFFICE.parent / 'version.ini').read_text(),
          'soffice_bin_sha256': sha(OFFICE.parent / 'soffice.bin'), 'samples': []}
(ROOT / 'run.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
for source in sorted(BUNDLE.glob('*.docx')):
    out = ROOT / source.stem
    out.mkdir()
    before = sha(source)
    sample = {'sample': source.name, 'started_at_utc': now(), 'input_sha256': before}
    sample['conversion'] = run([OFFICE, '-env:UserInstallation=' + PROFILE.as_uri(),
        '--headless', '--convert-to', 'pdf:writer_pdf_Export', '--outdir', out, source])
    pdf = out / (source.stem + '.pdf')
    if not pdf.is_file():
        raise RuntimeError('No output PDF: ' + source.name)
    sample['pdf_sha256'] = sha(pdf)
    sample['pdfinfo'] = run([POPPLER / 'pdfinfo.exe', pdf])
    sample['render'] = run([POPPLER / 'pdftoppm.exe', '-r', '144', '-png', pdf, out / 'page'])
    sample['input_sha256_after'] = sha(source)
    assert before == sample['input_sha256_after'], source.name
    sample['finished_at_utc'] = now()
    record['samples'].append(sample)
    (ROOT / 'run.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(source.name, sample['pdfinfo']['stdout'].split('Pages:')[-1].splitlines()[0], flush=True)
record['finished_at_utc'] = now()
(ROOT / 'run.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
