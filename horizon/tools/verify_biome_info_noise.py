"""Compare the host's unrounded biome-info noise with real Java 26.2 observations."""
from __future__ import annotations
import argparse,datetime as dt,gzip,hashlib,json,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('horizon','report'):p.add_argument('--'+name,required=True,type=Path)
    a=p.parse_args();host=a.horizon.resolve()
    if a.report.exists():p.error('Refusing to replace evidence')
    fixture=ROOT/'horizon/tests/fixtures/marsh-sampler-v1';metadata=json.loads((fixture/'metadata.json').read_text(encoding='utf-8'));inputs=fixture/'inputs.tsv';values=fixture/'values.tsv.gz'
    if sha(inputs)!=metadata['inputsSha256'] or sha(values)!=metadata['fixtureSha256']:raise ValueError('Frozen inputs changed')
    raw=gzip.decompress(values.read_bytes())
    if hashlib.sha256(raw).hexdigest()!=metadata['uncompressedValuesSha256']:raise ValueError('Reference values changed')
    expected=b'\n'.join(line for line in raw.splitlines() if line.startswith((b'info/',b'positive/')))+b'\n'
    work=ROOT/'build/qa/horizon'/a.report.stem;work.mkdir(parents=True,exist_ok=False);shutil.copy2(Path(__file__),work/'verifier-source.py')
    names=['crates/horizon-core/src/noise/simplex.rs','crates/horizon-world/src/worldgen/biome_temperature.rs','crates/horizon-world/examples/native_biome_info_noise.rs'];source={n:sha(host/n) for n in names}
    env=dict(os.environ,CARGO_BUILD_JOBS='4',CARGO_NET_OFFLINE='true');target=host.parent/'biome-info-checks-target';env['CARGO_TARGET_DIR']=str(target);profiles=[]
    for profile in ('debug','release'):
        command=['cargo','+stable','build','--offline','--locked','--manifest-path',str(host/'Cargo.toml'),'-p','horizon-world','--example','native_biome_info_noise']+(['--release'] if profile=='release' else [])
        result=subprocess.run(command,cwd=host,env=env,capture_output=True,text=True,timeout=600);(work/(profile+'-build.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
        if result.returncode:raise RuntimeError('Host observation example failed to build; preserved log')
        exe=target/profile/'examples'/('native_biome_info_noise'+('.exe' if os.name=='nt' else ''));result=subprocess.run([str(exe),str(inputs)],cwd=work,env=env,capture_output=True,timeout=60);actual=work/(profile+'-values.tsv');actual.write_bytes(result.stdout);(work/(profile+'-stderr.log')).write_bytes(result.stderr)
        wanted=expected.splitlines();observed=result.stdout.splitlines();diff=[{'row':i,'java':x.decode(),'native':y.decode()} for i,(x,y) in enumerate(zip(wanted,observed)) if x!=y]
        if len(wanted)!=len(observed):diff.insert(0,{'expectedCount':len(wanted),'actualCount':len(observed)})
        profiles.append({'profile':profile,'exitCode':result.returncode,'records':len(observed),'differenceCount':len(diff),'firstDifferences':diff[:8],'executableSha256':sha(exe),'outputSha256':sha(actual),'allJavaObservationsMatch':not diff and result.returncode==0})
    passed=all(x['allJavaObservationsMatch'] for x in profiles) and all(sha(host/n)==digest for n,digest in source.items())
    report={'schemaVersion':1,'status':'passed-independent-host-biome-info-noise' if passed else 'failed','completedAtUtc':dt.datetime.now(dt.timezone.utc).isoformat(),'hostBaseRevision':subprocess.check_output(['git','-C',str(host),'rev-parse','HEAD'],text=True).strip(),'hostSourceSha256':source,'referenceMetadataSha256':sha(fixture/'metadata.json'),'verifierSourceSha256':sha(work/'verifier-source.py'),'profiles':profiles,'scope':'Unrounded biome-info noise at 20,449 dense/negative/distant block coordinates and its positive/no-positive classification; 40,898 Java observations per profile.','gameFilesReadOrDownloaded':False,'notCovered':['Marsh material graph (qualified separately)','Full marsh block placement','All vanilla temperature or precipitation behavior','Game visuals/performance/modpack compatibility']}
    a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(report,indent=2));return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
