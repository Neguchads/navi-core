import unittest
from unittest.mock import Mock,patch
from navi_core import governed_provider as p, execution_gate as g, cli

def body():
    return {"model":"local:9b","prompt":"synthetic public fixture","stream":False,"format":"json","options":{"num_ctx":4096,"num_predict":256}}

def result(**kw):
    x={"done":True,"model":"local:9b","prompt_eval_count":50,"eval_count":10,"response":"{}"}
    x.update(kw);return x

class GovernedTests(unittest.TestCase):
    def test_reserve_before_transport_and_settle(self):
        orig=g.Ledger.reserve;events=[]
        def reserve(self,*a,**k):
            x=orig(self,*a,**k);events.append("reserved");return x
        def transport(*args):
            self.assertEqual(events,["reserved"])
            events.append("called");return result()
        with patch.object(g.Ledger,"reserve",reserve):
            data,proof=p.guarded_request(body(),60,transport)
        self.assertEqual(events,["reserved","called"])
        self.assertEqual(proof["reservation"]["reserved_tokens"],4352)
        self.assertEqual(proof["settlement"]["charged_tokens"],60)
        self.assertEqual(proof["ledger"]["remaining_tokens"],4292)
    def test_invalid_no_call(self):
        x=body();x["options"]["num_predict"]=0;transport=Mock()
        with self.assertRaises(cli.NaviError):p.guarded_request(x,60,transport)
        transport.assert_not_called()
    def test_failed_call_charged_full(self):
        original=g.Ledger.settle;settlements=[]
        def settle(self,*args,**kwargs):
            x=original(self,*args,**kwargs);settlements.append(x);return x
        with patch.object(g.Ledger,"settle",settle):
            with self.assertRaises(OSError):p.guarded_request(body(),60,Mock(side_effect=OSError()))
        self.assertEqual(settlements,[{"status":"unknown","charged_tokens":4352,"usage_source":"unknown-conservative"}])
    def test_missing_usage_and_model_mismatch(self):
        for response in (result(eval_count=None),result(model="other:9b"),result(done=False),result(eval_count=257)):
            with self.assertRaises(cli.NaviError):p.guarded_request(body(),60,Mock(return_value=response))
