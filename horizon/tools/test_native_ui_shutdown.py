"""Exit evidence distinguishes an unexpected exit from verifier cleanup."""
import subprocess,sys,unittest
from unittest.mock import Mock
from verify_native_ui import shutdown_owned_client

class ShutdownTests(unittest.TestCase):
    def test_existing_crash_does_not_request_shutdown(self):
        process=Mock(pid=123);process.poll.return_value=-1073741819;quit_client=Mock();evidence={}
        shutdown_owned_client(process,quit_client,evidence)
        self.assertEqual(evidence['initialExit'],{'exitCode':-1073741819,'exitCodeUnsignedHex':'0xc0000005'})
        self.assertEqual(evidence['finalExit'],evidence['initialExit']);self.assertEqual(evidence['actions'],[])
        quit_client.assert_not_called();process.terminate.assert_not_called();process.kill.assert_not_called()

    def test_graceful_quit_records_only_its_own_action(self):
        process=Mock(pid=124);process.poll.return_value=None
        def quit_client():process.poll.return_value=0
        evidence={};shutdown_owned_client(process,quit_client,evidence)
        self.assertIsNone(evidence['initialExit']['exitCode']);self.assertEqual(evidence['finalExit']['exitCode'],0)
        self.assertEqual(evidence['actions'],['control-quit']);process.terminate.assert_not_called()

    def test_timeout_records_termination_and_kill_without_relabeling_initial_exit(self):
        process=Mock(pid=125);process.poll.return_value=None
        process.wait.side_effect=[subprocess.TimeoutExpired('own-client',5),subprocess.TimeoutExpired('own-client',10),None]
        process.kill.side_effect=lambda:setattr(process.poll,'return_value',1)
        evidence={};quit_client=Mock(side_effect=RuntimeError('control unavailable'))
        shutdown_owned_client(process,quit_client,evidence)
        self.assertIsNone(evidence['initialExit']['exitCode']);self.assertEqual(evidence['finalExit']['exitCode'],1)
        self.assertEqual(evidence['actions'],['control-quit','wait-after-control-error','own-process-terminate','own-process-kill'])
        self.assertEqual(evidence['gracefulError'],'control unavailable')

    def test_client_finishing_after_control_closes_keeps_its_natural_exit(self):
        process=subprocess.Popen([sys.executable,'-c','import time; time.sleep(.1)'])
        evidence={};quit_client=Mock(side_effect=RuntimeError('control already closed'))
        shutdown_owned_client(process,quit_client,evidence)
        self.assertIsNone(evidence['initialExit']['exitCode'])
        self.assertEqual(evidence['finalExit']['exitCode'],0)
        self.assertEqual(evidence['actions'],['control-quit','wait-after-control-error'])

if __name__=='__main__':unittest.main()
