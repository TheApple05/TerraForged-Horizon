"""Create a native world through real UI controls, then save, reopen and inspect FULL chunks."""
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,math,os,shutil,subprocess,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','resources','hmod','report'):parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--classic',action='store_true',help='Render all 17 natural classic locations and inspect their saved FULL biome vectors')
    target_selection=parser.add_mutually_exclusive_group()
    target_selection.add_argument('--classic-target',action='append',default=[],metavar='BIOME_ID',help='Render only these classic targets, in argument order, before the origin QA teleport; implies --classic')
    target_selection.add_argument('--classic-first',metavar='BIOME_ID',help='Render all classic targets, with this target before the origin QA teleport; implies --classic')
    a=parser.parse_args();workspace=a.workspace.resolve();source=a.resources.resolve();artifact=a.hmod.resolve()
    a.classic=a.classic or bool(a.classic_target) or bool(a.classic_first)
    targets_file=ROOT/'horizon/tests/fixtures/classic-runtime-v1/targets.json'
    target_document=json.loads(targets_file.read_text(encoding='utf-8')) if a.classic else None
    if a.classic_target:
        unknown=set(a.classic_target)-target_document['targets'].keys()
        if unknown:parser.error('Unknown classic target(s): '+', '.join(sorted(unknown)))
        if len(set(a.classic_target))!=len(a.classic_target):parser.error('Classic targets must be unique')
    target_names=a.classic_target or sorted(target_document['targets'] if target_document else [])
    if a.classic_first:
        if a.classic_first not in target_document['targets']:parser.error('Unknown first classic target: '+a.classic_first)
        target_names=[a.classic_first]+[name for name in target_names if name!=a.classic_first]
    if a.report.exists():parser.error('Refusing to replace UI evidence')
    if not workspace.is_relative_to((ROOT/'build/qa/horizon').resolve()) or workspace.name!='staged':parser.error('Fresh full UI stage required')
    stage_file=workspace.parent/'stage-result.json';stage=json.loads(stage_file.read_text(encoding='utf-8'))
    if not stage.get('worldPresetUiIncluded'):parser.error('This stage does not include UI registration')
    for name,digest in stage['inputFiles'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Restage changed source '+name)
    package=json.loads(artifact.with_suffix(artifact.suffix+'.json').read_text(encoding='utf-8'))
    if package['sha256']!=sha(artifact) or package['stageResultSha256']!=sha(stage_file):raise ValueError('Package does not match this exact stage')
    with zipfile.ZipFile(artifact) as archive:
        for path in (workspace.parent/'mods/terraforged_native').rglob('*'):
            if path.is_file() and archive.read('mixins/terraforged_native/'+path.relative_to(workspace.parent/'mods/terraforged_native').as_posix())!=path.read_bytes():raise ValueError('Packaged source differs from staged bundle')
    work=workspace.parent/a.report.stem;work.mkdir(exist_ok=False);shutil.copy2(Path(__file__),work/'verifier-source.py')
    env=dict(os.environ,CARGO_BUILD_JOBS='4',CARGO_NET_OFFLINE='true',HORIZON_NO_AUDIO='1',HORIZON_NO_DISCORD='1',HORIZON_LAUNCHER_NO_SELF_UPDATE='1',HORIZON_TELEMETRY_URL='off',HORIZON_PLAYER_NAME='TerraForgedQA')
    env.pop('CARGO_TARGET_DIR',None)
    for name in ('HORIZON_HOME','HORIZON_LAUNCHER_HOME','XDG_DATA_HOME','XDG_CONFIG_HOME','HORIZON_LAUNCHER_TRASH','HORIZON_LAUNCHER_CLIPBOARD','HORIZON_LAUNCHER_DESKTOP'):
        path=work/'homes'/name.lower();path.mkdir(parents=True);env[name]=str(path.resolve())
    game=Path(env['HORIZON_HOME']);socket=game/'control.sock';resources=work/'prepared-resources'
    (game/'options.txt').write_text('onboardAccessibility:false\nrenderDistance:6\nsimulationDistance:3\nmaxFps:30\ntutorialStep:none\n',encoding='utf-8')
    checked=[source/'horizon-prepare.json',source/'horizon-resources.json',source/'facts.json']+sorted((source/'worldgen').rglob('*.json'))
    before={path.relative_to(source).as_posix():sha(path) for path in checked}
    report={'schemaVersion':2,'status':'running','startedAtUtc':dt.datetime.now(dt.timezone.utc).isoformat(),'horizonRevision':stage['horizonRevision'],'stageResultSha256':sha(stage_file),'verifierSourceSha256':sha(work/'verifier-source.py'),'hmodSha256':sha(artifact),'qaSpawnSupplied':False,'creationViaUi':True,'structuresEnabled':True,'commandsEnabledViaUiForQa':True,'renderDistanceChunks':6,'gameAssetsDownloaded':False,'runs':[],'visibilityChecks':[],'notCovered':['All 17 native biome resources/features','Source carver configuration','Original TerraForged spawn-height and player-placement parity','Structure placement coverage','Standard launcher native-build installation','Controlled native performance and mod combinations']}
    if a.classic:
        report['classicTargetsSha256']=sha(targets_file);report['classicRenderedViews']=[];report['classicTargetOrder']=target_names
        report['classicFirstTarget']=target_names[0];report['classicFirstTargetBeforeOrigin']=bool(a.classic_first or a.classic_target)
        if a.classic_target:
            selected=dict(target_document,targets={name:target_document['targets'][name] for name in target_names})
            selected['scope']='Selected UI/save checks only; unselected classic targets are not covered by this run.'
            targets_file=work/'selected-classic-targets.json';targets_file.write_text(json.dumps(selected,indent=2)+'\n',encoding='utf-8',newline='\n')
            report['selectedClassicTargetsSha256']=sha(targets_file)
        else:report['notCovered'].remove('All 17 native biome resources/features')
        report['notCovered'].append('Independent Java whole-feature and scenery parity')
    spawn_reference=ROOT/'horizon/tests/fixtures/native-spawn-v1/values.tsv'
    if spawn_reference.exists():
        centers=dict(line.split('\t') for line in spawn_reference.read_text(encoding='utf-8').splitlines())
        report['independentJavaConfiguredSearchCenter']=[int(n) for n in centers['8675309/CONTINENT_CENTER'].split(',')]
        report['spawnReferenceSha256']=sha(spawn_reference)
    process=None;log=None;sequence=0
    suffix='.exe' if os.name=='nt' else '';target=workspace/'target/fast';client=target/('horizon-client'+suffix);ctl=target/('horizon-ctl'+suffix);fixture=target/('terraforged_save_fixture'+suffix)
    def checkpoint(phase):
        report['phase']=phase;report['updatedAtUtc']=dt.datetime.now(dt.timezone.utc).isoformat()
        a.report.parent.mkdir(parents=True,exist_ok=True)
        temporary=a.report.with_name(a.report.name+'.tmp')
        temporary.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');temporary.replace(a.report)
    def run(command,label,timeout=120):
        try:result=subprocess.run(command,cwd=game,env=env,capture_output=True,text=True,timeout=timeout)
        except subprocess.TimeoutExpired as error:
            for stream,value in (('stdout',error.stdout),('stderr',error.stderr)):
                if isinstance(value,bytes):value=value.decode('utf-8',errors='replace')
                (work/(label+'.'+stream+'.log')).write_text(value or '',encoding='utf-8')
            raise
        (work/(label+'.stdout.log')).write_text(result.stdout,encoding='utf-8');(work/(label+'.stderr.log')).write_text(result.stderr,encoding='utf-8')
        if result.returncode:raise RuntimeError(f'{label}: exit {result.returncode}; see preserved logs')
        return result
    def control(words,timeout=30):
        nonlocal sequence
        sequence+=1;result=run([str(ctl),'--socket',str(socket)]+words,f'ctl-{sequence:04d}-{words[0]}',timeout)
        lines=result.stdout.strip().splitlines();reply=json.loads(lines[-1]) if lines else {}
        if 'error' in reply:raise RuntimeError(f'Game rejected {words[0]}: '+str(reply['error']))
        return reply
    def poll(predicate,timeout,description):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if process.poll() is not None:raise RuntimeError('Client exited while '+description)
            state=control(['state'])
            if predicate(state):return state
            time.sleep(.3)
        raise RuntimeError('Timed out '+description)
    def click_label(fragment):
        widgets=control(['ui']).get('widgets',[])
        matches=[w for w in widgets if fragment.lower() in str(w.get('label','')).lower() and w.get('kind') in ('button','tab')]
        exact=[w for w in matches if str(w.get('label','')).lower()==fragment.lower()]
        if exact:matches=exact
        if len(matches)!=1:raise RuntimeError(f'Expected one UI widget containing {fragment!r}, found {len(matches)}')
        return control(['click',matches[0]['id']])
    def visible(x,y,z,label):
        started=time.monotonic();deadline=started+420;next_memory=started;next_progress=started
        evidence={'label':label,'target':[x,y,z],'deadlineSeconds':420,'startedAtUtc':dt.datetime.now(dt.timezone.utc).isoformat(),'firstClassicTarget':bool(target_names and label==target_names[0]),'status':'loading','samples':[],'serverMemorySamples':[]}
        report['visibilityChecks'].append(evidence);checkpoint('loading '+label)
        def memory_sample(reason):
            sample={'reason':reason,'elapsedSeconds':time.monotonic()-started,'startedAtUtc':dt.datetime.now(dt.timezone.utc).isoformat(),'timeoutSeconds':75,'controlLogPrefix':f'ctl-{sequence+1:04d}-memory'}
            try:
                value=control(['memory'],75)
                sample.update({key:value.get(key) for key in ('server_columns','server_generation','client_columns','process')})
            except Exception as error:sample['diagnosticError']=str(error)
            sample['completedElapsedSeconds']=time.monotonic()-started;evidence['serverMemorySamples'].append(sample)
            checkpoint('loading '+label)
        try:
            while time.monotonic()<deadline:
                if process.poll() is not None:raise RuntimeError('Client exited while loading '+label)
                snapshot=control(['status']);block=control(['block',str(x),str(y),str(z)]);renderer=snapshot.get('renderer') or {}
                evidence['lastStatus']=snapshot;evidence['lastBlock']=block;evidence['elapsedSeconds']=time.monotonic()-started
                if block.get('loaded') and snapshot.get('chunks',0)>=81 and renderer.get('resident_sections',0)>0 and renderer.get('drawn_sections',0)>0 and not snapshot.get('pending_chunks',0) and not snapshot.get('pending_uploads',0) and not any((snapshot.get('streaming') or {}).values()):
                    control(['wait','20'],30);evidence['status']='visible';memory_sample('visible')
                    return snapshot
                now=time.monotonic()
                if now>=next_progress:
                    evidence['samples'].append({'elapsedSeconds':now-started,'status':snapshot,'block':block});checkpoint('loading '+label);next_progress=now+30
                if now>=next_memory:
                    memory_sample('loading');next_memory=time.monotonic()+60
                time.sleep(.5)
            evidence['status']='timed-out';memory_sample('deadline')
            raise RuntimeError(f'Requested terrain {label} did not become visible within 420 seconds')
        except Exception as error:
            if evidence['status']=='loading':evidence['status']='failed'
            evidence['error']=str(error);raise
        finally:
            evidence['elapsedSeconds']=time.monotonic()-started;evidence['completedAtUtc']=dt.datetime.now(dt.timezone.utc).isoformat();checkpoint('visibility '+evidence['status']+': '+label)
    def screenshot(name):
        path=work/(name+'.png');control(['screenshot',str(path)],60)
        if not path.exists() or path.stat().st_size<1024:raise RuntimeError('Screenshot missing')
        return {'path':str(path),'sha256':sha(path)}
    def look(yaw,pitch):
        player=control(['state'])['player']
        control(['turn',str(yaw-player['yaw']),str(pitch-player['pitch'])])
        control(['wait','20'],30)
    def render_classic_targets(names):
        for name in names:
            point=target_document['targets'][name];x,y,z=(point[key] for key in ('x','y','z'))
            rise=96 if name in ('reterraforged:bryce','reterraforged:stone_forest') else 48
            checkpoint('teleporting '+name)
            control(['command',f'tp @s {x+0.5} {min(290,y+rise)} {z+0.5}'])
            look(135,45);shown=visible(x,y,z,name)
            report['classicRenderedViews'].append({'biome':name,'target':[x,y,z],'state':control(['state']),'visibleTerrainState':shown,'screenshot':screenshot('classic-'+name.split(':')[1])})
            checkpoint('rendered '+name)
    try:
        checkpoint('copying prepared resources')
        shutil.copytree(source,resources)
        if not all(sha(resources/name)==digest for name,digest in before.items()):raise ValueError('Copied resources differ')
        probe=workspace/'crates/horizon-client-lib/qa/terraforged_save_fixture.rs'
        if probe.read_bytes()!=(ROOT/'horizon/tests/rust/save_fixture_probe.rs').read_bytes():raise ValueError('Staged save probe differs')
        report['fixtureProbeSha256']=sha(probe)
        checkpoint('building exact staged artifacts')
        run(['cargo','+stable','build','--offline','--locked','--manifest-path',str(workspace/'Cargo.toml'),'--profile','fast','-p','horizon-client','-p','horizon-client-lib','--bin','horizon-client','--bin','horizon-ctl','--bin','terraforged_save_fixture'],'build',1200)
        report['artifactsSha256']={p.name:sha(p) for p in (client,ctl,fixture)}
        checkpoint('built exact staged artifacts')
        world=None
        for index in range(2):
            log=(work/f'game-{index}.log').open('w',encoding='utf-8');smoke=work/f'game-{index}-smoke.json'
            client_deadline=900+450*(len(target_names)+2) if a.classic else 900
            command=[str(client),'--resources',str(resources),'--game-dir',str(game),'--home',str(game),'--dev-mod',str(artifact),'--name','TerraForgedQA','--offscreen','--control','--control-socket',str(socket),'--render-distance','6','--width','1280','--height','720','--timeout-seconds',str(client_deadline),'--smoke-report',str(smoke)]
            if world:command+=['--world',str(world)]
            checkpoint(f'starting client {index}')
            started=time.monotonic();process=subprocess.Popen(command,cwd=game,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            for attempt in range(180):
                if process.poll() is not None:raise RuntimeError('Client exited during startup')
                try:control(['state'],5);break
                except (RuntimeError,subprocess.TimeoutExpired):time.sleep(1)
            else:raise RuntimeError('Control endpoint did not start')
            if index==0:
                poll(lambda s:(s.get('menu') or {}).get('mode')=='main',180,'waiting for title')
                control(['click-button','Singleplayer'])
                state=poll(lambda s:(s.get('menu') or {}).get('mode') in ('select-world','create-world'),60,'opening world creation')
                if state['menu']['mode']=='select-world':control(['click-button','Create New World'])
                poll(lambda s:(s.get('menu') or {}).get('mode')=='create-world',60,'opening create screen')
                control(['type','--field','name','--replace','TerraForged UI QA'])
                state=control(['state'])
                if state['menu']['creative'] or state['menu']['hardcore']:raise RuntimeError('Expected default survival mode')
                if not state['menu']['allow_commands']:click_label('Allow Commands')
                click_label('World')
                poll(lambda s:(s.get('menu') or {}).get('tab')=='world',30,'opening World tab')
                control(['type','--field','seed','--replace','8675309'])
                cycle=[]
                for step in range(7):
                    state=control(['state']);menu=state.get('menu') or {};cycle.append(menu.get('world_type'))
                    if menu.get('world_type')=='terraforged:default':break
                    click_label('World Type')
                else:raise RuntimeError('Native preset never appeared in UI cycle')
                if not menu.get('generate_structures') or menu.get('bonus_chest'):raise RuntimeError('Default generation flags changed')
                widgets=control(['ui']).get('widgets',[])
                if not any('TerraForged' in str(w.get('label','')) for w in widgets):raise RuntimeError('Native preset label was not translated')
                report['presetCycle']=cycle;report['creationMenu']=menu;report['creationScreenshot']=screenshot('native-preset-ui')
                if (game/'saves').exists() and any(p.name=='level.dat' for p in (game/'saves').rglob('level.dat')):raise RuntimeError('A world existed before the UI Create action')
                control(['click-button','Create New World'],240)
                natural=poll(lambda s:s.get('screen')=='playing' and s.get('player') is not None,420,'waiting for natural spawn')
                control(['wait-ready','180'],210)
                natural=poll(lambda s:(s.get('player') or {}).get('on_ground') and (s.get('player') or {}).get('health',0)>0,120,'waiting for a living grounded player')
                if natural.get('gamemode')!='survival':raise RuntimeError('Creation did not enter survival')
                control(['wait','60'],30)
                natural=control(['state'])
                if not (natural.get('player') or {}).get('on_ground') or (natural.get('player') or {}).get('health',0)<20:raise RuntimeError('Natural survival spawn was not healthy and grounded after settling')
                look(0,25)
                position=natural['player']['block_pos'];report['naturalSpawnVisibleTerrainState']=visible(*position,'natural-spawn')
                report['naturalSpawnState']=control(['state']);report['naturalSpawnScreenshot']=screenshot('natural-spawn')
                worlds=[p.parent for p in (game/'saves').rglob('level.dat')]
                if len(worlds)!=1:raise RuntimeError('Expected exactly one UI-created world')
                world=worlds[0];report['worldPath']=str(world)
                control(['command','gamemode spectator @s'])
                if a.classic_target:render_classic_targets(target_names)
                elif a.classic_first:render_classic_targets(target_names[:1])
                control(['command','tp @s 8.5 90 8.5']);look(135,20)
                rendered=visible(8,75,8,'origin')
            else:
                poll(lambda s:s.get('screen')=='playing' and s.get('player') is not None,420,'reopening UI-created world')
                control(['wait-ready','180'],210)
                control(['command','tp @s 16392 80 -32760']);look(135,20);rendered=visible(16392,65,-32760,'reopened-distant-terrain')
            state=control(['state']);image=screenshot(f'game-{index}')
            if a.classic and index==0 and not a.classic_target:render_classic_targets(target_names[1:] if a.classic_first else target_names)
            checkpoint(f'saving client {index}')
            control(['quit'],120);code=process.wait(timeout=120);process=None;log.close();log=None
            if code:raise RuntimeError(f'Client exit {code}')
            action='check_ui_all' if index else 'check_ui'
            arguments=[]
            if a.classic:
                action='check_ui_all_classic' if index else 'check_ui_classic';arguments=[str(targets_file)]
            checkpoint(f'checking saved FULL chunks {index}')
            result=run([str(fixture),action,str(world),str(ROOT/'horizon/native-content/data/terraforged/worldgen/world_preset/default.json'),str(resources)]+arguments,f'game-{index}-saved-biomes',600 if a.classic else 300)
            saved=json.loads(result.stdout)
            report['runs'].append({'index':index,'exitCode':code,'elapsedSeconds':time.monotonic()-started,'state':state,'visibleTerrainState':rendered,'savedBiomeChecks':saved,'screenshot':image,'gameLogSha256':sha(work/f'game-{index}.log')})
            checkpoint(f'checked saved FULL chunks {index}')
        report['status']='passed-native-ui-create-reopen-smoke-awaiting-image-review';report['renderedImagesNeedReview']=True
    except Exception as error:report['status']='failed';report['error']=str(error)
    finally:
        if process is not None and process.poll() is None:
            try:subprocess.run([str(ctl),'--socket',str(socket),'quit'],cwd=game,env=env,capture_output=True,timeout=20);process.wait(timeout=20)
            except Exception:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait()
        if log is not None:log.close()
        report['checkedResourcesUnchanged']=all(sha(source/name)==digest for name,digest in before.items());report['checkedResourceCopyUnchanged']=resources.exists() and all(sha(resources/name)==digest for name,digest in before.items());report['checkedResourceFilesSha256']=before
        if not report['checkedResourcesUnchanged'] or not report['checkedResourceCopyUnchanged']:report['status']='failed';report['error']='Checked original or copied resources changed'
        report['completedAtUtc']=dt.datetime.now(dt.timezone.utc).isoformat();checkpoint('completed')
    print(json.dumps({k:report.get(k) for k in ('status','error','horizonRevision','completedAtUtc')},indent=2));return 0 if report['status'].startswith('passed-') else 1
if __name__=='__main__':raise SystemExit(main())
