"""Check all 17 variants in live native queries and stored generated quarts."""
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PASSED='passed-native-classic-natural-source-and-stored-quarts'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','resources','report'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();workspace=a.workspace.resolve();resources=a.resources.resolve()
    if not workspace.is_relative_to((ROOT/'build/qa/horizon').resolve()) or workspace.name!='staged':p.error('Fresh stage below build/qa/horizon required')
    if a.report.exists():p.error('Refusing to overwrite evidence')
    stage_path=workspace.parent/'stage-result.json';stage=json.loads(stage_path.read_text(encoding='utf-8'))
    for name,digest in stage['inputFiles'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Restage changed source '+name)
    work=workspace.parent/a.report.stem;work.mkdir(exist_ok=False);shutil.copy2(Path(__file__),work/'verifier-source.py')
    source=ROOT/'horizon/tests/rust/classic_biome_runtime_probe.rs';dest=workspace/'crates/horizon-world/src/bin/terraforged_classic_biomes.rs'
    if dest.exists() and dest.read_bytes()!=source.read_bytes():raise ValueError('Existing probe differs')
    if not dest.exists():shutil.copy2(source,dest)
    paths=[resources/'facts.json']+sorted((resources/'worldgen').rglob('*.json'));before={str(path.relative_to(resources)):sha(path) for path in paths}
    env=dict(os.environ,CARGO_NET_OFFLINE='true',CARGO_BUILD_JOBS='4',HORIZON_TELEMETRY_URL='off',HORIZON_NO_AUDIO='1',HORIZON_NO_DISCORD='1',HORIZON_LAUNCHER_NO_SELF_UPDATE='1')
    command=['cargo','+stable','build','--offline','--locked','--manifest-path',str(workspace/'Cargo.toml'),'-p','horizon-world','--release','--bin','terraforged_classic_biomes']
    built=subprocess.run(command,env=env,capture_output=True,text=True,encoding='utf-8',timeout=600);(work/'build.log').write_text(built.stdout+built.stderr,encoding='utf-8')
    target=Path(env.get('CARGO_TARGET_DIR',str(workspace/'target')));exe=target/'release'/('terraforged_classic_biomes'+('.exe' if os.name=='nt' else ''))
    inputs=ROOT/'horizon/tests/fixtures/host-density-v1/inputs.json';targets=ROOT/'horizon/tests/fixtures/classic-runtime-v1/targets.json'
    report={'schemaVersion':1,'status':'failed','horizonRevision':stage['horizonRevision'],'stageResultSha256':sha(stage_path),'verifierSourceSha256':sha(work/'verifier-source.py'),'probeSourceSha256':sha(source),'configurationSha256':sha(inputs),'advisoryTargetsSha256':sha(targets),'compileExitCode':built.returncode,'resourceFilesSha256':before,'gameAssetsDownloaded':False,'runs':[]}
    outputs=[]
    if built.returncode==0:
        report['executableSha256']=sha(exe)
        for index in range(2):
            for name in ('HORIZON_HOME','HORIZON_LAUNCHER_HOME','XDG_DATA_HOME','XDG_CONFIG_HOME','HORIZON_LAUNCHER_TRASH','HORIZON_LAUNCHER_CLIPBOARD','HORIZON_LAUNCHER_DESKTOP'):
                path=work/f'run-{index}-homes'/name.lower();path.mkdir(parents=True);env[name]=str(path.resolve())
            run=subprocess.run([str(exe),str(resources),str(inputs),str(targets)],env=env,capture_output=True,timeout=600)
            output=work/f'run-{index}.json';output.write_bytes(run.stdout);(work/f'run-{index}-stderr.log').write_bytes(run.stderr)
            observed=json.loads(run.stdout) if run.returncode==0 else None
            report['runs'].append({'exitCode':run.returncode,'outputSha256':sha(output),'observed':observed})
            if observed and observed['status']==PASSED:outputs.append(run.stdout)
            else:break
    report['freshProcessesAgree']=len(outputs)==2 and outputs[0]==outputs[1]
    report['resourcesUnchanged']=all(sha(resources/name)==digest for name,digest in before.items())
    if report['freshProcessesAgree'] and report['resourcesUnchanged']:report['status']=PASSED
    report['completedAtUtc']=dt.datetime.now(dt.timezone.utc).isoformat();a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('resourceFilesSha256','runs')},indent=2));return 0 if report['status']==PASSED else 1
if __name__=='__main__':raise SystemExit(main())
