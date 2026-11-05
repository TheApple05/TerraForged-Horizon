"""Freeze packaged Java marsh material and biome-info noise; never use native outputs as expected values."""
from __future__ import annotations
import argparse,datetime as dt,gzip,hashlib,json,os,re,shutil,socket,struct,subprocess,zipfile
from pathlib import Path
from java_reference import java_reference_root
ROOT=Path(__file__).resolve().parents[2]
PRODUCTION='1c9e5e7e8d286c145a647f466b2f908cda721d10672c40949864f1015570e886'
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('java-home','production-jar','classpath-file','server-instance','work','output'):p.add_argument('--'+name,required=True,type=Path)
    a=p.parse_args();java_reference_root()
    if a.work.exists() or a.output.exists() or not a.work.resolve().is_relative_to((ROOT/'build/qa/horizon').resolve()):p.error('Fresh QA work and fixture paths required')
    jar=a.production_jar.resolve()
    if sha(jar.read_bytes())!=PRODUCTION:raise ValueError('Exact qualified dev23 Fabric artifact required')
    a.work.mkdir(parents=True);classes=a.work/'classes';classes.mkdir();lines=[]
    axes=sorted(set(range(-64,65))|{-30000000,-32768,-16385,-16384,-8193,-128,127,128,129,255,256,1024,16384,30000000})
    for x in axes:
        for z in axes:
            for op in ('noise','info','positive'):lines.append(f'{op}/{x}/{z}\t{op}\t{x}\t{z}')
            for y in (61,62,63):lines.append(f'material/{x}/{z}/{y}\tmaterial\t{x}\t{z}\t{y}')
    region=[0xff800000,0xbf800000,0x80000000,0,1,0x3f800000,0x7f800000,0x7fc00000,0xffc00000]
    for value in (0.6,0.75):
        bits=struct.unpack('>I',struct.pack('>f',value))[0];region.extend(range(bits-3,bits+4))
    for i,bits in enumerate(region):
        for y in (-65,0,61,62,63,319):lines.append(f'select/{i}/{y}\tselect\t{bits:08x}\t{y}\t62')
    inputs=('\n'.join(lines)+'\n').encode();input_file=a.work/'inputs.tsv';input_file.write_bytes(inputs)
    probe=ROOT/'horizon/tests/java/NativeMarshSamplerProbe.java';cp=str(jar)+os.pathsep+a.classpath_file.read_text(encoding='utf-8').strip();suffix='.exe' if os.name=='nt' else ''
    companion=ROOT/'horizon/tests/java/NativeMarshCaptureMod.java'
    result=subprocess.run([str(a.java_home/'bin'/('javac'+suffix)),'--release','25','-encoding','UTF-8','-proc:none','-cp',cp,'-d',str(classes),str(probe),str(companion)],capture_output=True,text=True,timeout=90);(a.work/'compile.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError('Java sampler probe compile failed; see preserved compile log')
    qa=a.work/'marsh-capture-qa.jar'
    with zipfile.ZipFile(qa,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('fabric.mod.json',json.dumps({'schemaVersion':1,'id':'terraforged_marsh_capture_qa','version':'0.1.0','environment':'server','license':'MIT','entrypoints':{'main':['terraforged.qa.NativeMarshCaptureMod']},'depends':{'reterraforged':'*','fabricloader':'>=0.20.1','fabric-lifecycle-events-v1':'*','minecraft':'26.2','java':'>=25'}}))
        for file in sorted(classes.rglob('*.class')):archive.write(file,file.relative_to(classes).as_posix())
    template=a.server_instance.resolve()
    checked={'server.jar':'cdacdfb25898de5e4b4b0e5ddcc2722f77067e46605709c2d886c000ebb63ec5','fabric-server-launch.jar':'121ae339b9b903aaf4fb7b3903fbb5c1e37246ebe14786c2109a2a1eb29e32bc','mods/fabric-api-0.161.0+26.2.jar':'e5b858ceb13290c274e31cb888ff5a1a40cb91067e7ffab0b5b775aec51e216a'}
    if any(sha((template/name).read_bytes())!=digest for name,digest in checked.items()):raise ValueError('Existing local server installation differs')
    captures=[];runs=[]
    for index in range(2):
        instance=a.work/f'server-{index}';instance.mkdir();mods=instance/'mods';mods.mkdir()
        for directory in ('.fabric','libraries','versions'):shutil.copytree(template/directory,instance/directory)
        for name in ('server.jar','fabric-server-launch.jar','fabric-server-launcher.properties','eula.txt'):shutil.copy2(template/name,instance/name)
        shutil.copy2(template/'mods/fabric-api-0.161.0+26.2.jar',mods/'fabric-api-0.161.0+26.2.jar');installed=mods/jar.name;shutil.copy2(jar,installed);shutil.copy2(qa,mods/qa.name)
        if sha(installed.read_bytes())!=PRODUCTION:raise ValueError('Installed production artifact differs')
        with socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
        properties={'server-ip':'127.0.0.1','server-port':port,'online-mode':'false','enable-query':'false','enable-rcon':'false','level-name':'qa-world','level-seed':8675309,'level-type':'minecraft:flat','spawn-protection':0,'view-distance':2,'simulation-distance':2,'max-players':1,'pause-when-empty-seconds':-1,'max-tick-time':60000}
        (instance/'server.properties').write_text('\n'.join(f'{key}={value}' for key,value in properties.items())+'\n',encoding='utf-8')
        env=dict(os.environ,HORIZON_NO_AUDIO='1',HORIZON_NO_DISCORD='1',HORIZON_LAUNCHER_NO_SELF_UPDATE='1',HORIZON_TELEMETRY_URL='off')
        for name in ('HORIZON_HOME','HORIZON_LAUNCHER_HOME','XDG_DATA_HOME','XDG_CONFIG_HOME','HORIZON_LAUNCHER_TRASH','HORIZON_LAUNCHER_CLIPBOARD','HORIZON_LAUNCHER_DESKTOP'):
            home=instance/'homes'/name.lower();home.mkdir(parents=True);env[name]=str(home.resolve())
        file=a.work/f'java-{index}.tsv';command=[str(a.java_home/'bin'/('java'+suffix)),'-Xms256M','-Xmx2G','-XX:ActiveProcessorCount=4','-Dfabric.development=false',f'-Duser.home={instance.resolve() / "homes"}',f'-Dterraforged.qa.inputs={input_file.resolve()}',f'-Dterraforged.qa.production={installed.resolve()}',f'-Dterraforged.qa.output={file.resolve()}','-jar','fabric-server-launch.jar','nogui']
        result=subprocess.run(command,cwd=instance,env=env,capture_output=True,text=True,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        log=result.stdout+result.stderr;(a.work/f'java-{index}.log').write_text(log,encoding='utf-8');match=re.search(r'MARSH_SAMPLER_CAPTURE_OK records=(\d+) pid=(\d+)',log);origins=[line.split('PACKAGED_CLASS_ORIGIN=',1)[1] for line in log.splitlines() if 'PACKAGED_CLASS_ORIGIN=' in line]
        if result.returncode or not match or int(match[1])!=len(lines) or len(origins)!=3 or 'MARSH_FABRIC_SERVER_CAPTURE_OK minecraft=26.2' not in log:raise RuntimeError('Packaged Java producer failed; see preserved process log')
        raw=file.read_bytes();captures.append(raw);runs.append({'pid':int(match[2]),'exitCode':result.returncode,'records':len(lines),'outputSha256':sha(raw),'logSha256':sha(log.encode()),'verifiedPackagedOrigins':origins})
    if captures[0]!=captures[1] or runs[0]['pid']==runs[1]['pid']:raise ValueError('Fresh packaged Java captures differ')
    compressed=gzip.compress(captures[0],mtime=0)
    report={'schemaVersion':1,'status':'frozen-packaged-java-marsh-materials-and-biome-info','capturedAtUtc':dt.datetime.now(dt.timezone.utc).isoformat(),'productionJarSha256':PRODUCTION,'recordCount':len(lines),'inputsSha256':sha(inputs),'fixtureSha256':sha(compressed),'uncompressedValuesSha256':sha(captures[0]),'probeSourceSha256Lf':sha(probe.read_bytes().replace(b'\r\n',b'\n')),'companionSourceSha256Lf':sha(companion.read_bytes().replace(b'\r\n',b'\n')),'qaJarSha256':sha(qa.read_bytes()),'localServerInputsSha256':checked,'gameAssetsDownloaded':False,'runtime':'Two actual Fabric 0.20.1 / Minecraft 26.2 dedicated servers with Fabric API 0.161.0+26.2; reused copied local cached installation, no installer or download step','producerReports':runs,'freshJavaRunsAgree':True,'nativeExpectedValuesUsed':False,'scope':'Packaged SwampSurfaceFeature material graph/private getMaterial, real Minecraft 26.2 biome-info noise, and projected Java float-vs-double material threshold comparisons. Dense negative/distant coordinates and boundary values.','notCovered':['Full marsh block-placement loop','Heightmap/fluid/write semantics in actual worlds','Natural scenery, structures or performance']}
    a.output.mkdir(parents=True);(a.output/'inputs.tsv').write_bytes(inputs);(a.output/'values.tsv.gz').write_bytes(compressed);(a.output/'metadata.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps({'status':report['status'],'recordCount':len(lines),'freshJavaRunsAgree':True}))
if __name__=='__main__':main()
