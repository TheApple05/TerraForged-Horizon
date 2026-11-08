from pathlib import Path
import datetime as dt,hashlib,json,os,re,shutil,subprocess,time
root=Path(__file__).resolve().parent;host=Path("C:/Users/Main/Documents/Codex/TerraForged/build/qa/horizon/launcher-modpack-worktree");base=root.parent/"launcher-standard-v1"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
build=json.loads((root/"build-receipt.json").read_text(encoding="utf-8"));assert build["status"]=="compiled" and build["exitCode"]==0
exe=base/"bin/horizon-launcher-static.exe";assert not exe.exists();shutil.copy2(Path(build["executable"]),exe);assert sha(exe)==build["executableSha256"]
rules=json.loads((base/"environment.json").read_text(encoding="utf-8"))
runtime={k:v for k,v in os.environ.items() if k not in rules["remove"] and not any(k.startswith(p) for p in rules["removePrefixes"])};runtime.update(rules["overrides"])
for k in ("RUSTFLAGS","CARGO_ENCODED_RUSTFLAGS","CARGO_TARGET_DIR","RUSTC_WRAPPER","RUSTC_WORKSPACE_WRAPPER"):runtime.pop(k,None)
runtime.update(CARGO_NET_OFFLINE="true",CARGO_BUILD_JOBS="4");runtime["HORIZON_MOD_INDEX"]=str(root.parent/"launcher-dev7-preparation-v1/fixtures-v2/local-index.json")
testenv=dict(runtime,RUSTFLAGS="-C target-feature=+crt-static",CARGO_TARGET_DIR=str(root/"target"))
version=base/"homes/launcher/versions/native-f43eebf-9667ade2485e";record=version/"native-mods.json";client=version/"horizon-client.exe";before={str(p):sha(p) for p in (record,client)}
d={"status":"running","sourceCommit":build["sourceCommit"],"launcherSha256":sha(exe),"compiledLauncher":str(exe),"commands":[],"nativeVersion":"native-f43eebf-9667ade2485e","startedAtUtc":dt.datetime.now(dt.timezone.utc).isoformat(),"before":before}
receipt=root/"qualification.json";assert not receipt.exists()
def save():
    part=receipt.with_suffix(".tmp");part.write_text(json.dumps(d,indent=2)+"\n",encoding="utf-8",newline="\n")
    for n in range(6):
        try:part.replace(receipt);return
        except PermissionError:
            if n==5:raise
            time.sleep(.15*(n+1))
def run(label,args,env,expected=0,timeout=1200):
    e={"label":label,"argv":args,"expectedExitCode":expected,"startedAtUtc":dt.datetime.now(dt.timezone.utc).isoformat()};d["commands"].append(e);save();start=time.monotonic()
    with (root/(label+".stdout.log")).open("xb") as out,(root/(label+".stderr.log")).open("xb") as err:
        child=subprocess.Popen(args,cwd=host,env=env,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW);e["pid"]=child.pid;save()
        try:code=child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:child.kill();code=child.wait();e["ownTimeoutKill"]=True
    e.update(exitCode=code,exitCodeUnsignedHex=f"0x{code&0xffffffff:08x}",elapsedSeconds=time.monotonic()-start,stdoutSha256=sha(root/(label+".stdout.log")),stderrSha256=sha(root/(label+".stderr.log")));save()
    if code!=expected or e.get("ownTimeoutKill"):raise RuntimeError(label+" unexpected exit")
    return (root/(label+".stdout.log")).read_text(encoding="utf-8")
try:
    run("launcher-imports",["python",str(host/"tools/check_imports.py"),str(exe)],runtime)
    run("client-imports",["python",str(host/"tools/check_imports.py"),str(client)],runtime)
    text=run("static-tests",["cargo","+stable","test","--offline","--locked","--release","--manifest-path",str(host/"launcher/Cargo.toml"),"--lib","--bin","horizon-launcher"],testenv)
    d["testSummaries"]=re.findall(r"test result: ok[.] ([0-9]+) passed; ([0-9]+) failed; ([0-9]+) ignored",text);assert [int(v[0]) for v in d["testSummaries"]]==[510,97],d["testSummaries"]
    run("version",[str(exe),"--version"],runtime)
    cached=run("cached-native-build",[str(exe),"native-build","--instance","pack:terraforged_launcher_qa_dev7","--version","1860b66439c6c0c07afd1a13252c1cf9405fb38e","--profile","performance","--trust-native-code"],runtime)
    run("strict-owner-gate",[str(exe),"play","--instance","pack:terraforged_launcher_qa_dev7"],runtime,expected=1)
    assert "sign in" in (root/"strict-owner-gate.stderr.log").read_text(encoding="utf-8").lower()
    d["after"]={p:sha(Path(p)) for p in before};assert d["before"]==d["after"]
    d["status"]="passed-static-launcher-qualification"
except BaseException as error:d.update(status="failed",error=str(error),errorType=type(error).__name__)
d["completedAtUtc"]=dt.datetime.now(dt.timezone.utc).isoformat();save();print(json.dumps({k:d.get(k) for k in ("status","error","launcherSha256","testSummaries")}));raise SystemExit(0 if d["status"]=="passed-static-launcher-qualification" else 1)
