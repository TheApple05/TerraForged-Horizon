"""Offscreen local QA template for an exact installed native client; launcher GUI Play remains untested."""
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,math,os,subprocess,time
from pathlib import Path
WORK=Path(__file__).resolve().parent
BASE=WORK.parent
INPUTS=WORK/"inputs"
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def preferences_order_evidence(original,current,locked_sha):
    original_sha=hashlib.sha256(original).hexdigest();actual=hashlib.sha256(current).hexdigest()
    same_lines=sorted(original.splitlines(keepends=True))==sorted(current.splitlines(keepends=True))
    known_sort=current==b''.join(sorted(original.splitlines(keepends=True)))
    allowed=original_sha==locked_sha=='8ec689e16d81a9fb9102c4618b10b9295a12aaf8c2f4f903d883997a1da50b1f' and actual=='d33604c2fe7c0ab40c1ce301c3e5d36d9df29e7d390009786610fe070d6f4e79' and same_lines and known_sort
    return {'originalSha256':original_sha,'lockedSha256':locked_sha,'actualSha256':actual,'exactLineMultisetsEqual':same_lines,'exactKnownSortedOriginalBytes':known_sort,'allowedKnownOrderNormalization':allowed}
def verify_integrity(plan):
    bad=[];preference_evidence=None;preferences=Path(plan['gameHome'])/'horizon-mods.txt'
    for value,digest in plan['lockedFiles'].items():
        path=Path(value);actual=sha(path) if path.is_file() else None
        if path==preferences:
            original=Path(plan['preferenceOrderSnapshot']).read_bytes();current=path.read_bytes()
            preference_evidence=preferences_order_evidence(original,current,digest)
            if actual!=digest and not preference_evidence['allowedKnownOrderNormalization']:bad.append(str(path))
        elif actual!=digest:bad.append(str(path))
    resources=Path(plan['resources']);expected=json.loads((INPUTS/'resources-sha256.json').read_text(encoding='utf-8'))
    actual={path.relative_to(resources).as_posix():sha(path) for path in sorted(resources.rglob('*')) if path.is_file()}
    if actual!=expected:bad.append('installed prepared-resource inventory')
    if bad:raise ValueError('Fixed installed QA inputs changed: '+', '.join(bad))
    return {'lockedFilesVerified':len(plan['lockedFiles']),'resourceFilesVerified':len(actual),'resourceManifestSha256':sha(INPUTS/'resources-sha256.json'),'preferencesNormalization':preference_evidence}

def atomic_json(path,value):
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    for attempt in range(6):
        try:temporary.replace(path);return
        except PermissionError:
            if attempt==5:raise
            time.sleep(.15*(attempt+1))


def exit_details(code):
    return {'exitCode':code,'exitCodeUnsignedHex':None if code is None else f'0x{code & 0xffffffff:08x}'}

def shutdown_owned_client(process,quit_client,evidence):
    """Record the initial exit separately from any action taken on this Popen child."""
    started=time.monotonic();evidence.update(pid=process.pid,initialExit=exit_details(process.poll()),actions=[])
    try:
        if process.poll() is None:
            try:
                evidence['actions'].append('control-quit');quit_client();process.wait(timeout=20)
            except Exception as error:
                evidence['gracefulError']=str(error)
                if process.poll() is None:
                    evidence['actions'].append('own-process-terminate');process.terminate()
                    try:process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        if process.poll() is None:
                            evidence['actions'].append('own-process-kill');process.kill()
                        process.wait(timeout=10)
    finally:
        evidence.update(finalExit=exit_details(process.poll()),elapsedSeconds=time.monotonic()-started,completedAtUtc=dt.datetime.now(dt.timezone.utc).isoformat())
