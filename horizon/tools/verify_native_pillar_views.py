"""Capture two lower-camera geometry smoke views from a copied, completed QA world.

The source world's client must already be closed. This tool never builds artifacts,
creates a world, or opens the source world; only its fresh ordinary copy is played.
Screenshots require a separate human image review and do not establish Java parity.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys
import time
import zipfile

# Import only the existing ordinary-copy helper, without creating source-tree pyc files.
sys.dont_write_bytecode = True
from verify_native_ui import copy_prepared_resources

ROOT = Path(__file__).resolve().parents[2]
QA_ROOT = ROOT / "build/qa/horizon"
HOME_VARIABLES = (
    "HORIZON_HOME", "HORIZON_LAUNCHER_HOME", "XDG_DATA_HOME", "XDG_CONFIG_HOME",
    "HORIZON_LAUNCHER_TRASH", "HORIZON_LAUNCHER_CLIPBOARD", "HORIZON_LAUNCHER_DESKTOP",
)
VIEWS = (
    ("reterraforged:stone_forest", 36, 135, 20, "lower-stone_forest"),
    ("reterraforged:bryce", 48, 135, 25, "lower-bryce"),
)


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha(path):
    """Stream hashes; bounded retries cover brief Windows reader contention."""
    for attempt in range(5):
        try:
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            return digest.hexdigest()
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(.15 * (attempt + 1))


def plain_stat(path, *, reject_hardlinks=False):
    value = path.lstat()
    if stat.S_ISLNK(value.st_mode) or getattr(value, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
        raise ValueError("Links and reparse points are forbidden: " + str(path))
    if reject_hardlinks and stat.S_ISREG(value.st_mode) and value.st_nlink != 1:
        raise ValueError("Hardlinked world files are forbidden: " + str(path))
    return value


def qa_path(path, label):
    """Require both the written path and its resolution to stay in this checkout's QA."""
    original = path.absolute()
    boundary = QA_ROOT.resolve()
    resolved = original.resolve(strict=True)
    if not original.is_relative_to(boundary) or not resolved.is_relative_to(boundary):
        raise ValueError(label + " must be below " + str(boundary))
    for ancestor in (original, *original.parents):
        plain_stat(ancestor)
        if ancestor == boundary:
            break
    return resolved


def snapshot_tree(source):
    """Hash every ordinary source-world file, including unexpected extra files."""
    if not stat.S_ISDIR(plain_stat(source).st_mode):
        raise ValueError("World source must be a directory")
    files = {}

    def walk_error(error):
        raise error

    for current, children, names in os.walk(source, followlinks=False, onerror=walk_error):
        current = Path(current)
        plain_stat(current)
        for name in children:
            if not stat.S_ISDIR(plain_stat(current / name).st_mode):
                raise ValueError("World directories must be ordinary directories")
        for name in sorted(names):
            path = current / name
            if not stat.S_ISREG(plain_stat(path, reject_hardlinks=True).st_mode):
                raise ValueError("World contains a nonregular file: " + str(path))
            files[path.relative_to(source).as_posix()] = sha(path)
    return dict(sorted(files.items()))


def critical_resources(source):
    paths = [source / name for name in ("horizon-prepare.json", "horizon-resources.json", "facts.json")]
    worldgen = source / "worldgen"
    if not stat.S_ISDIR(plain_stat(worldgen).st_mode):
        raise ValueError("Prepared resources lack a worldgen directory")

    def walk_error(error):
        raise error

    for current, children, names in os.walk(worldgen, followlinks=False, onerror=walk_error):
        current = Path(current)
        plain_stat(current)
        for name in children:
            plain_stat(current / name)
        paths.extend(current / name for name in names if name.endswith(".json"))
    result = {}
    for path in sorted(paths):
        if not stat.S_ISREG(plain_stat(path).st_mode):
            raise ValueError("Critical resource must be an ordinary file: " + str(path))
        result[path.relative_to(source).as_posix()] = sha(path)
    return result


