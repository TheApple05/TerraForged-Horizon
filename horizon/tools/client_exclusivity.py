"""Reject client timing runs contaminated by another Horizon client."""
from __future__ import annotations
import ctypes, ctypes.wintypes as wintypes, datetime, os, subprocess, threading


def horizon_client_pids():
    if os.name != 'nt':
        result = subprocess.run(['ps', '-A', '-o', 'pid=,comm='], capture_output=True, text=True, check=True)
        return [int(row[0]) for line in result.stdout.splitlines()
                if len(row := line.split()) == 2 and row[1] == 'horizon-client']
    class Entry(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('usage', wintypes.DWORD), ('pid', wintypes.DWORD),
                    ('heap', ctypes.c_size_t), ('module', wintypes.DWORD), ('threads', wintypes.DWORD),
                    ('parent', wintypes.DWORD), ('priority', wintypes.LONG), ('flags', wintypes.DWORD),
                    ('exe', wintypes.WCHAR * 260)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.Process32NextW.argtypes = kernel.Process32FirstW.argtypes
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if not snapshot or snapshot == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        entry = Entry(); entry.size = ctypes.sizeof(entry)
        found = kernel.Process32FirstW(snapshot, ctypes.byref(entry)); pids = []
        while found:
            if entry.exe.lower() == 'horizon-client.exe': pids.append(entry.pid)
            found = kernel.Process32NextW(snapshot, ctypes.byref(entry))
        if ctypes.get_last_error() != 18: raise ctypes.WinError(ctypes.get_last_error())
        return pids
    finally:
        kernel.CloseHandle(snapshot)


class ExclusiveClientGuard:
    def __init__(self, owned_pid):
        self.owned_pid = owned_pid
        self.lock = threading.Lock(); self.stop = threading.Event()
        self.state = {'ownedPid': owned_pid, 'intervalSeconds': .25, 'samples': 0,
                      'maximumClientCount': 0, 'firstOtherClients': None, 'watchError': None}
        self.sample()
        self.thread = threading.Thread(target=self.watch, daemon=True)
        self.thread.start()

    def sample(self):
        try:
            pids = horizon_client_pids(); other = [pid for pid in pids if pid != self.owned_pid]
            with self.lock:
                self.state['samples'] += 1
                self.state['maximumClientCount'] = max(self.state['maximumClientCount'], len(pids))
                if other and self.state['firstOtherClients'] is None:
                    self.state['firstOtherClients'] = {'pids': other, 'atUtc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
        except Exception as error:
            with self.lock: self.state['watchError'] = str(error)

    def watch(self):
        while not self.stop.wait(.25): self.sample()

    def snapshot(self):
        with self.lock: return dict(self.state)

    def check(self):
        state = self.snapshot()
        if state['firstOtherClients'] or state['watchError']:
            raise RuntimeError('Exclusive-client observation failed; timing invalid: ' + str(state))
        return state

    def close(self):
        self.stop.set(); self.thread.join(5)
        if self.thread.is_alive(): raise RuntimeError('Client observer did not stop')


def self_test():
    from unittest.mock import patch
    with patch(__name__ + '.horizon_client_pids', return_value=[11]) as listing:
        guard = ExclusiveClientGuard(11)
        try:
            assert guard.check()['firstOtherClients'] is None
            listing.return_value = [11, 22]; guard.sample()
            assert guard.snapshot()['firstOtherClients']['pids'] == [22]
            try: guard.check()
            except RuntimeError: pass
            else: raise AssertionError('Another client was accepted')
        finally: guard.close()
    with patch(__name__ + '.horizon_client_pids', side_effect=OSError('controlled scan failure')):
        guard = ExclusiveClientGuard(11)
        try:
            try: guard.check()
            except RuntimeError: pass
            else: raise AssertionError('A failed observer was accepted')
        finally: guard.close()

