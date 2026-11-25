import json, pathlib, tempfile, unittest, subprocess, sys, shutil
from unittest.mock import patch
from jsonschema import Draft202012Validator
from navi_core import cli

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=pathlib.Path(self.tmp.name)/"fixture"; self.root.mkdir()
    def write(self,p,content):
        f=self.root/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(content,encoding="utf-8")
    def doc(self):
        self.write("README.md","[guide](guide.md)\n");self.write("guide.md","# guide\n")
        cli.init(self.root,"documentation","private")
    def test_schemas(self):
        for name in cli.CONTRACTS:
            with self.subTest(name=name): Draft202012Validator.check_schema(json.loads(cli.RES.joinpath(f"contracts/{name}.schema.json").read_text()))
    def test_detect_backend(self):
        self.write("package.json",'{"dependencies":{"hono":"4"},"scripts":{"verify":"test"}}');self.write("tsconfig.json","{}")
        self.assertEqual(cli.detect(self.root),["typescript-backend"])
    def test_ambiguous_detection(self):
        self.write("pyproject.toml","");self.write("CMakeLists.txt","")
        with self.assertRaises(cli.NaviError):cli.init(self.root,None,"unknown")
    def test_init_no_overwrite(self):
        self.doc();p=self.root/".navi/project.toml";before=p.read_bytes()
        with self.assertRaises(cli.NaviError):cli.init(self.root,"documentation","public")
        self.assertEqual(p.read_bytes(),before)
    def test_manifest_privacy_and_injection(self):
        self.doc();d=cli.load_manifest(self.root);d["knowledge"]["public_export"]=True
        with self.assertRaises(cli.NaviError):cli.validate("project",d)
        d["knowledge"]["public_export"]=False;d["verification"]["command"]="arbitrary"
        with self.assertRaises(cli.NaviError):cli.validate("project",d)
    def test_dry_run_no_process(self):
        self.doc()
        with patch("subprocess.run") as runner:
            self.assertEqual(cli.verify(self.root)["status"],"planned");runner.assert_not_called()
    def test_real_docs(self):
        self.doc();self.assertEqual(cli.verify(self.root,True)["results"][0]["checked_links"],1)
        (self.root/"guide.md").unlink()
        with self.assertRaises(cli.NaviError):cli.verify(self.root,True)
    def test_planned_profile_fails_closed(self):
        cli.init(self.root,"game-recomp","unknown")
        with self.assertRaises(cli.NaviError):cli.verify(self.root)
    def test_python_real_gate(self):
        self.write("pyproject.toml","");self.write("tests/test_fixture.py","import unittest\nclass T(unittest.TestCase):\n def test_ok(self): self.assertEqual(1,1)\n")
        cli.init(self.root,"python-tooling","private");self.assertEqual(cli.verify(self.root,True)["status"],"passed")
        self.write("tests/test_fixture.py","import unittest\nclass T(unittest.TestCase):\n def test_ok(self): self.fail('intentional fixture')\n")
        with self.assertRaises(cli.NaviError):cli.verify(self.root,True)
    def test_missing_tests(self):
        self.write("pyproject.toml","");cli.init(self.root,"python-tooling","private")
        with self.assertRaises(cli.NaviError):cli.verify(self.root)
    def test_empty_suite_rejected(self):
        self.write("pyproject.toml", ""); self.write("tests/test_empty.py", "# no tests\n")
        cli.init(self.root,"python-tooling","private")
        with self.assertRaises(cli.NaviError): cli.verify(self.root,True)
    @unittest.skipUnless(shutil.which("git") and shutil.which("node"),"git and node required")
    def test_static_real_gate(self):
        self.write("index.html","<html></html>");self.write("main.js","const n = 1;\n")
        subprocess.run(["git","init","-q",str(self.root)],check=True)
        subprocess.run(["git","-C",str(self.root),"add","main.js"],check=True)
        cli.init(self.root,"static-website","private")
        self.assertEqual(cli.verify(self.root,True)["status"],"passed")
        self.write("main.js","const = ;\n")
        with self.assertRaises(cli.NaviError): cli.verify(self.root,True)
    @unittest.skipUnless(shutil.which("cmake") and shutil.which("ctest"),"CMake and CTest required")
    def test_native_real_gate(self):
        self.write("CMakeLists.txt",'cmake_minimum_required(VERSION 3.20)\nproject(Fixture LANGUAGES CXX)\nadd_executable(smoke main.cpp)\nenable_testing()\nadd_test(NAME smoke COMMAND smoke)\n')
        self.write("main.cpp","int main() { return 0; }\n")
        cli.init(self.root,"cpp-native","private")
        self.assertEqual(cli.verify(self.root,True)["status"],"passed")
    def test_backend_node_version_guard(self):
        self.write("package.json",'{"dependencies":{"hono":"4"},"scripts":{"verify":"test"}}');self.write("package-lock.json","{}")
        cli.init(self.root,"typescript-backend","private")
        with patch("navi_core.cli.executable",return_value="node"), patch("subprocess.run",return_value=subprocess.CompletedProcess(["node"],0,"v22.0.0", "")):
            with self.assertRaisesRegex(cli.NaviError,"Node 24"):cli.verify(self.root,True)
    def test_high_risk(self):
        d=dict(schema_version=1,id="T1",project="fixture",goal="Test",acceptance=["works"],risk="critical",state="planned",approval_required=False)
        with self.assertRaises(cli.NaviError):cli.validate("task",d)
    def test_evidence(self):
        d=dict(schema_version=1,requirement="R1",commit="a"*40,command=["test"],status="passed",exit_code=1,artifact_sha256=None)
        with self.assertRaises(cli.NaviError):cli.validate("evidence",d)
    def test_cli(self):
        result=subprocess.run([sys.executable,"-m","navi_core","doctor"],capture_output=True,text=True,check=True);self.assertEqual(json.loads(result.stdout)["version"],"0.3.0rc2")
    def test_backend_real_gate(self):
        if not shutil.which("node") or not shutil.which("npm"):
            self.skipTest("Node and npm required")
        version=subprocess.check_output(["node","--version"],text=True).strip()
        if not version.startswith("v24."):
            self.skipTest("Node 24 required")
        self.write("package.json",'{"name":"fixture","version":"1.0.0","scripts":{"verify":"node --test"}}')
        self.write("package-lock.json",'{"name":"fixture","version":"1.0.0","lockfileVersion":3,"packages":{"":{"name":"fixture","version":"1.0.0"}}}')
        self.write("test.cjs","const test = require('node:test'); const assert = require('node:assert/strict'); test('ok',()=>assert.equal(2+2,4));\n")
        cli.init(self.root,"typescript-backend","private")
        self.assertEqual(cli.verify(self.root,True)["status"],"passed")
        self.write("test.cjs","const test = require('node:test'); test('fail',()=>{throw new Error('expected');});\n")
        with self.assertRaises(cli.NaviError): cli.verify(self.root,True)
