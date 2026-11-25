"""Reserve before one explicitly requested public-fixture Ollama call.

This uses an ephemeral local controller ledger, not a human approval service.
No user credentials or provider keys are passed to model inference.
"""
import pathlib
import secrets
import tempfile
from . import execution_gate as gate
from .cli import NaviError

def guarded_request(body,timeout,transport):
    if type(body) is not dict or type(body.get("options")) is not dict or not isinstance(body.get("model"),str) or body.get("stream") is not False:
        raise NaviError("Invalid governed request")
    options=body["options"]
    ctx=options.get("num_ctx");cap=options.get("num_predict")
    if type(ctx) is not int or ctx!=4096 or type(cap) is not int or not 1<=cap<=4096:
        raise NaviError("Invalid governed context/output limit")
    with tempfile.TemporaryDirectory(prefix="navi-governed-") as temp:
        key=secrets.token_bytes(32)
        ledger=gate.Ledger(pathlib.Path(temp)/"reservation.sqlite","ollama-fixture","local-controller",key,ctx+cap)
        op=gate.operation("ollama-fixture","local-controller","ollama-loopback","synthetic-inference",body,ctx+cap)
        receipt=ledger.reserve(op,gate.sign(op,key),actual_input=body)
        try:
            result=transport(body,timeout)
        except BaseException:
            ledger.settle(receipt,None)
            raise
        if type(result) is not dict or result.get("done") is not True or result.get("model")!=body["model"]:
            ledger.settle(receipt,None)
            raise NaviError("Provider identity or completion not confirmed")
        inp=result.get("prompt_eval_count");out=result.get("eval_count")
        if type(inp) is not int or type(out) is not int or not 0<=inp<=100000000 or not 0<=out<=100000000:
            ledger.settle(receipt,None)
            raise NaviError("Provider usage unavailable")
        settlement=ledger.settle(receipt,inp+out)
        if inp>ctx or out>cap or settlement["status"]!="settled":
            raise NaviError("Provider-reported usage exceeds requested allowance")
        return result,{"reservation":receipt,"settlement":settlement,"ledger":ledger.status(),
                       "requested_input_context":ctx,"requested_output_cap":cap,
                       "scope":"Ephemeral controller reservation; usage server-reported; no hard provider billing limit or persistent session ledger"}
