import json
from pathlib import Path
import tempfile
import unittest
from navi_core import cli,knowledge,nef,runtime

class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.base=Path(t.name).resolve()
        self.root=self.base/"project";self.root.mkdir()
        self.store=self.base/"private";self.store.mkdir()
        self.query=self.base/"query.txt";self.query.write_text("CSV export client")
    def doc(self,ident="csv",text="CSV export uses a UTF-8 header"):
        return {"schema_version":1,"id":ident,"title":"CSV export","text":text,"source":"docs/export.md","revision":"a"*40}
    def graph(self):
        return {"directed":False,"multigraph":False,"graph":{},"nodes":[
            {"id":"client","label":"CSV client","source_file":"src/client.py","source_location":"L1","private_extra":"not copied"},
            {"id":"writer","label":"Writer","source_file":"src/writer.py","source_location":"L3"}],
            "links":[{"source":"client","target":"writer","relation":"calls","confidence":"EXTRACTED"}]}
    def save(self,ident,data,kind):
        plan=knowledge.ingest(self.root,self.store,ident,data,kind)
        self.assertEqual(plan["status"],"review-required")
        return knowledge.ingest(self.root,self.store,ident,data,kind,plan["sha256"])
    def test_exact_review_and_dedup(self):
        p=knowledge.ingest(self.root,self.store,"csv",self.doc(),"document")
        self.assertEqual(list(self.store.iterdir()),[])
        with self.assertRaises(cli.NaviError):knowledge.ingest(self.root,self.store,"csv",self.doc(text="changed"),"document",p["sha256"])
        self.save("csv",self.doc(),"document")
        self.save("copy",self.doc("copy"),"document")
        r=knowledge.retrieve(self.root,self.store,self.query)
        self.assertEqual(len(r["evidence"]),1)
        self.assertEqual(r["evidence"][0]["source"],"docs/export.md")
        self.assertIn(r["retrieval"]["text"],("fts5-bm25","lexical-fallback"))
    def test_graph_neighbors_and_revocation(self):
        self.save("graph",self.graph(),"graph")
        r=knowledge.retrieve(self.root,self.store,self.query)
        self.assertEqual(len(r["graph"]["nodes"]),2)
        self.assertEqual(r["graph"]["links"][0]["confidence"],"EXTRACTED")
        self.assertNotIn("not copied",json.dumps(r))
        self.assertEqual(knowledge.revoke(self.root,self.store,"graph","graph",True)["status"],"revoked")
        self.assertEqual(knowledge.retrieve(self.root,self.store,self.query)["graph"]["nodes"],[])
    def test_lessons_revoked_and_scope(self):
        lesson={"schema_version":1,"id":"csv","kind":"preference","summary":"CSV header required",
                "source_reference":"user approved","validation":"fixture passed"}
        nef.learn(self.root,self.store,lesson,True)
        self.assertEqual(knowledge.retrieve(self.root,self.store,self.query)["evidence"][0]["kind"],"lesson")
        nef.revoke(self.root,self.store,"csv",True)
        self.assertEqual(knowledge.retrieve(self.root,self.store,self.query)["evidence"],[])
        self.save("csv",self.doc(),"document")
        other=self.base/"other";other.mkdir()
        self.assertEqual(knowledge.retrieve(other,self.store,self.query)["evidence"],[])
    def test_budget_and_no_query_storage(self):
        self.save("csv",self.doc(text="CSV export "+("x"*3000)),"document")
        r=knowledge.retrieve(self.root,self.store,self.query,1024)
        self.assertLessEqual(knowledge._size(r),1024)
        self.assertEqual(r["evidence"],[])
        self.assertNotIn("CSV export client",json.dumps(r))
        self.assertEqual(len(list(self.store.iterdir())),1)
    def test_bad_graph_and_paths(self):
        g=self.graph();g["nodes"][0]["source_file"]="../private"
        with self.assertRaises(cli.NaviError):knowledge.graphify(g)
        g=self.graph();g["links"][0]["target"]="missing"
        with self.assertRaises(cli.NaviError):knowledge.graphify(g)
        d=self.doc();d["raw_prompt"]="no"
        with self.assertRaises(cli.NaviError):knowledge.ingest(self.root,self.store,"csv",d,"document")
    def test_checkpoint_preserved(self):
        runtime.start(self.root,self.store,"task","generic")
        h={"schema_version":1,"objective":"CSV","revision":None,"state":"blocked","completed":[],"blockers":["Need source"],
           "decisions":["Preserve header"],"next_steps":["Ask user"],"rollback":"","acceptance":[],"verification":[]}
        runtime.advance(self.root,self.store,"task",0,"Checkpoint",handoff=h,reviewed=True)
        r=knowledge.retrieve(self.root,self.store,self.query,8192,"task")
        self.assertEqual(r["checkpoint"]["handoff"]["blockers"],["Need source"])
        self.assertEqual(r["checkpoint"]["handoff"]["decisions"],["Preserve header"])
    def test_cli(self):
        from contextlib import redirect_stdout
        from io import StringIO
        with redirect_stdout(StringIO()) as out:
            self.assertEqual(cli.main(["knowledge","retrieve","--root",str(self.root),"--store",str(self.store),"--query-file",str(self.query)]),0)
        self.assertEqual(json.loads(out.getvalue())["status"],"selected")
