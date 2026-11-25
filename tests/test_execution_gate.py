import concurrent.futures
import pathlib
import tempfile
import unittest
from navi_core import execution_gate as g

class GateTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.path=pathlib.Path(tmp.name)/"ledger.sqlite"
        self.key=b"x"*32
        self.ledger=g.Ledger(self.path,"lab","owner",self.key,100)
    def op(self,cap=60):
        return g.operation("lab","owner","fixture","synthetic-inference",{"a":1},cap,now=100)
    def reserve(self,op,**kw):
        return self.ledger.reserve(op,g.sign(op,self.key),actual_input={"a":1},now=100,**kw)
    def test_reservation_and_settlement(self):
        r=self.reserve(self.op())
        self.assertEqual(self.ledger.status()["remaining_tokens"],40)
        self.ledger.settle(r,20)
        self.assertEqual(self.ledger.status()["remaining_tokens"],80)
        with self.assertRaises(g.GateError):self.ledger.settle(r,20)
    def test_replay(self):
        o=self.op();self.reserve(o)
        with self.assertRaises(g.GateError):self.reserve(o)
    def test_binding(self):
        o=self.op()
        with self.assertRaises(g.GateError):self.ledger.reserve(o,g.sign(o,self.key),actual_input={"a":2},now=100)
        signature=g.sign(o,self.key);o["provider"]="other"
        with self.assertRaises(g.GateError):self.ledger.reserve(o,signature,actual_input={"a":1},now=100)
    def test_expiry_and_risk(self):
        o=self.op()
        with self.assertRaises(g.GateError):self.ledger.reserve(o,g.sign(o,self.key),actual_input={"a":1},now=220)
        o["risk"]="high"
        with self.assertRaises(g.GateError):g.sign(o,self.key)
    def test_unknown_charged_full(self):
        r=self.reserve(self.op());self.ledger.settle(r)
        self.assertEqual(self.ledger.status()["remaining_tokens"],40)
    def test_overrun_freezes(self):
        r=self.reserve(self.op());self.ledger.settle(r,61)
        self.assertTrue(self.ledger.status()["frozen"])
        with self.assertRaises(g.GateError):self.reserve(self.op(1))
    def test_concurrent_reservation(self):
        def attempt(_):
            try:self.reserve(self.op(30));return True
            except g.GateError:return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            outcomes=list(pool.map(attempt,range(8)))
        self.assertEqual(sum(outcomes),3)
        self.assertEqual(self.ledger.status()["remaining_tokens"],10)
    def test_reopen_does_not_refund(self):
        self.reserve(self.op())
        another=g.Ledger(self.path,"lab","owner",self.key,100)
        self.assertEqual(another.status()["remaining_tokens"],40)
        with self.assertRaises(g.GateError):g.Ledger(self.path,"lab","owner",b"z"*32,100)
        with self.assertRaises(g.GateError):g.Ledger(self.path,"lab","owner",self.key,200)
