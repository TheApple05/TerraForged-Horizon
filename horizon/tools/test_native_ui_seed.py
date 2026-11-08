"""The live UI and save checker accept Minecraft's signed-long seed range."""
import argparse, subprocess, sys, unittest
from pathlib import Path
from verify_native_ui import seed_value

class SeedTests(unittest.TestCase):
    def test_signed_long_boundaries(self):
        for value in (0, -1, 8675309, -(1<<63), (1<<63)-1):
            self.assertEqual(seed_value(str(value)), value)
        for text in ('', '1.5', str(-(1<<63)-1), str(1<<63)):
            with self.assertRaises(argparse.ArgumentTypeError):seed_value(text)

    def test_fixed_classic_coordinates_refuse_another_seed_before_any_stage_access(self):
        script=Path(__file__).with_name('verify_native_ui.py')
        command=[sys.executable,str(script),'--workspace','missing','--resources','missing','--hmod','missing','--report','missing','--seed','0','--classic']
        run=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(run.returncode,2)
        self.assertIn('Classic target coordinates are qualified only for seed 8675309',run.stderr)

if __name__=='__main__':unittest.main()
