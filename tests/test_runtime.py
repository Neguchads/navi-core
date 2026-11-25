import json
import tempfile
import unittest
from pathlib import Path
from navi_core import runtime,runtime_hooks,cli

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.base=Path(t.name).resolve()
        self.root=self.base/"project";self.root.mkdir()
        self.store=self.base/"private";self.store.mkdir()
    def brief(self,**kw):
        return dict({"schema_version":1,"goal":"Export CSV","deliverable":"CLI","complexity":"nontrivial",
                     "acceptance":["fixture passes"],"constraints_state":"known","ambiguity":"none",
                     "questions":[],"risk":"low","approved":False},**kw)
    def handoff(self,**kw):
        return dict({"schema_version":1,"objective":"Export CSV","revision":None,"state":"in-progress",
                     "completed":[],"blockers":[],"decisions":[],"next_steps":["Test"],"rollback":"",
                     "acceptance":[],"verification":[]},**kw)
    def test_lifecycle_and_recovery(self):
        self.assertEqual(runtime.start(self.root,self.store,"task","generic")["state"],"awaiting-brief")
        with self.assertRaises(cli.NaviError):runtime.advance(self.root,self.store,"task",0,"BeforeExecution")
        r=runtime.advance(self.root,self.store,"task",0,"UserPrompt",brief=self.brief(goal=""))
        self.assertEqual(r["status"],"clarify")
        with self.assertRaises(cli.NaviError):runtime.advance(self.root,self.store,"task",0,"UserPrompt",brief=self.brief())
        r=runtime.advance(self.root,self.store,"task",1,"UserPrompt",brief=self.brief())
        self.assertEqual(r["state"],"ready")
        runtime.advance(self.root,self.store,"task",2,"BeforeExecution")
        runtime.advance(self.root,self.store,"task",3,"AfterExecution")
        r=runtime.advance(self.root,self.store,"task",4,"Checkpoint",handoff=self.handoff(),reviewed=True)
        self.assertEqual(runtime.context(self.root,self.store,"task")["handoff"]["next_steps"],["Test"])
        done=self.handoff(state="complete",next_steps=[],acceptance=[{"criterion":"fixture passes","status":"passed","evidence":"test"}])
        r=runtime.advance(self.root,self.store,"task",5,"BeforeCompletion",handoff=done,reviewed=True)
        self.assertEqual(r["state"],"closed")
        self.assertEqual(len(runtime.history(self.root,self.store,"task")["events"]),7)
        with self.assertRaises(cli.NaviError):runtime.advance(self.root,self.store,"task",6,"BeforeExecution")
    def test_scope_and_no_raw_prompt(self):
        runtime.start(self.root,self.store,"task","codex")
        runtime.advance(self.root,self.store,"task",0,"UserPrompt",brief=self.brief(deliverable="SENSITIVE-UNIQUE-TEXT"))
        self.assertNotIn(b"SENSITIVE-UNIQUE-TEXT",(self.store/"runtime.sqlite3").read_bytes())
        other=self.base/"other";other.mkdir()
        with self.assertRaises(cli.NaviError):runtime.status(other,self.store,"task")
        self.assertEqual(runtime.sessions(other,self.store)["sessions"],[])
        with self.assertRaises(cli.NaviError):runtime.start(self.root,self.root,"task","codex")
    def test_checkpoint_review_and_criteria(self):
        runtime.start(self.root,self.store,"task","none")
        runtime.advance(self.root,self.store,"task",0,"UserPrompt",brief=self.brief())
        runtime.advance(self.root,self.store,"task",1,"BeforeExecution")
        runtime.advance(self.root,self.store,"task",2,"AfterExecution")
        with self.assertRaises(cli.NaviError):runtime.advance(self.root,self.store,"task",3,"Checkpoint",handoff=self.handoff())
        wrong=self.handoff(state="complete",acceptance=[{"criterion":"wrong","status":"passed","evidence":"test"}])
        with self.assertRaises(cli.NaviError):runtime.advance(self.root,self.store,"task",3,"BeforeCompletion",handoff=wrong,reviewed=True)
        self.assertEqual(runtime.status(self.root,self.store,"task")["revision"],3)
        runtime.advance(self.root,self.store,"task",3,"SessionEnd",handoff=self.handoff(),reviewed=True)
        self.assertEqual(runtime.context(self.root,self.store,"task")["state"],"paused")
    def test_connect_and_disconnect_only_owned(self):
        rel,_=runtime_hooks.fragment("codex")
        self.assertEqual(runtime_hooks.connection(self.root,self.store,"codex")["state"],"missing")
        self.assertFalse((self.root/rel).exists())
        self.assertEqual(runtime_hooks.connection(self.root,self.store,"codex","apply")["status"],"connected")
        self.assertEqual(runtime_hooks.connection(self.root,self.store,"codex","check")["status"],"current")
        with self.assertRaises(cli.NaviError):runtime_hooks.connection(self.root,self.store,"gemini","apply")
        p=self.root/rel;raw=p.read_bytes();p.write_text("{}")
        self.assertEqual(runtime_hooks.connection(self.root,self.store,"codex","disconnect")["status"],"review-required")
        self.assertEqual(p.read_text(),"{}")
        p.write_bytes(raw)
        self.assertEqual(runtime_hooks.connection(self.root,self.store,"codex","disconnect")["status"],"disconnected")
        self.assertFalse(p.exists())
    def test_existing_config_never_overwritten(self):
        path=self.root/".gemini/settings.json";path.parent.mkdir();path.write_text("{}")
        self.assertEqual(runtime_hooks.connection(self.root,self.store,"gemini","apply")["status"],"review-required")
        self.assertEqual(path.read_text(),"{}")
    def test_hooks_are_fixed_context_not_prompt_echo(self):
        for host,(_,start,prompt) in runtime.HOOKS.items():
            for event in (start,prompt):
                result=runtime_hooks.hook(host,event,{"hook_event_name":event,"prompt":"private-secret"})
                self.assertNotIn("private-secret",json.dumps(result))
                self.assertIn("NAVI NEF",result["hookSpecificOutput"]["additionalContext"])
        self.assertFalse(runtime.capabilities("manus")["native_write_interception"])
        self.assertFalse(runtime.capabilities("copilot")["native_context_hooks"])
        with self.assertRaises(cli.NaviError):runtime_hooks.hook("codex","SessionStart",{"hook_event_name":"Stop"})
    def test_cli(self):
        from contextlib import redirect_stdout
        from io import StringIO
        with redirect_stdout(StringIO()):
            self.assertEqual(cli.main(["hosts"]),0)
            self.assertEqual(cli.main(["capabilities","--host","generic"]),0)
            self.assertEqual(cli.main(["session","start","--root",str(self.root),"--store",str(self.store),"--id","test","--host","generic"]),0)
