import json
from pathlib import Path
import tempfile
import unittest
from navi_core import cli, nef

class NEFTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base=Path(tmp.name).resolve()
        self.root=self.base/"project";self.root.mkdir()
        self.store=self.base/"private";self.store.mkdir()
    def brief(self,**overrides):
        return dict({"schema_version":1,"goal":"Export","deliverable":"CSV","complexity":"nontrivial",
                     "acceptance":["fixture passes"],"constraints_state":"known","ambiguity":"none",
                     "questions":[],"risk":"low","approved":False},**overrides)
    def lesson(self,**overrides):
        return dict({"schema_version":1,"id":"csv","kind":"preference","summary":"Use CSV header",
                     "source_reference":"approved decision","validation":"fixture checked"},**overrides)
    def test_profiles(self):
        self.assertTrue(set(cli.REGISTRY)<=set(nef.standard()["profiles"]))
        self.assertEqual(len(nef.standard()["profiles"]),19)
        self.assertEqual(nef.standard("game-recomp")["profiles"]["game-recomp"]["verification_gate"],"planned")
    def test_plan_apply_idempotent(self):
        self.assertEqual(nef.scaffold(self.root,"godot-game")["status"],"planned")
        self.assertEqual(list(self.root.iterdir()),[])
        r=nef.scaffold(self.root,"godot-game",apply=True)
        self.assertEqual(len(r["created"]),4)
        self.assertTrue((self.root/"docs/HANDOFF.md").is_file())
        self.assertFalse((self.root/"scenes").exists())
        self.assertEqual(nef.scaffold(self.root,"godot-game",apply=True)["created"],[])
    def test_alternative_preserved(self):
        p=self.root/"ROADMAP.md";p.write_text("# existing")
        r=nef.migration(self.root,"documentation",apply=True)
        self.assertEqual(p.read_text(),"# existing")
        self.assertNotIn("docs/ROADMAP.md",r["created"])
        self.assertFalse((self.root/"docs/ROADMAP.md").exists())
    def test_explicit_folders(self):
        nef.scaffold(self.root,"game-recomp",apply=True,include_folders=True)
        self.assertTrue((self.root/"runtime").is_dir())
    def test_blocked_parent(self):
        (self.root/"docs").write_text("existing file")
        with self.assertRaises(cli.NaviError):nef.scaffold(self.root,"documentation",apply=True)
        self.assertFalse((self.root/"README.md").exists())
    def test_no_license_guess(self):
        with self.assertRaises(cli.NaviError):nef.scaffold(self.root,"documentation",["license"],True)
    def test_manifest_profile_conflict(self):
        cli.init(self.root,"documentation","private")
        with self.assertRaises(cli.NaviError):nef.inspect(self.root,"godot-game")
    def test_link_rejected(self):
        target=self.base/"outside";target.mkdir()
        try:(self.root/"docs").symlink_to(target,target_is_directory=True)
        except OSError:self.skipTest("symlink privilege unavailable")
        self.assertEqual(nef.scaffold(self.root,"documentation",apply=True)["status"],"blocked")
        self.assertEqual(list(target.iterdir()),[])
    def test_intake(self):
        self.assertEqual(nef.intake(self.brief())["status"],"ready")
        for case in ({"goal":" "},{"deliverable":""},{"acceptance":[]},{"constraints_state":"unknown"},
                     {"ambiguity":"material"},{"questions":["Which output?"]},{"risk":"high"}):
            self.assertEqual(nef.intake(self.brief(**case))["status"],"clarify")
        self.assertEqual(nef.intake(self.brief(complexity="simple",acceptance=[]))["status"],"ready")
        with self.assertRaises(cli.NaviError):nef.intake(self.brief(raw_prompt="not accepted"))
    def test_learning_review_and_scope(self):
        self.assertEqual(nef.learn(self.root,self.store,self.lesson())["status"],"review-required")
        self.assertEqual(list(self.store.iterdir()),[])
        self.assertEqual(nef.learn(self.root,self.store,self.lesson(),True)["status"],"saved")
        self.assertEqual(nef.recall(self.root,self.store,["csv"])["lessons"][0]["summary"],"Use CSV header")
        with self.assertRaises(FileExistsError):nef.learn(self.root,self.store,self.lesson(),True)
        with self.assertRaises(cli.NaviError):nef.recall(self.root,self.store,["csv"],1)
        other=self.base/"other";other.mkdir()
        with self.assertRaises(cli.NaviError):nef.recall(other,self.store,["csv"])
        with self.assertRaises(cli.NaviError):nef.learn(self.root,self.root,self.lesson(),True)
    def test_no_raw_prompts_or_traversal(self):
        with self.assertRaises(cli.NaviError):nef.learn(self.root,self.store,self.lesson(raw_prompt="secret"),True)
        with self.assertRaises(cli.NaviError):nef.recall(self.root,self.store,["../csv"])
    def test_cli_clarification(self):
        p=self.base/"brief.json";p.write_text(json.dumps(self.brief(goal="")))
        self.assertEqual(cli.main(["intake","--brief",str(p)]),1)

    def test_consolidated_mapping(self):
        (self.root/"guide.md").write_text("# existing guide")
        mapping={k:"guide.md" for k in ("overview","architecture","roadmap","handoff")}
        self.assertEqual(nef.scaffold(self.root,"documentation",apply=True,mapping=mapping)["created"],[])
        self.assertEqual(list(self.root.iterdir()),[self.root/"guide.md"])
        with self.assertRaises(cli.NaviError):nef.inspect(self.root,"documentation",{"handoff":"../guide.md"})
        self.assertEqual(nef.scaffold(self.root,"documentation",apply=True,mapping={"handoff":"absent.md"})["status"],"blocked")
    def test_folders_with_document_parents(self):
        result=nef.scaffold(self.root,"documentation",apply=True,include_folders=True)
        self.assertEqual(result["status"],"applied")
        self.assertTrue((self.root/"docs/HANDOFF.md").is_file())
    def test_lexical_scoped_recall(self):
        other=self.base/"other";other.mkdir()
        nef.learn(self.root,self.store,self.lesson(),True)
        nef.learn(other,self.store,self.lesson(id="other"),True)
        nef.learn(self.root,self.store,self.lesson(id="unrelated",summary="Use XML only"),True)
        query=self.base/"query.txt";query.write_text("Please export CSV with header")
        data=nef.search_lessons(self.root,self.store,query)
        self.assertEqual([x["id"] for x in data["lessons"]],["csv"])
        self.assertNotIn("Please export",json.dumps(data))
        self.assertEqual(len(list(self.store.iterdir())),3)
