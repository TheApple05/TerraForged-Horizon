"""One corrected offscreen fir view from an ordinary copy of the frozen dev6 QA world."""
import argparse,datetime as dt,hashlib,json,math,os,shutil,stat,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
STANDARD=ROOT.parent
BASELINE=STANDARD/'qa-dev7-default-view-v1'
def sha(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):value.update(chunk)
    return value.hexdigest()
def save(path,value):
    temporary=path.with_name(path.name+'.tmp');temporary.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    for attempt in range(6):
        try:temporary.replace(path);return
        except PermissionError:
            if attempt==5:raise
            time.sleep(.15*(attempt+1))
def tree(path):
    files={}
    for child in sorted(path.rglob('*')):
        info=child.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT:raise ValueError('Ordinary QA copies only: '+str(child))
        if child.is_file():files[child.relative_to(path).as_posix()]=sha(child)
    return files
def frozen_inputs(plan):
    checks={}
    for value,expected in plan['lockedFiles'].items():
        path=Path(value);actual=sha(path)
        if path==Path(plan['gameHome'])/'horizon-mods.txt':
            if expected!='8ec689e16d81a9fb9102c4618b10b9295a12aaf8c2f4f903d883997a1da50b1f' or actual!='d33604c2fe7c0ab40c1ce301c3e5d36d9df29e7d390009786610fe070d6f4e79':raise ValueError('Unexpected baseline preferences')
        elif actual!=expected:raise ValueError('Frozen input changed: '+value)
        checks[value]=actual
    expected=json.loads((BASELINE/'inputs/resources-sha256.json').read_text(encoding='utf-8'))
    names=[n for n in expected if n in ('facts.json','horizon-prepare.json','horizon-resources.json') or n.startswith('worldgen/') or 'white_wool' in n or n.endswith('/stairs.json') or n.endswith('/inner_stairs.json') or n.endswith('/outer_stairs.json')]
    for name in names:
        if sha(Path(plan['resources'])/name)!=expected[name]:raise ValueError('Focused resource changed: '+name)
    return {'lockedFilesSha256':checks,'focusedResourceFiles':len(names),'scope':'Focused model diagnostic; all28180resources already verified by unchanged parent report.','parentFullReportSha256':sha(BASELINE/'report.json')}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true');args=parser.parse_args()
    plan=json.loads((BASELINE/'plan.json').read_text());baseline=json.loads((BASELINE/'report.json').read_text());manifest_path=ROOT/'preparation.json'
    if not manifest_path.exists():
        verified=frozen_inputs(plan);source=Path(baseline['worldPath']);source_files=tree(source);game=ROOT/'homes/game';game.mkdir(parents=True,exist_ok=False)
        homes={}
        for name,relative in [('HORIZON_HOME','game'),('HORIZON_LAUNCHER_HOME','launcher'),('XDG_DATA_HOME','xdg-data'),('XDG_CONFIG_HOME','xdg-config'),('HORIZON_LAUNCHER_TRASH','trash'),('HORIZON_LAUNCHER_CLIPBOARD','clipboard/clipboard.data'),('HORIZON_LAUNCHER_DESKTOP','desktop')]:
            path=ROOT/'homes'/relative
            if name=='HORIZON_LAUNCHER_CLIPBOARD':path.parent.mkdir(parents=True);path.write_bytes(b'')
            else:path.mkdir(parents=True,exist_ok=name=='HORIZON_HOME')
            homes[name]=str(path)
        copied=[]
        for relative in ('horizon-native-mods/terraforged_native.hmod','horizon-native-mods/coords_hud.hnmod','horizon-mods/qa_glow.hmod','horizon-mods/.horizon-mod-data/coords_hud/shown','horizon-mods.txt'):
            original=Path(plan['gameHome'])/relative;target=game/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original,target);copied.append({'path':str(target),'source':str(original),'sha256':sha(target)})
        world=game/'saves'/source.name;world.parent.mkdir();shutil.copytree(source,world)
        if tree(world)!=source_files:raise ValueError('Copied world differs')
        (game/'options.txt').write_text('onboardAccessibility:false\nrenderDistance:12\nsimulationDistance:12\nmaxFps:30\ntutorialStep:none\nfullscreen:false\npauseOnLostFocus:false\n',encoding='utf-8')
        save(manifest_path,{'status':'prepared-not-launched','scope':'Focused structure/model diagnostic on ordinary copy of qualifieddev7 world. Parentfullview/save tests remain unchanged; no performance claim.','baselineReportSha256':sha(BASELINE/'report.json'),'baselineRawStatus':baseline['status'],'scriptSha256':sha(Path(__file__)),'sourceWorld':str(source),'sourceWorldFilesSha256':source_files,'copiedWorld':str(world),'copiedWorldFilesBeforeSha256':source_files,'copiedFiles':copied,'sevenHomes':homes,'frozenInputsBefore':verified})
    manifest=json.loads(manifest_path.read_text())
    if sha(Path(__file__))!=manifest['scriptSha256']:raise ValueError('Prepared capture script changed')
    if not args.run:print(json.dumps({'status':manifest['status'],'scope':manifest['scope'],'worldFiles':len(manifest['sourceWorldFilesSha256']),'scriptSha256':manifest['scriptSha256']},indent=2));return 0
    report_path=ROOT/'report.json'
    if report_path.exists():raise ValueError('Refusing a second capture attempt')
    report={'status':'running-corrected-offscreen-capture','scope':manifest['scope'],'startedAtUtc':dt.datetime.now(dt.timezone.utc).isoformat(),'operations':[],'angleChecks':[]};save(report_path,report)
    specification=json.loads((BASELINE/'inputs/environment.json').read_text());env=dict(os.environ)
    for key in list(env):
        if key in specification['remove'] or any(key.upper().startswith(prefix) for prefix in specification['removePrefixes']):env.pop(key,None)
    env.update(specification['overrides']);env.update(manifest['sevenHomes']);env['HORIZON_LAUNCHER_EXE']=plan['launcherExe'];env['HORIZON_LAUNCHER_LOCATION_FILE']=str(ROOT/'homes/location.json');env.pop('HORIZON_MOD_INDEX',None)
    for key in ('LIBGL_ALWAYS_SOFTWARE','GALLIUM_DRIVER','WEBKIT_DISABLE_DMABUF_RENDERER','WEBKIT_DISABLE_COMPOSITING_MODE'):env.pop(key,None)
    if any(not Path(value).resolve().is_relative_to(ROOT.resolve()) for value in manifest['sevenHomes'].values()):raise ValueError('Fresh QA home escaped capture root')
    game=Path(env['HORIZON_HOME']);socket=game/'control.json';process=None;log=None;sequence=0
    def checkpoint(phase):report['phase']=phase;save(report_path,report)
    def control(words,timeout=30):
        nonlocal sequence
        sequence+=1;label=f'ctl-{sequence:04d}-{words[0]}';argv=[plan['ctl'],'--socket',str(socket)]+words;start=time.monotonic();entry={'argv':argv,'label':label,'startedAtUtc':dt.datetime.now(dt.timezone.utc).isoformat()};report['operations'].append(entry)
        child=subprocess.Popen(argv,cwd=game,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=subprocess.CREATE_NO_WINDOW);entry['pid']=child.pid
        try:stdout,stderr=child.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:child.kill();stdout,stderr=child.communicate();entry['timedOut']=True
        (ROOT/(label+'.stdout.log')).write_text(stdout or '',encoding='utf-8');(ROOT/(label+'.stderr.log')).write_text(stderr or '',encoding='utf-8');entry.update(exitCode=child.returncode,exitCodeUnsignedHex=f'0x{child.returncode & 0xffffffff:08x}',elapsedSeconds=time.monotonic()-start);checkpoint(label)
        if child.returncode or entry.get('timedOut'):raise RuntimeError(label+' failed')
        reply=json.loads(stdout.strip().splitlines()[-1])
        if 'error' in reply:raise RuntimeError(label+': '+str(reply['error']))
        return reply
    def angle(label):
        state=control(['state']);player=state['player'];error=abs((player['yaw']-180+180)%360-180);pitch_error=abs(player['pitch']-50)
        result={'label':label,'requested':[180,50],'actual':[player['yaw'],player['pitch']],'yawModuloError':error,'pitchError':pitch_error,'state':state};report['angleChecks'].append(result);checkpoint(label)
        if not all(math.isfinite(n) for n in (error,pitch_error)) or error>.1 or pitch_error>.1:raise AssertionError('Camera qualification failed: '+label)
        return result
    try:
        report['frozenInputsAtLaunch']=frozen_inputs(plan)
        for value in manifest['copiedFiles']:
            if sha(Path(value['path']))!=value['sha256']:raise ValueError('Copied archive/preferences changed before launch')
        argv=[plan['client'],'--resources',plan['resources'],'--game-dir',str(game),'--home',str(game),'--name','TerraForgedQA','--offscreen','--control','--control-socket',str(socket),'--render-distance','12','--width','1280','--height','720','--timeout-seconds','900','--smoke-report',str(ROOT/'smoke.json'),'--world',manifest['copiedWorld']]
        log=(ROOT/'game.log').open('w',encoding='utf-8');process=subprocess.Popen(argv,cwd=game,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);report['client']={'argv':argv,'pid':process.pid,'cwd':str(game),'sevenHomes':manifest['sevenHomes']};checkpoint('starting client')
        for attempt in range(180):
            if process.poll() is not None:raise RuntimeError('Client exited during startup')
            try:state=control(['state'],5)
            except RuntimeError:time.sleep(1);continue
            if state.get('screen')=='playing' and state.get('player'):break
            time.sleep(1)
        else:raise RuntimeError('Copied world did not open')
        control(['command','gamemode spectator @s']);control(['command','tp @s 17.5 75 -43718.5'])
        deadline=time.monotonic()+420
        while time.monotonic()<deadline:
            if process.poll() is not None:raise RuntimeError('Client exited during fir loading')
            state=control(['status']);block=control(['block','0','70','-43692']);renderer=state.get('renderer') or {};report['lastTerrainStatus']=state;checkpoint('loading existing fir terrain')
            if block.get('loaded') and state.get('chunks',0)>=637 and renderer.get('resident_sections',0)>0 and renderer.get('drawn_sections',0)>0 and not state.get('pending_chunks',0) and not state.get('pending_uploads',0) and not any((state.get('streaming') or {}).values()):break
            time.sleep(.5)
        else:raise RuntimeError('Copied fir terrain did not become visible')
        for attempt in range(3):
            control(['command','tp @s 17.5 75 -43718.5 180 50']);control(['wait','20'])
            try:angle('absolute rotation attempt '+str(attempt+1));break
            except AssertionError:
                if attempt==2:raise
        report['beforeScreenshot']=angle('immediately before screenshot');image=ROOT/'fir-structure-close.png';control(['screenshot',str(image)],60);report['afterScreenshot']=angle('immediately after screenshot')
        if not image.exists() or image.stat().st_size<1024:raise RuntimeError('Corrected screenshot missing')
        report['screenshot']={'path':str(image),'sha256':sha(image)};report['roofBlock']=control(['block','17','71','-43724']);control(['quit'],120);code=process.wait(timeout=120);report['client'].update(exitCode=code,exitCodeUnsignedHex=f'0x{code & 0xffffffff:08x}');process=None
        if code:raise RuntimeError('Corrected client exit '+str(code))
        report['status']='passed-focused-fir-structure-view-awaiting-review'
    except Exception as error:report['status']='failed';report['error']=str(error)
    finally:
        if process is not None:
            try:
                if process.poll() is None:control(['quit'],20);process.wait(timeout=20)
            except Exception as error:
                report['cleanupError']=str(error)
                if process.poll() is None:
                    process.terminate()
                    try:process.wait(timeout=20)
                    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)
            report['client'].update(exitCode=process.poll(),exitCodeUnsignedHex=f'0x{process.poll() & 0xffffffff:08x}')
        if log is not None:log.close()
        try:
            report['frozenInputsAfter']=frozen_inputs(plan)
            report['baselineWorldUnchanged']=tree(Path(manifest['sourceWorld']))==manifest['sourceWorldFilesSha256'];report['baselineReportUnchanged']=sha(BASELINE/'report.json')==manifest['baselineReportSha256']
            report['copiedArchivesUnchanged']=all(sha(Path(value['path']))==value['sha256'] for value in manifest['copiedFiles'])
            if not all(report[key] for key in ('baselineWorldUnchanged','baselineReportUnchanged','copiedArchivesUnchanged')):raise ValueError('Baseline or copied input changed')
        except Exception as error:report['status']='failed';report['integrityError']=str(error)
        report['completedAtUtc']=dt.datetime.now(dt.timezone.utc).isoformat();checkpoint('completed')
    print(json.dumps({key:report.get(key) for key in ('status','error','integrityError','baselineWorldUnchanged','baselineReportUnchanged')},indent=2));return 0 if report['status'].startswith('passed-') else 1
if __name__=='__main__':raise SystemExit(main())
