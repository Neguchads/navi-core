import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from navi_core import installer,cli

class InstallerTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.base=Path(t.name).resolve()
        self.bundle=self.base/"bundle";self.bundle.mkdir()
        self.wheel=self.bundle/"navi_engineering_core-0.6.0rc1-py3-none-any.whl"
        self.wheel.write_bytes(b"fixture only")
        self.manifest=self.bundle/"WHEELS.sha256"
        self.manifest.write_text(hashlib.sha256(self.wheel.read_bytes()).hexdigest()+"  "+self.wheel.name+"\n")
        self.digest=hashlib.sha256(self.manifest.read_bytes()).hexdigest()
        self.destination=self.base/"env"
    def test_plan_and_mismatch(self):
        p=installer.provision(self.manifest,self.digest,self.destination)
        self.assertEqual(p["status"],"planned")
        self.assertFalse(self.destination.exists())
        self.wheel.write_bytes(b"modified")
        with self.assertRaises(cli.NaviError):installer.provision(self.manifest,self.digest,self.destination)
    def test_no_overwrite_or_git(self):
        self.destination.mkdir()
        with self.assertRaises(cli.NaviError):installer.provision(self.manifest,self.digest,self.destination)
        (self.base/".git").mkdir()
        with self.assertRaises(cli.NaviError):installer.provision(self.manifest,self.digest,self.base/"new")
    def test_uninstall_drift(self):
        self.destination.mkdir()
        f=self.destination/"fixture";f.write_text("initial")
        digest,count=installer._inventory(self.destination)
        receipt={"schema_version":1,"version":"0.6.0rc1","manifest_sha256":self.digest,
                 "inventory_sha256":digest,"entries":count,"destination_sha256":hashlib.sha256(__import__("os").fsencode(str(self.destination))).hexdigest()}
        (self.destination/installer.RECEIPT).write_text(json.dumps(receipt))
        f.write_text("changed")
        self.assertEqual(installer.uninstall(self.destination,True)["status"],"review-required")
        self.assertTrue(f.exists())
        f.write_text("initial")
        self.assertEqual(installer.uninstall(self.destination,True)["status"],"removed")
        self.assertFalse(self.destination.exists())
