"""Package the already-qualified source HMOD and static launcher, without game data."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path('D:/Codex-QA/TerraForged-Horizon/native-dev7-release-v1')
REPO = Path('C:/Users/Main/Documents/Codex/TerraForged-Horizon-performance')
PACKAGE = 'terraforged-horizon-26.3-0.1.0-native.dev7.hmod'
ZIP = 'terraforged-horizon-launcher-windows-x64-native.dev7.zip'
HMOD_SHA = 'ab511d1e0daa3670061a91d3ce3900127cb702ddfb60603d2d5dee9fe59fb355'
LAUNCHER_SHA = '0d5f250705896eeded0e6800c03de961835bcd389f96d6ba908fe2bdb598f468'

def digest(b): return hashlib.sha256(b).hexdigest()

assert digest((ROOT/PACKAGE).read_bytes()) == HMOD_SHA
launcher = ROOT/'launcher-windows-x64'
assert digest((launcher/'horizon-launcher.exe').read_bytes()) == LAUNCHER_SHA
assert (launcher/'Start-TerraForged-Horizon.cmd').read_text().splitlines() == [
    '@echo off', 'setlocal', 'set "HORIZON_LAUNCHER_NO_SELF_UPDATE=1"', 'start "" "%~dp0horizon-launcher.exe" %*']
assert (launcher/'LICENSE').exists() and (launcher/'THIRD_PARTY_NOTICES.md').exists()
files = sorted(p for p in launcher.rglob('*') if p.is_file())
assert not any(p.is_symlink() for p in files)
assert sum(p.suffix == '.exe' for p in files) == 1
assert not any(p.suffix.lower() in ['.dll', '.mca', '.dat', '.jar', '.json'] for p in files)
archive = ROOT/ZIP
assert not archive.exists(), 'Refusing to overwrite a prepared artifact'
entries = []
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in files:
        name = 'TerraForged-Horizon-Launcher/' + p.relative_to(launcher).as_posix()
        data = p.read_bytes()
        info = zipfile.ZipInfo(name, (2026, 11, 8, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        z.writestr(info, data)
        entries.append({'path': name, 'bytes': len(data), 'sha256': digest(data)})
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert z.namelist() == [e['path'] for e in entries]
    for entry in entries:
        assert digest(z.read(entry['path'])) == entry['sha256']
assets = [{'name': name, 'bytes': (ROOT/name).stat().st_size, 'sha256': digest((ROOT/name).read_bytes())} for name in [PACKAGE, ZIP]]
(ROOT/'SHA256SUMS').write_text(''.join(a['sha256']+'  '+a['name']+'\n' for a in assets), encoding='utf-8')
assets.append({'name': 'SHA256SUMS', 'bytes': (ROOT/'SHA256SUMS').stat().st_size, 'sha256': digest((ROOT/'SHA256SUMS').read_bytes())})
receipt = {
    'status': 'prepared-and-byte-verified-not-yet-published', 'tag': 'v0.1.0-native.dev7',
    'nativeSourceCommit': 'ed818ecc0371e1627192e1abdccb0a744f51f890',
    'hostSourceCommit': 'f43eebfc04b73f0c2bbf5048f7a3ab36c240f21d',
    'hostMergeCommit': '948904435cdf33b3bcbf052de55bbfeea128cc2e',
    'mixinsCommit': 'e8cd0aa38cffef49cb2e088ef716baa107148c02',
    'assets': assets, 'launcherZipEntries': entries,
    'selfUpdatePolicy': 'Use the included CMD wrapper to disable upstream self-update for this fork process.',
    'excluded': ['Minecraft resources', 'compiled game client', 'saves/worlds', 'accounts/sessions'],
    'qualification': 'Exact HMOD + launcher hashes qualified locally; ZIP extraction checked byte-for-byte. GUI/authenticated Play and fresh public install remain untested.'
}
(ROOT/'package-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
out = REPO/'docs/validation/horizon-native-dev7-release-preparation.json'
out.write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'status': receipt['status'], 'assets': assets, 'zipEntries': len(entries)}))
