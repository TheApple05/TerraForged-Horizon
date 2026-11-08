"""Compare real native clients in ABBA order, then save/reopen each scratch world.

The fixture supplies seed 8675309, a spectator spawn and disabled structures.
Timings include the integrated server, streaming and renderer; they are not pure
kernel timings. A separate UI run must qualify natural spawn and structures.
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, math, os, platform, shutil, statistics, subprocess, time
from pathlib import Path
from benchmark_kernel_sampler import memory_reader
from verify_native_ui import copy_prepared_resources, exit_details, shutdown_owned_client

ROOT = Path(__file__).resolve().parents[2]
STAGES = {'queued', 'generating', 'decorating', 'finishing', 'lighting', 'meshing'}
TARGETS = [('fir_forest', (0, 70, -43692)), ('cold_steppe', (-126976, 136, 76052)), ('bryce', (-118532, 99, -107012))]
HOME_KEYS = ('HORIZON_HOME', 'HORIZON_LAUNCHER_HOME', 'XDG_DATA_HOME', 'XDG_CONFIG_HOME', 'HORIZON_LAUNCHER_TRASH', 'HORIZON_LAUNCHER_CLIPBOARD', 'HORIZON_LAUNCHER_DESKTOP')
QA_ENV = dict(HORIZON_NO_AUDIO='1', HORIZON_NO_DISCORD='1', HORIZON_LAUNCHER_NO_SELF_UPDATE='1', HORIZON_TELEMETRY_URL='off', HORIZON_PLAYER_NAME='TerraForgedQA', HORIZON_JOB_THREADS='4', RUST_BACKTRACE='1')


def utc(): return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_checkpoint(temporary, destination):
    # Windows report readers can briefly deny rename while holding the old file.
    for attempt in range(30):
        try:
            temporary.replace(destination)
            return
        except PermissionError:
            if attempt == 29: raise
            time.sleep(.1)


def stages(value):
    if isinstance(value, list):
        try: value = dict(value)
        except (TypeError, ValueError): return None
    if not isinstance(value, dict) or not STAGES.issubset(value): return None
    if any(not isinstance(n, (int, float)) or not math.isfinite(n) or n < 0 for n in value.values()): return None
    return value


def quiet(value, ignore_meshing=False):
    value = stages(value)
    ignored = {'protos', 'meshing'} if ignore_meshing else {'protos'}
    return value is not None and all(n == 0 for name, n in value.items() if name not in ignored)


def near(status, camera):
    player = status.get('player') or {}
    position = player.get('position')
    return (isinstance(position, list) and len(position) == 3
            and all(isinstance(n, (int, float)) and math.isfinite(n) for n in position)
            and sum((a - b) ** 2 for a, b in zip(position, camera)) < 4)


class Readiness:
    """Confirm both ends of the integrated client; never infer work from an empty queue alone."""
    def __init__(self, camera, distance, initial_counts=None):
        self.camera = camera
        self.minimum = int(.8 * math.pi * distance ** 2)
        self.initial_counts = initial_counts
        self.counts_changed = False
        self.metrics = {}
        self.server_count = None
        self.server_streak = 0
        self.memory_at = -math.inf
        self.view_counts = None
        self.view_since = None
        self.view_samples = 0

    def observe(self, status, block, memory, elapsed, fresh_memory=False):
        counts = (status.get('chunks'), status.get('generated_chunks'))
        if self.initial_counts is None: self.initial_counts = counts
        self.counts_changed |= counts != self.initial_counts
        full = isinstance(counts[0], (int, float)) and counts[0] >= self.minimum
        resident = near(status, self.camera) and block.get('loaded') is True
        if resident: self.metrics.setdefault('firstTargetResidentSeconds', elapsed)
        gate = resident and full and (self.counts_changed or elapsed >= 5)
        if fresh_memory:
            self.memory_at = elapsed
            server = (memory or {}).get('server_generation') or {}
            server_count = ((memory or {}).get('server_columns') or {}).get('columns')
            if gate and quiet(server.get('stages'), ignore_meshing=True):
                self.metrics.setdefault('firstServerGenerationLightQuietSeconds', elapsed)
            if gate and quiet(server.get('stages')) and isinstance(server_count, int):
                self.metrics.setdefault('firstServerQuietSeconds', elapsed)
                self.server_streak = self.server_streak + 1 if server_count == self.server_count else 1
            else: self.server_streak = 0
            self.server_count = server_count
        renderer = status.get('renderer') or {}
        ready = (gate and self.server_streak >= 2 and elapsed - self.memory_at <= 5
                 and status.get('pending_chunks') == 0 and status.get('pending_uploads') == 0
                 and quiet(status.get('streaming'))
                 and renderer.get('resident_sections', 0) > 0 and renderer.get('drawn_sections', 0) > 0)
        view_counts = (*counts, renderer.get('resident_sections'))
        if not ready:
            self.view_counts = None; self.view_since = None; self.view_samples = 0
        elif view_counts != self.view_counts:
            self.view_counts = view_counts; self.view_since = elapsed; self.view_samples = 1
        else: self.view_samples += 1
        if ready and self.view_samples >= 2 and elapsed - self.view_since >= 1:
            self.metrics.setdefault('viewReadySeconds', elapsed)
            return True
        return False


def self_test():
    from tempfile import TemporaryDirectory
    from unittest.mock import patch
    with TemporaryDirectory() as folder:
        destination = Path(folder) / 'report.json'
        temporary = Path(folder) / 'report.json.tmp'
        destination.write_text('old')
        temporary.write_text('new')
        original_replace = Path.replace
        attempts = []
        def transient_lock(path, target):
            attempts.append(path)
            if len(attempts) == 1: raise PermissionError('controlled Windows reader lock')
            return original_replace(path, target)
        with patch.object(Path, 'replace', transient_lock), patch('time.sleep'):
            replace_checkpoint(temporary, destination)
        assert len(attempts) == 2 and destination.read_text() == 'new' and not temporary.exists()
    status = {'player': {'position': [1., 90., 2.]}, 'chunks': 100, 'generated_chunks': 100,
              'pending_chunks': 0, 'pending_uploads': 0, 'streaming': {**dict.fromkeys(STAGES, 0), 'protos': 7},
              'renderer': {'resident_sections': 10, 'drawn_sections': 5}}
    memory = {'server_columns': {'columns': 120}, 'server_generation': {'stages': list(status['streaming'].items())}}
    probe = Readiness([1., 90., 2.], 6, (100, 100))
    assert not probe.observe(status, {'loaded': True}, memory, 0, True)
    assert 'firstServerQuietSeconds' not in probe.metrics  # Initial empty queues are not evidence of new work.
    assert not probe.observe(status, {'loaded': False}, memory, 5, True)
    assert not probe.observe(status, {'loaded': True}, memory, 6, True)
    assert not probe.observe(status, {'loaded': True}, memory, 8, True)
    assert not probe.observe(status, {'loaded': True}, memory, 8.5)
    assert probe.observe(status, {'loaded': True}, memory, 9)
    assert probe.metrics['firstServerQuietSeconds'] == 6
    assert not Readiness([999., 90., 2.], 6).observe(status, {'loaded': True}, memory, 10, True)
    assert not quiet(None) and not quiet({}) and not quiet([['queued', 0]])
    assert quiet(memory['server_generation']['stages'])
    assert not quiet({**status['streaming'], 'lighting': 1})
    assert quiet({**status['streaming'], 'meshing': 1}, ignore_meshing=True)
    assert not quiet({**status['streaming'], 'meshing': 1})
    assert not quiet({**status['streaming'], 'queued': float('nan')})
    working = Readiness([1., 90., 2.], 6, (0, 0))
    busy_server = {'server_columns': {'columns': 120}, 'server_generation': {'stages': {**status['streaming'], 'meshing': 1}}}
    assert not working.observe(status, {'loaded': True}, busy_server, 1, True)
    assert working.metrics['firstServerGenerationLightQuietSeconds'] == 1
    assert 'firstServerQuietSeconds' not in working.metrics
    blocked = Readiness([1., 90., 2.], 6, (0, 0))
    for elapsed in (1, 3, 5):
        assert not blocked.observe({**status, 'pending_uploads': 1}, {'loaded': True}, memory, elapsed, True)
    assert not blocked.observe(status, {'loaded': True}, memory, 20)  # Stale server observations cannot pass.
    print('NATIVE_CLIENT_BENCH_SELF_TEST_OK target position queues protos staleMemory stableWindow')


def checked_resources(source):
    files = [source / name for name in ('horizon-prepare.json', 'horizon-resources.json', 'facts.json')]
    files += sorted((source / 'worldgen').rglob('*.json'))
    if not (source / 'worldgen').is_dir(): raise ValueError('Prepared worldgen directory missing')
    return {p.relative_to(source).as_posix(): sha(p) for p in files}


def unchanged(source, expected):
    return all((source / name).is_file() and sha(source / name) == digest for name, digest in expected.items())


def fixture_run(args, action, world, resources, env, folder, evidence):
    command = [str(args.fixture), action, str(world), str(ROOT / 'horizon/native-content/data/terraforged/worldgen/world_preset/default.json'), str(resources)]
    evidence.update(command=command, startedAtUtc=utc(), timeoutSeconds=600)
    started = time.monotonic()
    try:
        with (folder / (action + '.stdout.log')).open('x', encoding='utf-8') as out, (folder / (action + '.stderr.log')).open('x', encoding='utf-8') as err:
            result = subprocess.run(command, cwd=folder, env=env, stdout=out, stderr=err, timeout=600)
        evidence.update(exit_details(result.returncode))
        if result.returncode: raise RuntimeError(f'Fixture {action} exited {result.returncode}')
        evidence['result'] = json.loads((folder / (action + '.stdout.log')).read_text(encoding='utf-8'))
        return evidence['result']
    except Exception as error:
        evidence.update(error=str(error), errorType=type(error).__name__); raise
    finally: evidence.update(elapsedSeconds=time.monotonic() - started, completedAtUtc=utc())


def client_session(args, version, row, phase, targets, game, world, resources, env, checkpoint):
    folder = Path(row['work']) / phase; folder.mkdir()
    evidence = {'status': 'running', 'views': [], 'startedAtUtc': utc()}; row[phase] = evidence
    client = getattr(args, version + '_client'); hmod = getattr(args, version + '_hmod')
    endpoint = game / ('control-' + phase + '.json' if os.name == 'nt' else 'control-' + phase + '.sock')
    command = [str(client), '--resources', str(resources), '--game-dir', str(game), '--home', str(game), '--world', str(world),
               '--name', 'TerraForgedQA', '--offscreen', '--no-pause', '--control', '--control-socket', str(endpoint),
               '--render-distance', str(args.render_distance), '--width', '1280', '--height', '720',
               '--timeout-seconds', str(args.startup_timeout + args.load_timeout * (len(targets) + 1) + 180),
               '--smoke-report', str(folder / 'smoke.json')]
    if hmod: command += ['--dev-mod', str(hmod)]
    evidence['command'] = command
    started = time.monotonic(); process = None; read_rss = lambda: None; close_rss = lambda: None
    peak_rss = 0; sequence = 0
    with (folder / 'game.log').open('x', encoding='utf-8') as log, (folder / 'control.jsonl').open('x', encoding='utf-8') as control_log:
        def control(words, timeout=10):
            nonlocal sequence, peak_rss
            sequence += 1; at = time.monotonic(); entry = {'sequence': sequence, 'words': words, 'elapsedSeconds': at - started, 'timeoutSeconds': timeout}
            try:
                if process.poll() is not None: raise RuntimeError('Owned client exited: ' + str(exit_details(process.returncode)))
                result = subprocess.run([str(args.ctl), '--socket', str(endpoint), '--timeout', str(timeout), *words], cwd=game, env=env, capture_output=True, text=True, timeout=timeout + 2)
                entry.update(exit_details(result.returncode)); entry.update(stdout=result.stdout, stderr=result.stderr)
                if result.returncode: raise RuntimeError(f'Control {words[0]} exited {result.returncode}')
                lines = result.stdout.strip().splitlines(); reply = json.loads(lines[-1]) if lines else {}
                if 'error' in reply: raise RuntimeError(f'Control {words[0]}: {reply["error"]}')
                return reply
            except subprocess.TimeoutExpired as error:
                entry['stdout'] = error.stdout.decode('utf-8', errors='replace') if isinstance(error.stdout, bytes) else error.stdout
                entry['stderr'] = error.stderr.decode('utf-8', errors='replace') if isinstance(error.stderr, bytes) else error.stderr
                entry['error'] = str(error); raise
            except Exception as error: entry['error'] = str(error); raise
            finally:
                peak_rss = max(peak_rss, read_rss() or 0)
                entry['durationSeconds'] = time.monotonic() - at
                control_log.write(json.dumps(entry) + '\n'); control_log.flush()

        def view(label, point, camera, teleport=True, measured_start=None, collection=None):
            before = control(['status'])
            check = Readiness(camera, args.render_distance, (before.get('chunks'), before.get('generated_chunks')))
            item = {'label': label, 'target': point, 'camera': camera, 'status': 'loading', 'deadlineSeconds': args.load_timeout,
                    'minimumResidentChunks': check.minimum, 'samples': 0, 'memorySamples': 0, 'startedAtUtc': utc()}
            (evidence['views'] if collection is None else collection).append(item); checkpoint(f'{version} {phase} loading {label}')
            at = time.monotonic() if measured_start is None else measured_start
            deadline = time.monotonic() + args.load_timeout; next_memory = at; next_checkpoint = at
            memory = None
            try:
                try: control(['stats', 'reset'])
                except Exception as error: item['frameStatsDiagnostic'] = str(error)
                if teleport:
                    region = world / f'dimensions/minecraft/overworld/region/r.{point[0] >> 9}.{point[2] >> 9}.mca'
                    item['destinationRegionExistedBefore'] = region.exists()
                    if region.exists(): raise RuntimeError('Cold destination region already exists: ' + str(region))
                    at = time.monotonic(); deadline = at + args.load_timeout; next_memory = at; next_checkpoint = at
                    control(['command', 'tp @s ' + ' '.join(map(str, camera))])
                control(['look', '135', '45'])
                while time.monotonic() < deadline:
                    status = control(['status']); block = control(['block', *map(str, point)])
                    now = time.monotonic(); fresh_memory = now >= next_memory
                    if fresh_memory:
                        try: memory = control(['memory'])
                        except Exception as error:
                            memory = None; item['lastMemoryDiagnostic'] = str(error)
                        item['memorySamples'] += 1; next_memory = time.monotonic() + 2
                    elapsed = time.monotonic() - at
                    item['samples'] += 1
                    item['lastStatus'] = {key: status.get(key) for key in ('chunks', 'generated_chunks', 'pending_chunks', 'pending_uploads', 'streaming', 'renderer', 'player')}
                    item['lastBlock'] = block
                    if fresh_memory and memory:
                        item['lastServerMemory'] = {key: memory.get(key) for key in ('process', 'client_columns', 'server_columns', 'server_generation')}
                        resident_mb = (memory.get('process') or {}).get('resident_mb')
                        if isinstance(resident_mb, (int, float)): item['peakCensusResidentMiB'] = max(item.get('peakCensusResidentMiB', 0), resident_mb)
                    ready = check.observe(status, block, memory, elapsed, fresh_memory)
                    item.update(check.metrics); item['elapsedSeconds'] = elapsed
                    if ready:
                        item['status'] = 'ready'
                        try: item['frameStats'] = control(['stats', 'raw'])
                        except Exception as error: item['frameStatsDiagnostic'] = str(error)
                        image = folder / (label + '.png'); control(['screenshot', str(image)], 60)
                        if not image.is_file() or image.stat().st_size < 1024: raise RuntimeError('Missing usable screenshot for ' + label)
                        item['screenshot'] = {'path': str(image), 'sha256': sha(image)}
                        return item
                    if time.monotonic() >= next_checkpoint:
                        checkpoint(f'{version} {phase} loading {label}'); next_checkpoint = time.monotonic() + 2
                    time.sleep(.5)
                raise TimeoutError(f'{label} did not reach confirmed server/client/render readiness in {args.load_timeout} seconds')
            except Exception as error:
                item.update(status='failed', error=str(error), errorType=type(error).__name__); raise
            finally:
                item.update(elapsedSeconds=time.monotonic() - at, completedAtUtc=utc()); checkpoint(f'{version} {phase} {label}: {item["status"]}')

        try:
            process = subprocess.Popen(command, cwd=game, env=env, stdout=log, stderr=subprocess.STDOUT,
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            evidence['pid'] = process.pid
            try: read_rss, close_rss, evidence['residentMetric'] = memory_reader(process.pid)
            except Exception as error: evidence['residentMetricError'] = str(error)
            checkpoint(f'{version} {phase} client started')
            deadline = started + args.startup_timeout
            while True:
                try:
                    initial = control(['status'], 5)
                    if initial.get('player'): break
                except Exception as error:
                    evidence['lastStartupDiagnostic'] = str(error)
                    if process.poll() is not None: raise
                if time.monotonic() >= deadline: raise TimeoutError('Client player/control startup deadline exceeded')
                time.sleep(.5)
            evidence['playerControlReadySeconds'] = time.monotonic() - started
            initial_point, initial_camera = ((8, 100, 8), (8.5, 130., 8.5)) if phase == 'primary' else (TARGETS[-1][1], row['lastCamera'])
            view('initial', initial_point, initial_camera, teleport=False, measured_start=started)
            for label, point in targets:
                rise = 96 if label == 'bryce' else 48
                camera = (point[0] + .5, min(290, point[1] + rise), point[2] + .5)
                if label == 'distant': camera = (16392., 80., -32760.)
                view(label, point, camera)
                row['lastCamera'] = camera
            if phase == 'primary' and version == 'candidate' and row['index'] == 2:
                stress = {'status': 'running', 'scope': 'Untimed cancellation/unload stress after all primary speed samples',
                          'startedAtUtc': utc(), 'steps': [], 'settleViews': []}
                evidence['stabilityStress'] = stress
                far = [(262144., 200., 262144.), (-262144., 200., -262144.)]
                stress['farRegionFilesExistedBefore'] = [{
                    'camera': camera,
                    'regionFileExisted': (world / f'dimensions/minecraft/overworld/region/r.{int(camera[0]) >> 9}.{int(camera[2]) >> 9}.mca').exists()
                } for camera in far]
                stress_started = time.monotonic()
                try:
                    for camera in [*far, row['lastCamera']] * 2:
                        step = {'camera': camera, 'elapsedSeconds': time.monotonic() - stress_started}
                        stress['steps'].append(step); checkpoint('candidate rapid teleport stress')
                        step['reply'] = control(['command', 'tp @s ' + ' '.join(map(str, camera))])
                        step['status'] = control(['status'])
                        time.sleep(.5)
                    view('stress-settle', TARGETS[-1][1], row['lastCamera'], teleport=False, collection=stress['settleViews'])
                    stress['settledMemory'] = control(['memory'])
                    stress['status'] = 'passed'
                except BaseException as error:
                    stress.update(status='failed', error=str(error), errorType=type(error).__name__); raise
                finally:
                    stress.update(elapsedSeconds=time.monotonic() - stress_started, completedAtUtc=utc())
                    checkpoint('candidate rapid teleport stress ' + stress['status'])
            evidence['quitRequestedAtUtc'] = utc(); control(['quit'], 120)
            code = process.wait(timeout=120); evidence.update(exit_details(code))
            if code: raise RuntimeError('Client exited unsuccessfully: ' + str(exit_details(code)))
            evidence['status'] = 'passed'
        except BaseException as error:
            evidence.update(status='failed', error=str(error), errorType=type(error).__name__); raise
        finally:
            if process is not None:
                shutdown_owned_client(process, lambda: control(['quit'], 15), evidence.setdefault('cleanup', {}))
            peak_rss = max(peak_rss, read_rss() or 0); close_rss()
            evidence.update(processPeakResidentBytes=peak_rss, elapsedSeconds=time.monotonic() - started, completedAtUtc=utc())
            control_log.flush(); log.flush()
            evidence['gameLogSha256'] = sha(folder / 'game.log'); evidence['controlLogSha256'] = sha(folder / 'control.jsonl')
            if (folder / 'smoke.json').is_file(): evidence['smokeReportSha256'] = sha(folder / 'smoke.json')
            checkpoint(f'{version} {phase} client {evidence["status"]}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline-client', 'candidate-client', 'ctl', 'fixture', 'resources', 'work', 'report', 'baseline-hmod', 'candidate-hmod'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--render-distance', type=int, default=12)
    parser.add_argument('--startup-timeout', type=int, default=240)
    parser.add_argument('--load-timeout', type=int, default=600)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test: self_test(); return 0
    for name in ('baseline_client', 'candidate_client', 'ctl', 'fixture', 'resources', 'work', 'report'):
        if getattr(args, name) is None: parser.error('--' + name.replace('_', '-') + ' is required')
    for name in ('baseline_client', 'candidate_client', 'ctl', 'fixture', 'resources', 'work', 'report', 'baseline_hmod', 'candidate_hmod'):
        value = getattr(args, name)
        if value is not None: setattr(args, name, value.resolve())
    if bool(args.baseline_hmod) != bool(args.candidate_hmod): parser.error('Supply both hmod paths or neither')
    for name in ('baseline_client', 'candidate_client', 'ctl', 'fixture', 'baseline_hmod', 'candidate_hmod'):
        value = getattr(args, name)
        if value is not None and not value.is_file(): parser.error('Missing artifact: ' + str(value))
    if not 2 <= args.render_distance <= 32 or min(args.startup_timeout, args.load_timeout) < 30: parser.error('Use render distance 2..32 and timeouts of at least 30 seconds')
    if args.work.exists() or args.report.exists(): parser.error('Choose fresh work/report paths; existing evidence is never replaced')
    if args.work.is_relative_to(args.resources) or args.report.is_relative_to(args.resources): parser.error('Evidence must be outside source resources')
    before = checked_resources(args.resources)
    args.work.mkdir(parents=True)
    shutil.copy2(Path(__file__), args.work / 'verifier-source.py')
    report = {'schemaVersion': 1, 'status': 'running', 'startedAtUtc': utc(), 'order': ['baseline', 'candidate', 'candidate', 'baseline'],
              'scope': 'Real integrated native client: supplied seed8675309 spectator spawn, structures disabled, offscreen1280x720, FPS cap60. Cold destination residence, server-stage quiet and renderer readiness are distinct end-to-end observations; no pure chunk-generation throughput claim.',
              'conditions': {'seed': 8675309, 'qaSpawnSupplied': True, 'structuresEnabled': False, 'renderDistanceChunks': args.render_distance, 'simulationDistanceChunks': 5, 'sharedWorkerThreads': 4, 'frameRateCap': 60, 'statusIntervalSeconds': .5, 'serverMemoryIntervalSeconds': 2, 'stableViewSeconds': 1},
              'notCovered': ['Natural spawn/UI creation', 'Structures-enabled stability', 'Whole-world Java block parity', 'Saved classic-biome vectors beyond origin/distant', 'Native tile/river cache counts', 'General modpack or FPS speedup'],
              'counterSemantics': {'generated_chunks': 'Received and disk-loaded columns too; used only as a readiness change signal, never as a fresh-generation count', 'server_generation.caches': 'Host pipeline census, not TerraForged tile/river counts', 'serverGenerationLightQuiet': 'queued/generating/decorating/finishing/lighting zero; meshing excluded', 'serverQuiet': 'All server stages zero except protos; first observation gated on requested residence and changed/full view', 'viewReady': 'Two fresh quiet server samples and client/render readiness, stable resident counts for at least one second'},
              'qaEnvironmentOverrides': QA_ENV, 'otherHostLoadControlled': False,
              'host': {'os': platform.system(), 'osVersion': platform.version(), 'architecture': platform.machine(), 'cpu': platform.processor(), 'logicalProcessors': os.cpu_count()},
              'checkedSourceResourcesSha256': before, 'verifierSha256': sha(Path(__file__)), 'runs': []}
    report['artifacts'] = {name: {'path': str(value), 'sha256': sha(value)} for name in ('baseline_client', 'candidate_client', 'ctl', 'fixture', 'baseline_hmod', 'candidate_hmod') if (value := getattr(args, name)) is not None}
    report['presetSha256'] = sha(ROOT / 'horizon/native-content/data/terraforged/worldgen/world_preset/default.json')
    def checkpoint(phase):
        report.update(phase=phase, updatedAtUtc=utc())
        args.report.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.report.with_name(args.report.name + '.tmp')
        temporary.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n'); replace_checkpoint(temporary, args.report)
    checkpoint('initializing ABBA run')
    try:
        for index, version in enumerate(report['order']):
            folder = args.work / f'{index}-{version}'; folder.mkdir()
            row = {'index': index, 'version': version, 'status': 'running', 'work': str(folder), 'startedAtUtc': utc()}; report['runs'].append(row)
            env = dict(os.environ, **QA_ENV)
            env.pop('HORIZON_SESSION_FILE', None)
            row['qaHomeOverrides'] = {}
            for key in HOME_KEYS:
                path = folder / 'homes' / key.lower(); path.mkdir(parents=True); env[key] = str(path); row['qaHomeOverrides'][key] = str(path)
            temporary = folder / 'temp'; temporary.mkdir()
            for key in ('TEMP', 'TMP'):
                env[key] = str(temporary); row['qaHomeOverrides'][key] = str(temporary)
            game = Path(env['HORIZON_HOME']); world = game / 'saves/NativeQA'; resources = folder / 'prepared-resources'
            (game / 'options.txt').write_text(f'graphicsPreset:"custom"\nonboardAccessibility:false\nrenderDistance:{args.render_distance}\nsimulationDistance:5\nmaxFps:60\nenableVsync:false\ninactivityFpsLimit:"minimized"\npauseOnLostFocus:false\ntutorialStep:none\n', encoding='utf-8')
            row['optionsSha256'] = sha(game / 'options.txt')
            try:
                def progress(value): row['preparedResourceCopy'] = value; checkpoint(f'{index}-{version} copying resources')
                copy_prepared_resources(args.resources, resources, progress)
                row['checkedCopyMatchesBeforeRun'] = unchanged(resources, before)
                if not row['checkedCopyMatchesBeforeRun']: raise RuntimeError('Copied resource inputs differ')
                fixture_run(args, 'init', world, resources, env, folder, row.setdefault('fixtureInitialization', {})); checkpoint(f'{index}-{version} fixture initialized')
                client_session(args, version, row, 'primary', TARGETS, game, world, resources, env, checkpoint)
                client_session(args, version, row, 'reopen', [('distant', (16392, 65, -32760))], game, world, resources, env, checkpoint)
                fixture_run(args, 'check_all', world, resources, env, folder, row.setdefault('savedFullChunkChecks', {}))
                row['status'] = 'passed'
            except BaseException as error:
                row.update(status='failed', error=str(error), errorType=type(error).__name__)
                if not isinstance(error, Exception): raise
            finally:
                row['checkedCopyResourcesUnchanged'] = resources.exists() and unchanged(resources, before)
                if not row['checkedCopyResourcesUnchanged']: row.update(status='failed', resourceError='Checked copied resource inputs changed or incomplete')
                row['completedAtUtc'] = utc(); checkpoint(f'{index}-{version} {row["status"]}')
        report['summary'] = {}
        for label, _ in TARGETS:
            metrics = {}
            for metric in ('firstTargetResidentSeconds', 'firstServerGenerationLightQuietSeconds', 'firstServerQuietSeconds', 'viewReadySeconds'):
                values = {version: [v[metric] for run in report['runs'] if run['version'] == version for v in run.get('primary', {}).get('views', []) if v['label'] == label and v['status'] == 'ready' and metric in v] for version in ('baseline', 'candidate')}
                metrics[metric] = {'secondsByVersion': values, 'completeAbba': all(len(v) == 2 for v in values.values())}
                if metrics[metric]['completeAbba']: metrics[metric]['medianSeconds'] = {name: statistics.median(v) for name, v in values.items()}
            report['summary'][label] = metrics
        report['status'] = 'passed-native-client-abba-save-reopen' if all(run['status'] == 'passed' for run in report['runs']) else 'failed'
    except BaseException as error:
        report.update(status='failed', error=str(error), errorType=type(error).__name__); raise
    finally:
        report['checkedSourceResourcesUnchanged'] = unchanged(args.resources, before)
        report['artifactsUnchanged'] = all(sha(Path(value['path'])) == value['sha256'] for value in report['artifacts'].values())
        if not report['checkedSourceResourcesUnchanged'] or not report['artifactsUnchanged']: report['status'] = 'failed'
        report['completedAtUtc'] = utc(); checkpoint('completed')
    print(json.dumps({'status': report['status'], 'report': str(args.report), 'runStatuses': [row['status'] for row in report['runs']]}, indent=2))
    return 0 if report['status'].startswith('passed-') else 1


if __name__ == '__main__': raise SystemExit(main())