def atomic_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")
    for attempt in range(6):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(.15 * (attempt + 1))


def visible_terrain(snapshot, block):
    renderer = snapshot.get("renderer") or {}
    return bool(
        block.get("loaded") and snapshot.get("chunks", 0) >= 81
        and renderer.get("resident_sections", 0) > 0 and renderer.get("drawn_sections", 0) > 0
        and not snapshot.get("pending_chunks", 0) and not snapshot.get("pending_uploads", 0)
        and not any((snapshot.get("streaming") or {}).values())
    )


def validate_stage(workspace, artifact):
    stage_file = workspace.parent / "stage-result.json"
    stage = json.loads(stage_file.read_text(encoding="utf-8"))
    if not stage.get("worldPresetUiIncluded"):
        raise ValueError("The stage must include native world-preset UI registration")
    if stage.get("stagedWorkspace") and Path(stage["stagedWorkspace"]).resolve() != workspace:
        raise ValueError("stage-result.json names a different workspace")
    for name, digest in stage["inputFiles"].items():
        path = (ROOT / name).resolve(strict=True)
        if not path.is_relative_to(ROOT) or sha(path) != digest:
            raise ValueError("Restage changed source " + name)
    package_file = artifact.with_suffix(artifact.suffix + ".json")
    package = json.loads(package_file.read_text(encoding="utf-8"))
    if package["sha256"] != sha(artifact) or package["stageResultSha256"] != sha(stage_file):
        raise ValueError("Package does not match this exact stage")
    bundle = workspace.parent / "mods/terraforged_native"
    if not stat.S_ISDIR(plain_stat(bundle).st_mode):
        raise ValueError("Staged source bundle must be an ordinary directory")

    def walk_error(error):
        raise error

    with zipfile.ZipFile(artifact) as archive:
        for current, children, names in os.walk(bundle, followlinks=False, onerror=walk_error):
            current = Path(current)
            plain_stat(current)
            for name in children:
                plain_stat(current / name)
            for name in names:
                path = current / name
                if not stat.S_ISREG(plain_stat(path).st_mode):
                    raise ValueError("Staged bundle contains a nonregular file")
                member = "mixins/terraforged_native/" + path.relative_to(bundle).as_posix()
                if archive.read(member) != path.read_bytes():
                    raise ValueError("Packaged source differs from staged bundle: " + member)
    return stage, stage_file, package_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("workspace", "resources", "hmod", "world", "report"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    try:
        workspace = qa_path(args.workspace, "Staged workspace")
        resources = qa_path(args.resources, "Own-QA prepared resources")
        source_world = qa_path(args.world, "Completed UI QA world")
        if workspace.name != "staged" or not workspace.is_dir():
            raise ValueError("--workspace must name the existing staged workspace")
        if not resources.is_dir() or not (source_world / "level.dat").is_file():
            raise ValueError("Existing prepared resources and a completed saved world are required")
        if resources.is_relative_to(source_world) or source_world.is_relative_to(resources):
            raise ValueError("Prepared resources and the source world must be separate trees")
        artifact = args.hmod.resolve(strict=True)
        if not stat.S_ISREG(plain_stat(artifact).st_mode):
            raise ValueError("HMOD must be an ordinary existing file")
        report_path = args.report.resolve()
        if report_path.suffix != ".json":
            raise ValueError("Use a fresh .json report path")
        if not any(report_path.is_relative_to(path.resolve()) for path in (ROOT / "docs/validation", QA_ROOT)):
            raise ValueError("Report must be below this checkout's docs/validation or build/qa/horizon")
        if report_path.exists() or report_path.with_name(report_path.name + ".tmp").exists():
            raise ValueError("Refusing to replace existing evidence or its temporary report")
        if report_path.is_relative_to(source_world) or report_path.is_relative_to(resources):
            raise ValueError("Report must be outside both read-only source trees")
        work = workspace.parent / report_path.stem
        if work.exists() or work == workspace or work.is_relative_to(source_world) or work.is_relative_to(resources):
            raise ValueError("Choose a report stem with a fresh, separate work directory next to staged")
    except (OSError, ValueError) as error:
        parser.error(str(error))

    started = time.monotonic()
    report = {
        "schemaVersion": 1, "status": "running", "startedAtUtc": utc_now(),
        "scope": "Two lower-camera geometry smoke candidates from an ordinary copy of a completed UI QA world",
        "workspace": str(workspace), "preparedResourcesPath": str(resources),
        "sourceWorldPath": str(source_world), "hmodPath": str(artifact), "workDirectory": str(work),
        "sourceWorldClientClosedRequiredBeforeInvocation": True,
        "sourceWorldClientClosureVerifiedByRunner": False,
        "copiedWorldModifiedIntentionally": True, "sourceWorldOpenedByClient": False,
        "preparedResourcesReadOnly": True, "compilationPerformed": False,
        "creationViaUi": False, "qaSpawnSupplied": False, "gameAssetsDownloaded": False,
        "renderDistanceChunks": 6, "simulationDistanceChunks": 3, "maxFps": 30,
        "offscreen": True, "imageSize": [1280, 720], "renderedImagesNeedReview": True,
        "visibilityChecks": [], "renderedViews": [], "controlCommands": [], "phaseTimings": [],
        "notCovered": [
            "Independent Java whole-feature or scenery parity", "Beauty or player visual acceptance",
            "Natural creation/spawn or all-17-biome acceptance (covered separately by the source UI QA run)",
            "Saved FULL biome-vector verification", "Standard launcher installation",
            "Controlled native performance or mod combinations", "Private player worlds or AppData Horizon home",
        ],
    }
    process = None
    game_stdout = game_stderr = None
    source_before = resources_before = None
    copied_world = game = socket = ctl = None
    env = None
    sequence = 0
    report_reserved = False
    phase_started = started

    def checkpoint(phase):
        nonlocal phase_started
        now = time.monotonic()
        if phase != report.get("phase"):
            if report["phaseTimings"]:
                report["phaseTimings"][-1]["elapsedSeconds"] = now - phase_started
            report["phaseTimings"].append({"phase": phase, "startedAtUtc": utc_now()})
            phase_started = now
        report["phase"] = phase
        report["phaseTimings"][-1]["elapsedSeconds"] = now - phase_started
        report["updatedAtUtc"] = utc_now()
        report["elapsedSeconds"] = now - started
        atomic_json(report_path, report)

    def control(words, timeout=30):
        nonlocal sequence
        sequence += 1
        prefix = work / f"ctl-{sequence:04d}-{words[0]}"
        command = [str(ctl), "--socket", str(socket), *words]
        entry = {"sequence": sequence, "arguments": words, "startedAtUtc": utc_now(),
                 "timeoutSeconds": timeout, "stdoutPath": str(prefix) + ".stdout.log",
                 "stderrPath": str(prefix) + ".stderr.log"}
        report["controlCommands"].append(entry)
        began = time.monotonic()
        child = None
        try:
            with Path(entry["stdoutPath"]).open("xb") as out, Path(entry["stderrPath"]).open("xb") as err:
                child = subprocess.Popen(command, cwd=game, env=env, stdout=out, stderr=err,
                                         creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                entry["pid"] = child.pid
                try:
                    entry["exitCode"] = child.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    entry["timedOut"] = True
                    child.kill()
                    entry["exitCode"] = child.wait(timeout=10)
                    raise
            if entry["exitCode"]:
                raise RuntimeError(f"Control {words[0]} exited {entry['exitCode']}; see preserved logs")
            lines = Path(entry["stdoutPath"]).read_text(encoding="utf-8", errors="replace").strip().splitlines()
            reply = json.loads(lines[-1]) if lines else {}
            if not isinstance(reply, dict) or not reply:
                raise RuntimeError("Control returned no JSON object for " + words[0])
            if "error" in reply or reply.get("ok") is False:
                raise RuntimeError(f"Game rejected {words[0]}: {reply}")
            return reply
        except BaseException as error:
            entry["error"] = str(error)
            raise
        finally:
            if child is not None and child.poll() is None:
                pending_error = sys.exc_info()[0] is not None
                try:
                    child.kill()
                    child.wait(timeout=10)
                except Exception as error:
                    entry["cleanupError"] = str(error)
                    if not pending_error:
                        raise
            entry["elapsedSeconds"] = time.monotonic() - began
            entry["completedAtUtc"] = utc_now()

    def poll(predicate, timeout, description):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("Client exited while " + description)
            state = control(["state"], min(30, max(.1, deadline - time.monotonic())))
            if predicate(state):
                return state
            time.sleep(.3)
        raise RuntimeError("Timed out " + description)

    def look(yaw, pitch):
        player = control(["state"])["player"]
        control(["turn", str(yaw - player["yaw"]), str(pitch - player["pitch"])])
        control(["wait", "20"])

    def visible(x, y, z, label):
        began = time.monotonic()
        deadline = began + 420
        next_progress = began
        evidence = {"label": label, "target": [x, y, z], "deadlineSeconds": 420,
                    "startedAtUtc": utc_now(), "status": "loading", "samples": []}
        report["visibilityChecks"].append(evidence)
        checkpoint("loading " + label)
        try:
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("Client exited while loading " + label)
                snapshot = control(["status"], min(30, max(.1, deadline - time.monotonic())))
                if time.monotonic() >= deadline:
                    break
                block = control(["block", str(x), str(y), str(z)], min(30, max(.1, deadline - time.monotonic())))
                evidence.update(lastStatus=snapshot, lastBlock=block, elapsedSeconds=time.monotonic() - began)
                if visible_terrain(snapshot, block):
                    control(["wait", "20"])
                    evidence["status"] = "visible"
                    return snapshot
                if time.monotonic() >= next_progress:
                    evidence["samples"].append({"elapsedSeconds": time.monotonic() - began, "status": snapshot, "block": block})
                    checkpoint("loading " + label)
                    next_progress = time.monotonic() + 30
                time.sleep(.5)
            evidence["status"] = "timed-out"
            raise RuntimeError("Terrain " + label + " did not become visible within 420 seconds")
        except BaseException as error:
            if evidence["status"] == "loading":
                evidence["status"] = "failed"
            evidence["error"] = str(error)
            raise
        finally:
            evidence.update(elapsedSeconds=time.monotonic() - began, completedAtUtc=utc_now())
            pending_error = sys.exc_info()[0] is not None
            try:
                checkpoint("visibility " + evidence["status"] + ": " + label)
            except Exception as error:
                if not pending_error:
                    raise
                report.setdefault("reportWriteErrors", []).append(str(error))

    def shutdown_client():
        """Give only this Popen client 120 seconds, then terminate only its PID."""
        if process is None:
            return
        cleanup = report.setdefault("clientShutdown", {"startedAtUtc": utc_now(), "pid": process.pid})
        began = time.monotonic()
        if process.poll() is None:
            deadline = began + 120
            try:
                control(["quit"], 120)
                process.wait(timeout=max(.1, deadline - time.monotonic()))
                cleanup["method"] = "control-quit"
            except Exception as error:
                cleanup["gracefulError"] = str(error)
                if process.poll() is None:
                    process.terminate()
                    cleanup["method"] = "own-process-terminate"
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        cleanup["method"] = "own-process-kill"
                        process.wait(timeout=10)
                else:
                    cleanup["method"] = "exited-during-control-quit"
        else:
            cleanup.setdefault("method", "already-exited")
        cleanup.update(exitCode=process.poll(), elapsedSeconds=time.monotonic() - began, completedAtUtc=utc_now())
        report["client"]["exitCode"] = process.poll()

    try:
        work.mkdir(exist_ok=False)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(report, indent=2) + "\n")
        report_reserved = True
        shutil.copy2(Path(__file__), work / "verifier-source.py")
        helper = Path(__file__).with_name("verify_native_ui.py")
        shutil.copy2(helper, work / "copy-helper-source.py")
        report["verifierSourceSha256"] = sha(work / "verifier-source.py")
        report["copyHelperSourceSha256"] = sha(work / "copy-helper-source.py")
        checkpoint("validating exact stage and artifacts")
        stage, stage_file, package_file = validate_stage(workspace, artifact)
        suffix = ".exe" if os.name == "nt" else ""
        client = workspace / "target/fast" / ("horizon-client" + suffix)
        ctl = workspace / "target/fast" / ("horizon-ctl" + suffix)
        for path in (client, ctl):
            if not stat.S_ISREG(plain_stat(path).st_mode):
                raise ValueError("Exact staged executable missing: " + str(path))
        pinned = {str(path): sha(path) for path in (stage_file, artifact, package_file, client, ctl)}
        report.update(horizonRevision=stage["horizonRevision"], stageResultSha256=sha(stage_file),
                      hmodSha256=sha(artifact), packageMetadataSha256=sha(package_file), stageInputFilesSha256=stage["inputFiles"],
                      artifactsSha256={path.name: sha(path) for path in (client, ctl)}, pinnedFilesSha256=pinned)
        targets_file = ROOT / "horizon/tests/fixtures/classic-runtime-v1/targets.json"
        targets = json.loads(targets_file.read_text(encoding="utf-8"))
        if targets.get("seed") != 8675309:
            raise ValueError("Unexpected classic fixture seed")
        report["classicTargetsSha256"] = sha(targets_file)
        report["classicTargetOrder"] = [view[0] for view in VIEWS]
        env = dict(os.environ, HORIZON_NO_AUDIO="1", HORIZON_NO_DISCORD="1",
                   HORIZON_LAUNCHER_NO_SELF_UPDATE="1", HORIZON_TELEMETRY_URL="off", HORIZON_PLAYER_NAME="TerraForgedQA")
        env.pop("CARGO_TARGET_DIR", None)
        for name in HOME_VARIABLES:
            path = work / "homes" / name.lower()
            path.mkdir(parents=True, exist_ok=False)
            env[name] = str(path.resolve())
        report["isolatedHomes"] = {name: env[name] for name in HOME_VARIABLES}
        report["qaEnvironment"] = {name: env[name] for name in ("HORIZON_NO_AUDIO", "HORIZON_NO_DISCORD", "HORIZON_LAUNCHER_NO_SELF_UPDATE", "HORIZON_TELEMETRY_URL")}
        game = Path(env["HORIZON_HOME"])
        socket = game / "control.sock"
        report["controlSocketPath"] = str(socket)
        (game / "options.txt").write_text("onboardAccessibility:false\nrenderDistance:6\nsimulationDistance:3\nmaxFps:30\ntutorialStep:none\n", encoding="utf-8", newline="\n")
        checkpoint("hashing read-only source world and resources")
        source_before = snapshot_tree(source_world)
        resources_before = critical_resources(resources)
        report["sourceWorldFilesSha256Before"] = source_before
        report["checkedResourceFilesSha256Before"] = resources_before
        copied_world = game / "saves" / source_world.name
        copied_world.parent.mkdir()
        report["copiedWorldPath"] = str(copied_world)

        def progress(value):
            report["worldCopy"] = value
            checkpoint("copying source world into isolated home")

        copy_prepared_resources(source_world, copied_world, progress, workers=2)
        copied_before = snapshot_tree(copied_world)
        report["copiedWorldFilesSha256BeforeLaunch"] = copied_before
        report["copiedWorldStartMatchesSource"] = copied_before == source_before
        report["sourceWorldUnchangedAfterCopy"] = snapshot_tree(source_world) == source_before
        if not report["copiedWorldStartMatchesSource"] or not report["sourceWorldUnchangedAfterCopy"]:
            raise ValueError("World source changed or its ordinary copy differs; client not launched")
        if critical_resources(resources) != resources_before:
            raise ValueError("Prepared resources changed before launch")
        if not all(sha(Path(path)) == digest for path, digest in pinned.items()):
            raise ValueError("Exact stage, HMOD metadata or executables changed before launch")
        smoke = work / "game-smoke.json"
        command = [str(client), "--resources", str(resources), "--game-dir", str(game), "--home", str(game),
                   "--dev-mod", str(artifact), "--name", "TerraForgedQA", "--offscreen", "--control",
                   "--control-socket", str(socket), "--render-distance", "6", "--width", "1280", "--height", "720",
                   "--timeout-seconds", "2400", "--smoke-report", str(smoke), "--world", str(copied_world)]
        report["client"] = {"command": command, "stdoutPath": str(work / "game.stdout.log"),
                            "stderrPath": str(work / "game.stderr.log"), "smokeReportPath": str(smoke)}
        checkpoint("starting copied-world client")
        game_stdout = (work / "game.stdout.log").open("xb")
        game_stderr = (work / "game.stderr.log").open("xb")
        process = subprocess.Popen(command, cwd=game, env=env, stdout=game_stdout, stderr=game_stderr,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        report["client"].update(pid=process.pid, startedAtUtc=utc_now())
        checkpoint("waiting for own control endpoint")
        endpoint_deadline = time.monotonic() + 180
        while time.monotonic() < endpoint_deadline:
            if process.poll() is not None:
                raise RuntimeError("Client exited during startup")
            try:
                control(["state"], min(5, max(.1, endpoint_deadline - time.monotonic())))
                break
            except (RuntimeError, subprocess.TimeoutExpired):
                time.sleep(1)
        else:
            raise RuntimeError("Own control endpoint did not start within 180 seconds")
        checkpoint("waiting for copied world to play")
        poll(lambda state: state.get("screen") == "playing" and state.get("player") is not None,
             420, "loading copied saved world")
        control(["wait-ready", "180"], 210)
        report["copiedWorldInitialState"] = control(["state"])
        control(["command", "gamemode spectator @s"])
        poll(lambda state: state.get("gamemode") == "spectator", 30, "entering QA spectator mode")
        rule_reply = control(["command", "gamerule minecraft:advance_time false"])
        control(["time", "6000"])
        control(["wait", "40"])
        qa_state = control(["state"])
        if (qa_state.get("time") or {}).get("day_time") != 6000:
            raise RuntimeError("QA noon did not remain frozen after 40 game ticks")
        report["qaControls"] = {"gamemode": "spectator", "advance_time": False, "day_time": 6000,
                                "frozenNoonVerifiedAfterTicks": 40, "gameruleReply": rule_reply, "state": qa_state}
        for name, rise, yaw, pitch, image_name in VIEWS:
            point = targets["targets"][name]
            x, y, z = (point[key] for key in ("x", "y", "z"))
            camera = [x + .5, min(290, y + rise), z + .5]
            checkpoint("teleporting " + name)
            control(["command", f"tp @s {camera[0]} {camera[1]} {camera[2]}"])
            look(yaw, pitch)
            shown = visible(x, y, z, name)
            image = work / (image_name + ".png")
            control(["screenshot", str(image)], 60)
            if not image.is_file() or image.stat().st_size < 1024:
                raise RuntimeError("Screenshot missing or too small: " + image.name)
            with image.open("rb") as stream:
                header = stream.read(24)
            if header[:8] != b"\x89PNG\r\n\x1a\n" or struct.unpack(">II", header[16:24]) != (1280, 720):
                raise RuntimeError("Screenshot is not the requested 1280x720 PNG")
            report["renderedViews"].append({"biome": name, "target": [x, y, z], "camera": camera,
                "cameraRiseBlocks": rise, "yaw": yaw, "pitch": pitch, "state": control(["state"]),
                "visibleTerrainState": shown, "screenshot": {"path": str(image), "sha256": sha(image)}})
            checkpoint("captured " + image_name)
        checkpoint("saving and quitting own copied-world client")
        shutdown_client()
        if process.returncode:
            raise RuntimeError("Own client exit " + str(process.returncode))
        report["status"] = "raw-pass-awaiting-image-review"
    except BaseException as error:
        report["status"] = "failed"
        report["error"] = str(error) or type(error).__name__
        report["errorType"] = type(error).__name__
    finally:
        if process is not None and process.poll() is None:
            try:
                if report_reserved:
                    checkpoint("cleaning up own client")
            except Exception as error:
                report.setdefault("reportWriteErrors", []).append(str(error))
            try:
                shutdown_client()
            except Exception as error:
                report.setdefault("cleanupErrors", []).append(str(error))
                report["status"] = "failed"
                report.setdefault("error", "Own client cleanup failed: " + str(error))
        for stream in (game_stdout, game_stderr):
            if stream is not None:
                try:
                    stream.close()
                except Exception as error:
                    report.setdefault("cleanupErrors", []).append(str(error))
                    report["status"] = "failed"
                    report.setdefault("error", "Could not close own client log")
        for label, reader, before, after_key, unchanged_key in (
            ("source world", lambda: snapshot_tree(source_world), source_before, "sourceWorldFilesSha256After", "sourceWorldUnchanged"),
            ("prepared resources", lambda: critical_resources(resources), resources_before, "checkedResourceFilesSha256After", "checkedResourcesUnchanged"),
        ):
            if before is None:
                continue
            try:
                after = reader()
                report[after_key] = after
                report[unchanged_key] = after == before
                if not report[unchanged_key]:
                    raise ValueError("Read-only " + label + " changed")
            except Exception as error:
                report[unchanged_key] = False
                report.setdefault("integrityErrors", []).append(str(error))
                report["status"] = "failed"
                report.setdefault("error", str(error))
        if copied_world is not None and copied_world.is_dir():
            try:
                report["copiedWorldFilesSha256After"] = snapshot_tree(copied_world)
            except Exception as error:
                report.setdefault("integrityErrors", []).append("Copied world hash: " + str(error))
                report["status"] = "failed"
                report.setdefault("error", "Could not hash saved copied world")
        if "pinnedFilesSha256" in report:
            try:
                report["pinnedFilesUnchanged"] = all(sha(Path(path)) == digest for path, digest in report["pinnedFilesSha256"].items())
                if not report["pinnedFilesUnchanged"]:
                    raise ValueError("Exact stage, HMOD metadata or staged executables changed")
            except Exception as error:
                report["pinnedFilesUnchanged"] = False
                report["status"] = "failed"
                report.setdefault("error", str(error))
        try:
            report["gameLogsSha256"] = {path.name: sha(path) for path in (work / "game.stdout.log", work / "game.stderr.log") if path.is_file()}
        except Exception as error:
            report.setdefault("integrityErrors", []).append("Own client log hash: " + str(error))
            report["status"] = "failed"
            report.setdefault("error", "Could not hash preserved client logs")
        report["completedAtUtc"] = utc_now()
        if report_reserved:
            try:
                checkpoint("completed")
            except Exception as error:
                report["status"] = "failed"
                report.setdefault("error", "Final report write failed: " + str(error))
                report.setdefault("reportWriteErrors", []).append(str(error))
    print(json.dumps({key: report.get(key) for key in ("status", "error", "horizonRevision", "completedAtUtc")}, indent=2))
    return 0 if report["status"] == "raw-pass-awaiting-image-review" else 1


if __name__ == "__main__":
    raise SystemExit(main())
