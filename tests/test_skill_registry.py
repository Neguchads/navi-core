import hashlib
import json
import pathlib
import tempfile
import unittest
import zipfile
from navi_core.cli import NaviError
from navi_core import skill_registry as s

class SkillRegistryTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=pathlib.Path(tmp.name)

    def archive(self,name,entries):
        path=self.root/name
        with zipfile.ZipFile(path,"w") as z:
            for k,v in entries.items(): z.writestr(k,v)
        return path

    def approval(self,slug,raw,**overrides):
        a={"id":slug,"sha256":hashlib.sha256(raw.encode()).hexdigest(),"decision":"approved",
           "license":"MIT","reviewed_by":"local reviewer","review_reference":"review-1",
           "risk":"low","hosts":["codex"],"tags":["architecture"]}
        a.update(overrides)
        return a

    def review(self,*a):
        return {"schema_version":1,"scope":"private-local","approvals":list(a)}

    def test_duplicates_and_conflicts(self):
        p=self.archive("a.zip",{"one/plan/SKILL.md":"a","two/plan/SKILL.md":"a","three/plan/SKILL.md":"b"})
        d=s.scan([p])
        self.assertEqual(d["summary"],{"occurrences":3,"ids":1,"distinct_contents":2,"conflicting_ids":1})
        self.assertEqual(d["skills"][0]["state"],"conflict")
        self.assertNotIn("text",json.dumps(d))

    def test_no_implicit_approval(self):
        p=self.archive("a.zip",{"plan/SKILL.md":"a"})
        d=s.scan([p])
        self.assertEqual(s.select(d,self.review(),"codex","plan",1000,"low")["selected"],[])

    def test_explicit_variant_and_budget(self):
        p=self.archive("a.zip",{"one/plan/SKILL.md":"a","two/plan/SKILL.md":"bb"})
        d=s.scan([p]);a=self.approval("plan","bb")
        self.assertEqual(s.select(d,self.review(a),"codex","plan",1,"low")["selected"],[])
        sel=s.select(d,self.review(a),"codex","plan",2000,"low")
        self.assertEqual(sel["selected"][0]["sha256"],a["sha256"])
        self.assertEqual(s.packet(sel,[p],2000)["skills"][0]["text"],"bb")

    def test_ambiguous_and_stale_review(self):
        p=self.archive("a.zip",{"one/plan/SKILL.md":"a","two/plan/SKILL.md":"b"})
        d=s.scan([p]);a=self.approval("plan","a");b=self.approval("plan","b")
        with self.assertRaises(NaviError):s.select(d,self.review(a,b),"codex","plan",1000,"low")
        with self.assertRaises(NaviError):s.select(d,self.review(self.approval("plan","c")),"codex","plan",1000,"low")

    def test_host_risk_and_license(self):
        p=self.archive("a.zip",{"plan/SKILL.md":"a"})
        d=s.scan([p]);a=self.approval("plan","a",risk="high")
        self.assertEqual(s.select(d,self.review(a),"codex","plan",1000,"low")["selected"],[])
        self.assertEqual(s.select(d,self.review(a),"claude","plan",1000,"critical")["selected"],[])
        with self.assertRaises(NaviError):s.select(d,self.review(self.approval("plan","a",license="unverified")),"codex","plan",1000,"low")

    def test_no_extraction_and_unsafe_path(self):
        p=self.archive("a.zip",{"../plan/SKILL.md":"danger"})
        with self.assertRaises(NaviError):s.scan([p])
        self.assertFalse((self.root.parent/"plan").exists())

    def test_archive_replacement(self):
        p=self.archive("a.zip",{"plan/SKILL.md":"a"})
        d=s.scan([p]);sel=s.select(d,self.review(self.approval("plan","a")),"codex","plan",2000,"low")
        self.archive("a.zip",{"plan/SKILL.md":"b"})
        with self.assertRaises(NaviError):s.packet(sel,[p],2000)

    def test_packet_serialized_budget(self):
        p=self.archive("a.zip",{"plan/SKILL.md":"a"})
        sel=s.select(s.scan([p]),self.review(self.approval("plan","a")),"codex","plan",1,"low")
        with self.assertRaises(NaviError):s.packet(sel,[p],1)

    def test_output_exclusive(self):
        path=self.root/"registry.json";s.write_private(path,{"a":1})
        with self.assertRaises(FileExistsError):s.write_private(path,{"a":2})
        self.assertEqual(s.read_json(path),{"a":1})

    def test_duplicate_json_keys(self):
        path=self.root/"a.json";path.write_text('{"x":1,"x":2}')
        with self.assertRaises(NaviError):s.read_json(path)
