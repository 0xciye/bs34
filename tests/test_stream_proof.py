"""Run the real native capture-layer checks on disposable, off-screen windows."""
from pathlib import Path
import subprocess
import unittest

class StreamProofTests(unittest.TestCase):
    def test_native_capture_layer_keeps_game_capturable(self):
        project=Path(__file__).resolve().parents[1]
        executable=project/'build/Release/bs_stream_proof_check.exe'
        if not executable.is_file():
            self.skipTest('Build bs_stream_proof_check with BS_MENU_PREVIEW=ON first')
        result=subprocess.run([str(executable)],cwd=project,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('Capture layer checks passed',result.stdout)

if __name__=='__main__':unittest.main()