def main():
    parser=argparse.ArgumentParser(description='QA-only reuse of verify_native_ui.py against an exact installed client. Default is preflight; --run starts offscreen local game QA, never launcher Play.')
    parser.add_argument('--run',action='store_true')
    a=parser.parse_args();plan=json.loads((WORK/'plan.json').read_text(encoding='utf-8'))
    verified=verify_integrity(plan)
    specification=json.loads((INPUTS/'environment.json').read_text(encoding='utf-8'));env=dict(os.environ)
    for key in list(env):
        if key in specification['remove'] or any(key.upper().startswith(prefix) for prefix in specification['removePrefixes']):env.pop(key,None)
    env.update(specification['overrides']);game=Path(plan['gameHome']);env['HORIZON_HOME']=str(game)
    for key in ('LIBGL_ALWAYS_SOFTWARE','GALLIUM_DRIVER','WEBKIT_DISABLE_DMABUF_RENDERER','WEBKIT_DISABLE_COMPOSITING_MODE'):env.pop(key,None)
    env['HORIZON_LAUNCHER_EXE']=plan['launcherExe']
    env.setdefault('PIPEWIRE_PROPS','{ application.name = "Horizon" media.role = "Game" }')
    homes=('HORIZON_HOME','HORIZON_LAUNCHER_HOME','XDG_DATA_HOME','XDG_CONFIG_HOME','HORIZON_LAUNCHER_TRASH','HORIZON_LAUNCHER_CLIPBOARD','HORIZON_LAUNCHER_DESKTOP')
    if any(not Path(env[key]).resolve().is_relative_to(BASE.resolve()) for key in homes):raise ValueError('A QA home escapes StandardRoot')
    instances=json.loads((Path(env['HORIZON_LAUNCHER_HOME'])/'instances.json').read_text(encoding='utf-8'))
    if instances['instances']['pack:'+plan['packId']]['version']!=plan['nativeVersion']:raise ValueError('Registry pack no longer pins the exact installed native version')
    if '--offscreen' not in plan['baseArgv']:raise ValueError('This QA revision requires explicitly labeled offscreen rendering')
    if any((game/'saves').rglob('level.dat')):raise ValueError('Fresh QA creation requires no existing pack worlds')
    shown_file=game/'horizon-mods/.horizon-mod-data/coords_hud/shown'
    if shown_file.read_text(encoding='utf-8').strip()!='true':raise ValueError('Official HUD must initially be shown for exact off/on toggle checks')
    preflight={'status':'preflight-passed-no-game-launched','scope':plan['scope'],'integrity':verified,'argv':plan['baseArgv'],'cwd':str(game),'environmentOverrides':dict(specification['overrides'],HORIZON_HOME=str(game),HORIZON_LAUNCHER_EXE=env['HORIZON_LAUNCHER_EXE']),'sevenHomes':{key:env[key] for key in homes},'scriptSha256':sha(Path(__file__)),'planSha256':sha(WORK/'plan.json')}
    atomic_json(WORK/'preflight.json',preflight)
    if not a.run:print(json.dumps(preflight,indent=2));return 0
    qualification=json.loads(Path(plan['launcherQualification']).read_text(encoding='utf-8'))
    if qualification['status']!='passed-static-launcher-qualification':raise RuntimeError('Owned compiler/test tasks must finish before client QA')
    a.report=WORK/'report.json'
    if a.report.exists():raise ValueError('Refusing to replace an earlier QA run; preserve its failed attempts')
    work=WORK/'run';work.mkdir(exist_ok=False)
    original_options=(game/'options.txt').read_bytes() if (game/'options.txt').exists() else b''
    (work/'options-before.txt').write_bytes(original_options)
    (game/'options.txt').write_text('onboardAccessibility:false\nrenderDistance:'+str(plan['renderDistance'])+'\nsimulationDistance:12\nmaxFps:30\ntutorialStep:none\nfullscreen:false\npauseOnLostFocus:false\n',encoding='utf-8')
    socket=Path(plan['socket']);resources=Path(plan['resources']);client=Path(plan['client']);ctl=Path(plan['ctl']);fixture=Path(plan['oldSaveProbe'])
    targets_file=INPUTS/'selected-classic-targets.json';target_document=json.loads(targets_file.read_text(encoding='utf-8'));target_names=plan['selectedTargets']
    a.classic=True;a.classic_target=target_names;a.classic_first=None
    report={'schemaVersion':3,'status':'running-direct-installed-client-qa','startedAtUtc':dt.datetime.now(dt.timezone.utc).isoformat(),'scope':plan['scope'],'launcherGuiPlayCovered':False,'normalCliOwnerGateCovered':False,'strictCliOwnerGateUnchanged':True,'windowPresentation':'Actual window/swapchain; deliberately differs from the old offscreen helper.','horizonRevision':plan['engineCommit'],'nativeVersion':plan['nativeVersion'],'oldSaveProbeScope':plan['oldSaveProbeScope'],'preflight':preflight,'qaSpawnSupplied':False,'creationViaUi':True,'structuresEnabled':True,'commandsEnabledViaUiForQa':True,'renderDistanceChunks':plan['renderDistance'],'gameAssetsDownloaded':False,'runs':[],'operations':[],'visibilityChecks':[],'classicRenderedViews':[],'classicTargetOrder':target_names,'notCovered':['Launcher GUI Play and its developer-offline dispatch','Authenticated launcher Play','Exact f43 save-reader qualification','Unselected classic biome coverage','Independent Java whole-feature/scenery parity','Controlled performance measurements']}
    report['windowPresentation']='Offscreen rendering; the separate frozen dev6 baseline already proved actual-window Vulkan presentation.'
    report['renderDistanceChunks']=plan['renderDistance'];report['cameraChecks']=[]
    process=None;log=None;sequence=0;requested_view=None
    def checkpoint(phase):
        report['phase']=phase;report['updatedAtUtc']=dt.datetime.now(dt.timezone.utc).isoformat()
        a.report.parent.mkdir(parents=True,exist_ok=True)
        atomic_json(a.report,report)
    def run(command,label,timeout=120):
        entry={'argv':command,'label':label,'startedAtUtc':dt.datetime.now(dt.timezone.utc).isoformat()};report['operations'].append(entry);started=time.monotonic()
        child=subprocess.Popen(command,cwd=game,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0);entry['pid']=child.pid
        try:stdout,stderr=child.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            child.kill();stdout,stderr=child.communicate();entry['timedOut']=True
        entry['stdoutPath']=str(work/(label+'.stdout.log'));entry['stderrPath']=str(work/(label+'.stderr.log'))
        Path(entry['stdoutPath']).write_text(stdout or '',encoding='utf-8');Path(entry['stderrPath']).write_text(stderr or '',encoding='utf-8')
        entry.update(exit_details(child.returncode));entry['elapsedSeconds']=time.monotonic()-started;checkpoint('command '+label)
        if entry.get('timedOut') or child.returncode:raise RuntimeError(f'{label}: exit {child.returncode}; see preserved logs')
        return subprocess.CompletedProcess(command,child.returncode,stdout,stderr)
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
        evidence['optionProof']=control(['options-get','renderDistance','simulationDistance'])
        if any(evidence['optionProof']['options'][key]['value']!=12 for key in ('renderDistance','simulationDistance')):raise RuntimeError('Live render/simulation options must equal12')
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
                if snapshot.get('render_distance')==12 and block.get('loaded') and snapshot.get('chunks',0)>=plan['expectedTrackedColumns'] and renderer.get('resident_sections',0)>0 and renderer.get('drawn_sections',0)>0 and not snapshot.get('pending_chunks',0) and not snapshot.get('pending_uploads',0) and not any((snapshot.get('streaming') or {}).values()):
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
        before=assert_view('before screenshot '+name) if requested_view else None
        path=work/(name+'.png');control(['screenshot',str(path)],60)
        if not path.exists() or path.stat().st_size<1024:raise RuntimeError('Screenshot missing')
        if requested_view:assert_view('after screenshot '+name)
        return {'path':str(path),'sha256':sha(path)}
    def assert_view(label):
        state=control(['state']);player=state['player'];yaw,pitch=requested_view
        error=abs((player['yaw']-yaw+180)%360-180);pitch_error=abs(player['pitch']-pitch)
        evidence={'label':label,'requested':[yaw,pitch],'actual':[player['yaw'],player['pitch']],'yawModuloError':error,'pitchError':pitch_error,'state':state}
        report['cameraChecks'].append(evidence)
        if not all(math.isfinite(v) for v in (player['yaw'],player['pitch'],error,pitch_error)) or error>.1 or pitch_error>.1:raise AssertionError('Actual camera angle did not match requested '+label)
        return evidence
    def look(yaw,pitch):
        nonlocal requested_view
        requested_view=(yaw,pitch)
        for attempt in range(3):
            player=control(['state'])['player'];x,y,z=player['position']
            control(['command',f'tp @s {x} {y} {z} {yaw} {pitch}']);control(['wait','20'],30)
            try:assert_view('absolute rotation attempt '+str(attempt+1));return
            except AssertionError:
                if attempt==2:raise
    def render_classic_targets(names):
        for name in names:
            point=target_document['targets'][name];x,y,z=(point[key] for key in ('x','y','z'))
            rise=96 if name in ('reterraforged:bryce','reterraforged:stone_forest') else 48
            checkpoint('teleporting '+name)
            control(['command',f'tp @s {x+0.5} {min(290,y+rise)} {z+0.5}'])
            look(135,45);shown=visible(x,y,z,name)
            look(135,45)
            report['classicRenderedViews'].append({'biome':name,'target':[x,y,z],'state':control(['state']),'visibleTerrainState':shown,'screenshot':screenshot('classic-'+name.split(':')[1])})
            checkpoint('rendered '+name)
    def chat_keys(text,expected):
        control(['key','t','tap']);control(['type',text]);typed=control(['screen'])
        if typed.get('chat_input')!=text:raise RuntimeError('Typed chat input differs from requested '+text)
        control(['key','enter','tap']);control(['wait','20']);messages=control(['messages','10'])
        if expected not in json.dumps(messages.get('styled',[])):raise RuntimeError('Expected client UI chat confirmation absent: '+expected)
        return {'typedScreen':typed,'messages':messages,'state':control(['state'])}
    def hud_and_recipe():
        evidence={};report['hudAndRecipe']=evidence
        dimension=control(['state']).get('dimension','minecraft:overworld')
        evidence['where']=chat_keys('/where',' in '+dimension);evidence['where']['screenshot']=screenshot('hud-where')
        for text,expected,value,label in [('/coords off','Coordinates panel hidden','false','hud-off'),('/coords on','Coordinates panel shown','true','hud-on')]:
            evidence[label]=chat_keys(text,expected)
            if shown_file.read_text(encoding='utf-8').strip()!=value:raise RuntimeError('HUD setting not persisted for '+text)
            evidence[label]['storedShown']=value;evidence[label]['screenshot']=screenshot(label)
        evidence['commandSemantics']='Official HUD2.0 toggles on either coords command; off/on arguments are ignored by this version.'
        control(['options','mods']);evidence['modsScreen']=control(['ui']);evidence['modsScreenshot']=screenshot('installed-mods-screen')
        for step in range(4):
            if control(['state']).get('screen')=='playing':break
            control(['key','esc','tap'])
        else:raise RuntimeError('Mods screen did not close through Escape')
        evidence['inventoryBeforeIngredients']=control(['inventory'])
        control(['give','minecraft:amethyst_block','1']);control(['give','minecraft:glowstone_dust','1'])
        evidence['inventoryBeforeCraft']=control(['inventory']);control(['key','e','tap']);screen=control(['screen'])
        if screen.get('screen')!='inventory' or screen.get('craft_size')!=2:raise RuntimeError('Expected 2x2 survival inventory')
        for item,destination in [('minecraft:amethyst_block',100),('minecraft:glowstone_dust',101)]:
            screen=control(['screen']);slots=[slot for slot in screen['slots'] if slot['slot']<36 and slot.get('item')==item]
            if len(slots)!=1:raise RuntimeError('Expected one ingredient stack for '+item)
            control(['click-slot',str(slots[0]['slot'])]);control(['click-slot',str(destination)])
        evidence['recipeScreen']=control(['screen']);result=[slot for slot in evidence['recipeScreen']['slots'] if slot['slot']==200]
        if len(result)!=1 or result[0].get('item')!='qa_glow:glowing_amethyst' or result[0].get('count')!=1:raise RuntimeError('Installed custom recipe did not produce one glowing amethyst')
        evidence['recipeScreenshot']=screenshot('custom-recipe-result');control(['click-slot','200','shift'])
        evidence['inventoryAfterCraft']=control(['inventory']);evidence['screenAfterCraft']=control(['screen'])
        before=evidence['inventoryBeforeIngredients']['counts'];after=evidence['inventoryAfterCraft']['counts']
        if after.get('qa_glow:glowing_amethyst',0)!=before.get('qa_glow:glowing_amethyst',0)+1:raise RuntimeError('Craft output missing from inventory')
        if any(after.get(item,0)!=before.get(item,0) for item in ('minecraft:amethyst_block','minecraft:glowstone_dust')):raise RuntimeError('Craft ingredients were not consumed exactly')
        if any(slot.get('item') for slot in evidence['screenAfterCraft']['slots'] if 100<=slot['slot']<=103):raise RuntimeError('Craft grid retained ingredients')
        evidence['craftedScreenshot']=screenshot('custom-recipe-crafted');control(['key','e','tap']);checkpoint('HUD chat and custom recipe checked')
    def place_crafted_block():
        evidence={'scope':'Crafted-item placement through existing place API in creative; command-created stone support only.'};report['craftedBlockPlacement']=evidence
        control(['command','gamemode creative @s']);control(['command','setblock 40 299 8 minecraft:stone']);control(['command','tp @s 40.5 301 11.5'])
        evidence['stateBefore']=control(['state']);evidence['support']=control(['block','40','299','8']);evidence['targetBefore']=control(['block','40','300','8'])
        if evidence['stateBefore'].get('gamemode')!='creative' or not evidence['stateBefore']['player'].get('flying'):raise RuntimeError('Creative placement requires preserved spectator flight')
        if evidence['support'].get('block')!='minecraft:stone' or not evidence['support'].get('loaded'):raise RuntimeError('QA support was not loaded stone')
        if evidence['targetBefore'].get('block')!='minecraft:air':raise RuntimeError('QA block placement target was not empty air')
        inventory=control(['inventory']);item='qa_glow:glowing_amethyst'
        if inventory['counts'].get(item)!=1:raise RuntimeError('Expected exactly one crafted custom item before placement')
        if not any(slot.get('item')==item for slot in inventory['hotbar']):
            sources=[slot for slot in inventory['main'] if slot.get('item')==item];destinations=[slot for slot in inventory['hotbar'] if slot.get('item') is None]
            if len(sources)!=1 or not destinations:raise RuntimeError('Crafted item cannot be moved to an empty hotbar slot')
            control(['key','e','tap']);control(['click-slot',str(sources[0]['slot'])]);control(['click-slot',str(destinations[0]['slot'])]);control(['key','e','tap'])
        evidence['inventoryBefore']=control(['inventory']);evidence['placeReply']=control(['place','40','300','8','--item',item]);control(['wait','60'])
        evidence['inventoryAfter']=control(['inventory'])
        if not evidence['placeReply'].get('ok') or not evidence['placeReply'].get('changed'):raise RuntimeError('Existing place API did not confirm custom block placement')
        if evidence['inventoryAfter']['counts'].get(item)!=1:raise RuntimeError('Creative placement did not retain the crafted item')
        custom_block_check('before-save');look(180,35);evidence['screenshot']=screenshot('custom-block-placed')
        control(['command','gamemode spectator @s']);control(['command','tp @s 8.5 90 8.5']);look(135,20)
    def custom_block_check(label):
        evidence={'block':control(['block','40','300','8']),'light':control(['light','40','300','8','41','300','8'])}
        if evidence['block'].get('block')!='qa_glow:glowing_amethyst' or not evidence['block'].get('loaded'):raise RuntimeError('Saved custom block missing at '+label)
        if evidence['light'].get('block')!='76':raise RuntimeError('Custom block light7/adjacent6 missing at '+label)
        report.setdefault('customBlockPersistence',{})[label]=evidence;checkpoint('custom block '+label)
    try:
        world=None
        for index in range(2):
            log=(work/f'game-{index}.log').open('w',encoding='utf-8');smoke=work/f'game-{index}-smoke.json'
            command=list(plan['baseArgv'])+['--smoke-report',str(smoke)]
            if world:command+=['--world',str(world)]
            checkpoint(f'starting client {index}')
            started=time.monotonic();process=subprocess.Popen(command,cwd=game,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            report.setdefault('clientLaunches',[]).append({'index':index,'pid':process.pid,'command':command,'cwd':str(game),'stdoutAndStderrPath':str(work/f'game-{index}.log'),'startedAtUtc':dt.datetime.now(dt.timezone.utc).isoformat()})
            checkpoint(f'running client {index}')
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
                hud_and_recipe()
                control(['command','gamemode spectator @s'])
                if a.classic_target:render_classic_targets(target_names)
                elif a.classic_first:render_classic_targets(target_names[:1])
                control(['command','tp @s 8.5 90 8.5']);look(135,20)
                rendered=visible(8,75,8,'origin')
                place_crafted_block()
            else:
                poll(lambda s:s.get('screen')=='playing' and s.get('player') is not None,420,'reopening UI-created world')
                control(['wait-ready','180'],210)
                custom_block_check('after-reopen')
                control(['command','tp @s 40.5 301 11.5']);look(180,35)
                report['customBlockPersistence']['after-reopen']['closeViewScreenshot']=screenshot('custom-block-reopened')
                report['inventoryAfterReopen']=control(['inventory'])
                if report['inventoryAfterReopen']['counts'].get('qa_glow:glowing_amethyst',0)<1:raise RuntimeError('Crafted custom item missing after reopen')
                if shown_file.read_text(encoding='utf-8').strip()!='true':raise RuntimeError('HUD setting missing after reopen')
                control(['command','tp @s 16392 80 -32760']);look(135,20);rendered=visible(16392,65,-32760,'reopened-distant-terrain')
            state=control(['state']);image=screenshot(f'game-{index}')
            if a.classic and index==0 and not a.classic_target:render_classic_targets(target_names[1:] if a.classic_first else target_names)
            checkpoint(f'saving client {index}')
            report['clientLaunches'][-1]['requestedShutdown']='control-quit'
            control(['quit'],120);code=process.wait(timeout=120)
            report['clientLaunches'][-1].update(exit_details(code));process=None;log.close();log=None
            if code:raise RuntimeError(f'Client exit {code}')
            action='check_ui_all' if index else 'check_ui'
            arguments=[]
            if a.classic:
                action='check_ui_all_classic' if index else 'check_ui_classic';arguments=[str(targets_file)]
            checkpoint(f'checking saved FULL chunks {index}')
            result=run([str(fixture),action,str(world),str(INPUTS/'world-preset.json'),str(resources)]+arguments,f'game-{index}-saved-biomes',600 if a.classic else 300)
            saved=json.loads(result.stdout)
            report['runs'].append({'index':index,'exitCode':code,'elapsedSeconds':time.monotonic()-started,'state':state,'visibleTerrainState':rendered,'crossRevisionSavedBiomeCompatibilityChecks':saved,'screenshot':image,'gameLogSha256':sha(work/f'game-{index}.log')})
            checkpoint(f'checked saved FULL chunks {index}')
        report['status']='passed-direct-installed-client-ui-save-qa-awaiting-image-review';report['renderedImagesNeedReview']=True
    except Exception as error:
        report['status']='failed';report['error']=str(error)
        if process is not None:
            report['clientExitCodeOnError']=process.poll()
            report['clientExitOnError']=exit_details(report['clientExitCodeOnError'])
    finally:
        if process is not None:
            cleanup=report.setdefault('clientCleanup',{})
            try:shutdown_owned_client(process,lambda:control(['quit'],20),cleanup)
            except Exception as error:
                report['cleanupError']=str(error);report['status']='failed'
        if log is not None:log.close()
        report['gameLogsSha256']={str(path):sha(path) for path in work.glob('game-*.log')}
        try:report['finalIntegrity']=verify_integrity(plan)
        except Exception as error:report['status']='failed';report['integrityError']=str(error);report.setdefault('error',str(error))
        report['completedAtUtc']=dt.datetime.now(dt.timezone.utc).isoformat();checkpoint('completed')
    print(json.dumps({k:report.get(k) for k in ('status','error','horizonRevision','completedAtUtc')},indent=2));return 0 if report['status'].startswith('passed-') else 1
if __name__=='__main__':raise SystemExit(main())
