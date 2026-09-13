"""Seal only this new evidence directory; never change historical manifests."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).parent
target = root / 'delivery-evidence-manifest.json'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
if target.exists():
    manifest = json.loads(target.read_text(encoding='utf-8'))
    expected = {x['file'] for x in manifest['files']}
    actual = {p.name for p in root.iterdir() if p.is_file() and p != target}
    assert actual == expected, ('scope mismatch', actual ^ expected)
    for entry in manifest['files']:
        p = root / entry['file']
        assert p.stat().st_size == entry['bytes'] and sha(p) == entry['sha256'], p
    print(f"NEW_EVIDENCE_INTEGRITY_OK: {len(expected)} files; does not imply overall WP-E PASS")
else:
    assert (root / 'review-delivery.md').exists(), 'Final independent review required before sealing'
    entries = [{'file':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(root.iterdir()) if p.is_file() and p != target]
    for p in root.glob('*.json'):
        obj = json.loads(p.read_text(encoding='utf-8-sig'))
        if isinstance(obj,dict) and 'images' in obj:
            for image in obj['images']:
                assert (root/image['file']).is_file(), (p,image)
    target.write_text(json.dumps({'created_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'All immediate files in this new evidence directory except this manifest itself. Original DOCX remain at paths bound in windows-matrix.json; historical26/49/38 scopes are not changed.',
        'files':entries},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"SEALED_NEW_EVIDENCE: {len(entries)} files")
