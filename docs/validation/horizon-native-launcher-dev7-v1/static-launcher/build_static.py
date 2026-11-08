from pathlib import Path
import datetime as dt,hashlib,json,os,subprocess,time
root=Path(__file__).resolve().parent
host=Path("C:/Users/Main/Documents/Codex/TerraForged/build/qa/horizon/launcher-modpack-worktree")
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert subprocess.check_output(["git","-C",str(host),"rev-parse","HEAD"],text=True).strip()=="f43eebfc04b73f0c2bbf5048f7a3ab36c240f21d"
assert not subprocess.check_output(["git","-C",str(host),"status","--porcelain"],text=True).strip()
rules=json.loads(Path("D:/Codex-QA/TerraForged-Horizon/launcher-standard-v1/environment.json").read_text(encoding="utf-8"))
env={k:v for k,v in os.environ.items() if k not in rules["remove"] and not any(k.startswith(p) for p in rules["removePrefixes"])}
for key in ("CARGO_ENCODED_RUSTFLAGS","RUSTC_WRAPPER","RUSTC_WORKSPACE_WRAPPER"):env.pop(key,None)
for key in ("HORIZON_HOME","HORIZON_LAUNCHER_HOME","XDG_DATA_HOME","XDG_CONFIG_HOME","HORIZON_LAUNCHER_TRASH","HORIZON_LAUNCHER_CLIPBOARD","HORIZON_LAUNCHER_DESKTOP"):
    p=root/"homes"/key.lower()
    if key=="HORIZON_LAUNCHER_CLIPBOARD":p=p/"clipboard.data";p.parent.mkdir(parents=True)
    else:p.mkdir(parents=True)
    env[key]=str(p)
env.update(HORIZON_NO_KEYCHAIN="1",HORIZON_NO_AUDIO="1",HORIZON_NO_DISCORD="1",HORIZON_LAUNCHER_NO_SELF_UPDATE="1",HORIZON_TELEMETRY_URL="off",CARGO_TARGET_DIR=str(root/"target"),CARGO_BUILD_JOBS="4",CARGO_NET_OFFLINE="true",RUSTFLAGS="-C target-feature=+crt-static")
cmd=["cargo","+stable","build","--offline","--locked","--release","--manifest-path",str(host/"launcher/Cargo.toml"),"--bin","horizon-launcher"]
d={"status":"starting","sourceCommit":"f43eebfc04b73f0c2bbf5048f7a3ab36c240f21d","command":cmd,"rustflags":env["RUSTFLAGS"],"startedAtUtc":dt.datetime.now(dt.timezone.utc).isoformat(),"rustc":subprocess.check_output(["rustc","+stable","-Vv"],text=True),"scope":"Portable launcher rebuild only; no game/assets/auth/account interaction","jobs":4}
receipt=root/"build-receipt.json"
def save():
    tmp=receipt.with_suffix(".tmp");tmp.write_text(json.dumps(d,indent=2)+"\n",encoding="utf-8");tmp.replace(receipt)
save();start=time.monotonic()
with (root/"build.stdout.log").open("xb") as out,(root/"build.stderr.log").open("xb") as err:
    child=subprocess.Popen(cmd,cwd=host,env=env,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW);d.update(status="running",pid=child.pid);save()
    while child.poll() is None:
        d["updatedAtUtc"]=dt.datetime.now(dt.timezone.utc).isoformat();d["elapsedSeconds"]=time.monotonic()-start;save();time.sleep(5)
    d.update(status="compiled" if child.returncode==0 else "failed",exitCode=child.returncode,elapsedSeconds=time.monotonic()-start,completedAtUtc=dt.datetime.now(dt.timezone.utc).isoformat())
exe=root/"target/release/horizon-launcher.exe"
if child.returncode==0:d.update(executable=str(exe),executableSha256=sha(exe),bytes=exe.stat().st_size)
save();print(json.dumps(d));raise SystemExit(child.returncode)
