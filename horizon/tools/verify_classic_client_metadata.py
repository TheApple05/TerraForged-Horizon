"""Check renderer biome registration and real enabled-world-pack metadata."""
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','resources','report'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();workspace=a.workspace.resolve();resources=a.resources.resolve()
    if not workspace.is_relative_to((ROOT/'build/qa/horizon').resolve()) or workspace.name!='staged':p.error('Fresh full UI stage required')
    if a.report.exists():p.error('Refusing to replace evidence')
    stage_file=workspace.parent/'stage-result.json';stage=json.loads(stage_file.read_text(encoding='utf-8'))
    if not stage.get('worldPresetUiIncluded'):p.error('World UI integration required')
    for name,digest in stage['inputFiles'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Restage changed source '+name)
    work=workspace.parent/a.report.stem;work.mkdir(exist_ok=False);shutil.copy2(Path(__file__),work/'verifier-source.py')
    source=ROOT/'horizon/tests/rust/classic_client_metadata_probe.rs';dest=workspace/'crates/horizon-client/qa/terraforged_classic_client_metadata.rs'
    dest.parent.mkdir(exist_ok=True)
    if dest.exists():raise ValueError('Fresh metadata probe destination required')
    shutil.copy2(source,dest)
    manifest=workspace/'crates/horizon-client/Cargo.toml';before_manifest=sha(manifest)
    addition='\n[[bin]]\nname = "terraforged_classic_client_metadata"\npath = "qa/terraforged_classic_client_metadata.rs"\n'
    manifest.write_text(manifest.read_text(encoding='utf-8')+addition,encoding='utf-8',newline='\n')
    files=[resources/'facts.json']+sorted((resources/'worldgen').rglob('*.json'));before={str(f.relative_to(resources)):sha(f) for f in files}
    env=dict(os.environ,CARGO_NET_OFFLINE='true',CARGO_BUILD_JOBS='4',HORIZON_TELEMETRY_URL='off',HORIZON_NO_AUDIO='1',HORIZON_NO_DISCORD='1',HORIZON_LAUNCHER_NO_SELF_UPDATE='1');env.pop('CARGO_TARGET_DIR',None)
    for name in ('HORIZON_HOME','HORIZON_LAUNCHER_HOME','XDG_DATA_HOME','XDG_CONFIG_HOME','HORIZON_LAUNCHER_TRASH','HORIZON_LAUNCHER_CLIPBOARD','HORIZON_LAUNCHER_DESKTOP'):
        directory=work/'homes'/name.lower();directory.mkdir(parents=True);env[name]=str(directory.resolve())
    build=subprocess.run(['cargo','+stable','build','--offline','--locked','--profile','fast','--manifest-path',str(workspace/'Cargo.toml'),'-p','horizon-client','--bin','terraforged_classic_client_metadata'],env=env,capture_output=True,text=True,encoding='utf-8',timeout=600)
    (work/'build.log').write_text(build.stdout+build.stderr,encoding='utf-8')
    report={'schemaVersion':1,'status':'failed','horizonRevision':stage['horizonRevision'],'stageResultSha256':sha(stage_file),'probeSourceSha256':sha(source),'verifierSourceSha256':sha(work/'verifier-source.py'),'qaManifestBeforeSha256':before_manifest,'qaManifestAfterSha256':sha(manifest),'compileExitCode':build.returncode,'resourceFilesSha256':before,'gameAssetsDownloaded':False}
    if build.returncode==0:
        exe=workspace/'target/fast'/('terraforged_classic_client_metadata'+('.exe' if os.name=='nt' else ''));report['executableSha256']=sha(exe)
        run=subprocess.run([str(exe),str(resources),str(work/'metadata-world')],env=env,capture_output=True,timeout=240)
        (work/'output.json').write_bytes(run.stdout);(work/'stderr.log').write_bytes(run.stderr);report['exitCode']=run.returncode;report['outputSha256']=sha(work/'output.json')
        if run.returncode==0:report['observed']=json.loads(run.stdout);report['status']=report['observed']['status']
    report['resourcesUnchanged']=all(sha(resources/name)==digest for name,digest in before.items())
    if not report['resourcesUnchanged']:report['status']='failed-resources-changed'
    report['completedAtUtc']=dt.datetime.now(dt.timezone.utc).isoformat();a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k!='resourceFilesSha256'},indent=2));return 0 if report['status']=='passed-native-client-classic-biome-metadata' else 1
if __name__=='__main__':raise SystemExit(main())
