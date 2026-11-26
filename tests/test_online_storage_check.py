"""Check that storage verification survives processes and detects lost/corrupt data."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_storage_probe_round_trip_and_loss(tmp_path):
    env = dict(os.environ, DATABASE_URL='sqlite:///' + str(tmp_path / 'private.db'),
               ONLINE_INSTRUCTION_MEDIA_DIR=str(tmp_path / 'media'))
    script = str(ROOT / 'scripts/check_online_instruction_storage.py')
    def run(*args):
        result = subprocess.run([sys.executable, script, *args], env=env, cwd=ROOT,
                                text=True, capture_output=True, check=False)
        return result.returncode, json.loads(result.stdout)
    code, first = run('--initialize')
    assert code == 0
    marker = first['marker']
    assert run('--expected-marker', marker)[0] == 0
    assert run('--initialize')[0] == 1
    assert run('--expected-marker', 'wrong')[0] == 1
    probe = tmp_path / 'media/.wsbco-online-storage-check.json'
    original = probe.read_bytes()
    probe.write_bytes(original + b' ')
    assert run('--expected-marker', marker)[0] == 1
    probe.write_bytes(original)
    assert run('--expected-marker', marker)[0] == 0
    (tmp_path / 'private.db').unlink()
    assert run('--expected-marker', marker)[0] == 1
    probe.unlink()
    code, lost = run('--expected-marker', marker)
    assert code == 1 and 'missing' in lost['message'].lower()
