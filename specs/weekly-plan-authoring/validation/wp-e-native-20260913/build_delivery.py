import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

O = Path(__file__).parent
R = Path('C:/Users/admin/.codex/visualizations/2026/09/12/01a0937c-3f64-7ce2-98f9-fecd1934901c')
W = R / 'wp-e-windows-84f189f'
MAIN = Path('C:/Users/admin/code/kindergartenManager')
SHA = '0bded3377c01956833bcbb6cd306f9a7f5d924e1'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name, obj):
    (O/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def git(root, *args):
    p = subprocess.run(['git','-C',str(root),*args], capture_output=True, text=True, encoding='utf-8')
    return {'exit':p.returncode, 'stdout':p.stdout.strip(), 'stderr':p.stderr.strip()}

now = datetime.now(timezone.utc).isoformat()
mfile = R/'wp-e-header-week-20260912/candidate-manifest-final.json'
m = read(mfile)
env = read(O/'environment.json')
checks = []
for name,rel,expected in [
    ('candidate manifest',mfile,'8570185e52b0a9ca50ea298556ad6607ebc9014e66cc01f26716ffc4c76e7936'),
    ('renderer',W/'app/integration/word_export/shared_weekly_word.py',m['generator_sha256']),
    ('seed',W/'templates/weekplan.docx',m['seed_sha256'])]:
    actual=digest(rel)
    checks.append({'name':name,'path':str(rel),'expected':expected,'actual':actual,'status':'MATCH' if actual==expected else 'MISMATCH'})
for case in m['cases']:
    for ext,key in [('body.json','body_sha256'),('docx','docx_sha256')]:
        p=mfile.parent/'candidates-final'/f"{case['id']}.{ext}"
        actual=digest(p)
        checks.append({'name':case['id'],'path':str(p),'expected':case[key],'actual':actual,'status':'MATCH' if actual==case[key] else 'MISMATCH'})
packages=[]
for dirname in ['wp-e-native-final-20260912','wp-e-reduction-20260912']:
    p=R/dirname/'evidence-manifest.json'
    rows=[]
    for entry in read(p)['files']:
        source=p.parent/entry['file']
        actual=digest(source) if source.exists() else None
        rows.append({**entry,'path':str(source),'actual_sha256':actual,'status':'MISSING' if actual is None else 'MATCH' if actual==entry['sha256'] else 'MISMATCH'})
    packages.append({'manifest':str(p),'manifest_sha256':digest(p),'original_scope':len(rows),
                     'counts':{s:sum(x['status']==s for x in rows) for s in ['MATCH','MISSING','MISMATCH']},'files':rows})
bundle=W/'specs/weekly-plan-authoring/validation/wp-e-handoff-20260912/verify_bundle.py'
import sys
verified=subprocess.run([sys.executable,str(bundle)],cwd=W,capture_output=True,text=True,encoding='utf-8')
write('integrity-final.json', {'created_utc':now,'checks':checks,'external_packages':packages,
    'bundle':{'path':str(bundle),'exit':verified.returncode,'stdout':verified.stdout.strip(),'stderr':verified.stderr.strip(),
              'scope_note':'26 original bundle files only; excludes new DOCX/screenshots; neither Word PASS nor WP-E PASS'},
    'prior_report_note':'integrity-inputs.json retained unchanged; its 99 existing-file rows omit four missing transient Word lock files. This report explicitly retains all 38 reduction manifest entries.'})
write('git-final.json', {'created_utc':now,'main':{a:git(MAIN,*b) for a,b in [('head',['rev-parse','HEAD']),('branch',['branch','--show-current']),('status',['status','--short'])]},
    'worktree':{a:git(W,*b) for a,b in [('head',['rev-parse','HEAD']),('branch',['branch','--show-current']),('status',['status','--short']),('product_diff',['diff','--name-only',SHA,'HEAD'])]},
    'remote_note':'No fetch/push performed; local commits are not assumed present remotely.'})
normal=[]
for case in m['cases']:
    if case['id'] not in ['five-normal','five-holiday','six-sunday-normal','six-saturday-normal']: continue
    ident=case['id']
    normal.append({'id':ident,'tested_code_sha':SHA,'client':env,'renderer_sha256':m['generator_sha256'],'seed_sha256':m['seed_sha256'],
        'input':str(mfile.parent/'candidates-final'/f'{ident}.body.json'),'input_sha256':case['body_sha256'],
        'output_original':str(mfile.parent/'candidates-final'/f'{ident}.docx'),'output_sha256':case['docx_sha256'],
        'original_unchanged':all(x['status']=='MATCH' for x in checks if x['name']==ident),
        'native_page_count':1,'native_a4_portrait':'PASS','body_font':'PASS: 宋体12pt常规','title_font':'PASS: 宋体16pt加粗',
        'visible_text_paragraph_spacing':'PASS: fixed20pt via per-file grouped native selections',
        'blank_and_merged_structure':'Not asserted to be uniformly20pt; see report selection scope and mixed-spacing qualification',
        'content_counts_dates_whitespace_holidays':'PASS','all_page_text_and_boundaries':'PASS',
        'result':'PASS_CANDIDATE_FORMAT_CURRENT_SHA_CLIENT_ONLY',
        'native_evidence':[p.name for p in sorted(O.glob(ident+'*.json')) if 'diagnostic' not in p.name],
        'independent_reviews':[p.name for p in sorted(O.glob('review-'+ident+'*.md'))]})
long_original=[{**{k:v for k,v in c.items() if k!='native_status'},
    'candidate_manifest_native_status':c['native_status'],
    'native_status':'FAIL_SINGLE_PAGE_HISTORICAL','this_batch_native_observation':'NOT_RUN',
    'native_page_count':2,'single_page':'FAIL','observation_date':'2026-09-12; historical observation retained, not re-observed this batch',
    'full_format':'NOT_RUN; no inherited PASS'} for c in m['cases'] if 'long' in c['id']]
dedup=read(R/'wp-e-reduction-20260912/native-recheck.json')
write('windows-matrix.json',{'created_utc':now,'scope':'Candidate format acceptance only; formal released qualification not verified',
    'normal_cases':normal,'original_long_cases':long_original,'original_long_evidence':str(R/'wp-e-native-final-20260912/native-matrix.json'),
    'dedup_long_cases':dedup['cases'],'dedup_evidence':str(R/'wp-e-reduction-20260912/native-recheck.json'),
    'dedup_client_reference':dedup['environment_reference'],'dedup_observation_date':'2026-09-12; retained, not new observation',
    'other_states':{'new_adopted_single_page_revision':'NOT_RUN; no new proposal adopted or saved',
    'historical_three_long':'Retain historical two-page FAIL; not re-observed', 'compact_synthetic':'Retain historical candidate status; not promoted to revision success',
    'application_refuses_download_when_cannot_converge':'NOT_RUN; later page acceptance',
    'released_catalog_binding':'NOT_VERIFIED; later qualification binding gate',
    'ubuntu_pages_real_model_database_catalog_ci_oci_migrations_deployment':'NOT_RUN this batch; later WP-E gates',
    'WP-C_historical_native_dual_RED_four_types':'UNMET; user-authorized local WP-E continuation unchanged',
    'WP-E':'OPEN','WP-F':'NOT_RUN'}})
print(json.dumps({'checks':len(checks),'bad_checks':[x for x in checks if x['status']!='MATCH'],
                  'packages':[(p['original_scope'],p['counts']) for p in packages], 'bundle':verified.stdout.strip()},ensure_ascii=False))
