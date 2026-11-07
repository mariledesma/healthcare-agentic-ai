"""Persistence/API contracts run in a subprocess with no production DB access."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class StorageContractTests(unittest.TestCase):
    def test_persistence_review_and_history_contracts(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            environment={**os.environ,'DATABASE_URL':'sqlite:///'+str(Path(folder)/'isolated.db'),
                         'PYTHONPATH':str(root)}
            result=subprocess.run([sys.executable,str(root/'tests/storage_contract_worker.py')],cwd=root,
                env=environment,text=True,capture_output=True,timeout=40)
        self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
        self.assertEqual(json.loads(result.stdout)['checks'],'passed')
