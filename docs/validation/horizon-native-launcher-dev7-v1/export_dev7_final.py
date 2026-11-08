"""Freeze reviewed receipts only; exclude game resources, saves and executables."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil

QA = Path('D:/Codex-QA/TerraForged-Horizon')
BASE = QA / 'launcher-standard-v1/qa-dev7-default-view-v1'
DETAIL = BASE.parent / 'qa-dev7-fir-detail-v1'
REPO = Path('C:/Users/Main/Documents/Codex/TerraForged-Horizon-performance')
OUT = REPO / 'docs/validation/horizon-native-launcher-dev7-v1'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(p):
    return json.loads(p.read_text(encoding='utf-8'))

def save(p, value):
    p.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

j = read(BASE / 'report.json')
assert sha(BASE / 'report.json') == '282bf18e4971ff7478eff5eaed8a3a4aeb47881903111c61e43c7c185b1f478a'
assert j['status'] == 'passed-direct-installed-client-ui-save-qa-awaiting-image-review'
assert len(j['clientLaunches']) == 2 and all(r['exitCode'] == 0 for r in j['clientLaunches'])
assert len(j['cameraChecks']) == 40
assert all(c['yawModuloError'] <= .1 and c['pitchError'] <= .1 for c in j['cameraChecks'])
views = []
for v in j['visibilityChecks']:
    s = v['lastStatus']
    assert v['status'] == 'visible' and s['chunks'] >= 637 and s['render_distance'] == 12
    assert not s['pending_chunks'] and not s['pending_uploads'] and not any(s['streaming'].values())
    assert s['renderer']['resident_sections'] > 0 and s['renderer']['drawn_sections'] > 0
    views.append({'label': v['label'], 'elapsedSeconds': v['elapsedSeconds'], 'trackedColumns': s['chunks'], 'options': v['optionProof']})
assert len(views) == 6
assert j['finalIntegrity']['lockedFilesVerified'] == 30
assert j['finalIntegrity']['resourceFilesVerified'] == 28180
assert j['finalIntegrity']['preferencesNormalization']['allowedKnownOrderNormalization']
assert j['naturalSpawnState']['player']['health'] == 20 and j['naturalSpawnState']['player']['on_ground']
saved = []
for r in j['runs']:
    checks = r['crossRevisionSavedBiomeCompatibilityChecks']
    assert checks['status'] == 'passed-native-save-fixture-reader'
    chunks = [c for c in checks['chunkChecks'] if c['storedBiomeFingerprint'] is not None]
    assert all(c['storedBiomeFingerprint'] == c['nativeBiomeFingerprint'] for c in chunks)
    saved.append({'fullChunks': len(chunks), 'quartValues': sum(c['quartBiomes'] for c in chunks)})
assert [s['quartValues'] for s in saved] == [6144, 7680]
images = {}
def inspect_images(v):
    if isinstance(v, dict):
        if isinstance(v.get('path'), str) and v['path'].endswith('.png') and 'sha256' in v:
            p = Path(v['path'])
            assert sha(p) == v['sha256']
            images[p.name] = v['sha256']
        for x in v.values(): inspect_images(x)
    elif isinstance(v, list):
        for x in v: inspect_images(x)
inspect_images(j)
assert len(images) == 15
d = read(DETAIL / 'report.json')
assert d['status'] == 'passed-focused-fir-structure-view-awaiting-review' and d['client']['exitCode'] == 0
assert all(d[x] for x in ['baselineWorldUnchanged', 'baselineReportUnchanged', 'copiedArchivesUnchanged'])
assert d['roofBlock']['block'] == 'minecraft:white_wool_stairs'
assert sha(DETAIL / 'fir-structure-close.png') == d['screenshot']['sha256']
cushions = [o for o in d['lastTerrainStatus']['objects'] if o.get('kind') == 'minecraft:cushion']
assert len(cushions) == 3 and all(o.get('color') == 'magenta' for o in cushions)
static = read(QA / 'launcher-static-v1/qualification.json')
assert static['status'] == 'passed-static-launcher-qualification'

OUT.mkdir(parents=True, exist_ok=False)
copies = []
def copy(source, relative):
    assert source.suffix.lower() not in ['.exe', '.dll', '.mca', '.dat', '.hmod', '.hnmod']
    target = OUT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    assert source.read_bytes() == target.read_bytes()
    copies.append({'path': relative, 'source': str(source), 'sha256': sha(source), 'bytes': source.stat().st_size})

for name in ['report.json', 'plan.json', 'preflight.json', 'preparation-recovery.json', 'verify_installed_native_ui.py']:
    copy(BASE / name, name)
for name in ['client-coverage-proof.json', 'dev7-package-receipt.json', 'dev7-stage-result.json', 'environment.json', 'installed-horizon-native.json', 'installed-native-mods.json', 'launcher-qualification.json', 'native-build-receipt.json', 'old-save-probe-source.rs', 'preferences-original.txt', 'selected-classic-targets.json', 'static-launcher-build.json', 'world-preset.json']:
    copy(BASE / 'inputs' / name, 'inputs/' + name)
for p in (BASE / 'run').iterdir():
    if not p.name.startswith('ctl-') and (p.suffix in ['.png', '.log', '.json']):
        copy(p, 'run/' + p.name)
for name in ['report.json', 'preparation.json', 'capture_fir.py', 'fir-structure-close.png', 'game.log', 'smoke.json']:
    copy(DETAIL / name, 'fir-detail/' + name)
for p in (QA / 'launcher-static-v1').iterdir():
    if p.is_file() and p.suffix in ['.json', '.py', '.log']:
        copy(p, 'static-launcher/' + p.name)
for name in ['report.json', 'summary.json']:
    copy(QA / 'launcher-dev7-preparation-v1/launcher-run-v1' / name, 'preparation/' + name)

review = {
    'status': 'reviewed-passed-scoped-local-launcher-client-save-acceptance',
    'reviewedAtUtc': dt.datetime.now(dt.timezone.utc).isoformat(),
    'reviewer': 'Codex root; manual image inspection and independent receipt/hash assertions',
    'rawVerdictPreserved': j['status'], 'rawReportSha256': sha(BASE / 'report.json'),
    'hmodSha256': 'ab511d1e0daa3670061a91d3ce3900127cb702ddfb60603d2d5dee9fe59fb355',
    'clientSha256': '6a87351e5c85b83d728e55cfd6597cc90917b286a42fd16c8b819911fae6cd85',
    'staticLauncherSha256': '0d5f250705896eeded0e6800c03de961835bcd389f96d6ba908fe2bdb598f468',
    'clientExitCodes': [0, 0], 'cameraAssertions': 40, 'views': views,
    'saveReaderObservations': saved, 'saveReaderScope': j['oldSaveProbeScope'],
    'integrity': j['finalIntegrity'], 'imagesReviewed': images,
    'manualImageReview': 'All 15 unedited images inspected: healthy spawn, preset, HUD changes, three enabled mods, actual recipe result/crafted item, placed/reopened textured light block, all three target landscapes and reopened distant desert. Terrain coherent in these views. Long TerraForged Mods row clips warning text; name/version/ON remain readable.',
    'firDetail': {'rawReportSha256': sha(DETAIL / 'report.json'), 'imageSha256': d['screenshot']['sha256'], 'finding': 'White-wool stairs are textured; magenta patches are three magenta minecraft:cushion entities listed by the client, visible beside the structure.', 'cushions': cushions, 'baselineWorldAndReportUnchanged': True, 'exitCode': 0},
    'remainingLimits': j['notCovered'] + ['Arbitrary modpacks, dedicated server and other OS clients', 'Sustained background ring overlap, general FPS or controlled speedup', 'Historical unexplained exit cause remains unknown', 'Only manual whole-HMOD installation; GitHub native installer selects HNMOD', 'Prepared-resource base copied privately; fresh signed-in/public installation not qualified', 'No runtime old-save upgrade/migration qualification'],
    'excluded': ['Minecraft resource content', 'world/save files', 'executables', 'account/session files'],
    'copies': copies,
}
save(OUT / 'review.json', review)
copy(Path(__file__), 'export_dev7_final.py')
lines = [f'{sha(p)}  {p.relative_to(OUT).as_posix()}' for p in sorted(OUT.rglob('*')) if p.is_file()]
(OUT / 'SHA256SUMS').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(json.dumps({'status': review['status'], 'files': len(lines) + 1, 'images': len(images), 'reportSha256': review['rawReportSha256'], 'exportBytes': sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())}))
