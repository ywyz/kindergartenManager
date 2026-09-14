"""Read-only portable checks. Integrity is not Word acceptance or WP-E PASS."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def check(root, rows, key='file'):
    for row in rows:
        p = root / row[key]
        if not p.is_file():
            raise SystemExit(f'MISSING: {p}')
        data = p.read_bytes()
        if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
            raise SystemExit(f'HASH_MISMATCH: {p}')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--materials', required=True, type=Path)
    args = parser.parse_args()
    new = ROOT / 'validation/wp-e-native-20260913'
    manifest = read(new / 'delivery-evidence-manifest.json')
    check(new, manifest['files'])
    actual = {p.name for p in new.iterdir() if p.is_file()}
    expected = {r['file'] for r in manifest['files']} | {'delivery-evidence-manifest.json'}
    if actual != expected:
        raise SystemExit(f'NEW_SCOPE_MISMATCH: {actual ^ expected}')
    print(f'NEW_EVIDENCE_INTEGRITY_OK: {len(manifest["files"])} files')
    portable = read(ROOT / 'evidence/WP-E-portable-materials-20260913.json')
    check(args.materials, portable['files'], key='path')
    actual_materials = {p.relative_to(args.materials).as_posix() for p in args.materials.rglob('*') if p.is_file()}
    if actual_materials != {r['path'] for r in portable['files']}:
        raise SystemExit('PORTABLE_MATERIAL_SCOPE_MISMATCH')
    print(f'PORTABLE_MATERIALS_OK: {len(portable["files"])} existing files')
    for name, total, expected_missing in [('wp-e-native-final-20260912',49,set()),
        ('wp-e-reduction-20260912',38,{'accepted-files/~$ve-holiday-long-dedup.docx','accepted-files/~$ve-long-dedup.docx','accepted-files/~$x-saturday-long-dedup.docx','accepted-files/~$x-sunday-long-dedup.docx'})]:
        folder = args.materials / name
        rows = read(folder/'evidence-manifest.json')['files']
        missing = {row['file'] for row in rows if not (folder/row['file']).is_file()}
        if len(rows) != total or missing != expected_missing:
            raise SystemExit(f'HISTORICAL_SCOPE_CHANGED: {name}: {missing}')
        check(folder, [r for r in rows if r['file'] not in missing])
        print(f'{name}: {total-len(missing)}/{total} MATCH; {len(missing)} historical MISSING retained')
    subprocess.run([sys.executable, str(ROOT/'validation/wp-e-handoff-20260912/verify_bundle.py')], check=True)
    print('HANDOFF_INTEGRITY_OK; candidate-only Word result retained; formal qualification and WP-E remain OPEN')

if __name__ == '__main__':
    main()
