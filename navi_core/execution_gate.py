"""Local trusted-controller operation authorization and atomic budget reservation.

Not a sandbox, remote identity system, or provider billing cap. Only a trusted
controller may hold the signing key and access the SQLite ledger. Workers must
not receive either. No high-risk or production operation is enabled here.
"""
import contextlib
import hashlib
import hmac
import json
from pathlib import Path
import re
import sqlite3
import time
import uuid

class GateError(ValueError):
    pass

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False,ensure_ascii=False).encode("utf-8")

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

ID=re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}$")
HEX=re.compile(r"^[a-f0-9]{64}$")
ACTIONS={"synthetic-inference","deterministic-fixture"}
FIELDS={"version","authority","ledger_id","operation_id","action","risk","input_sha256","provider","max_tokens","issued_at","expires_at"}

def validate(op):
    if type(op) is not dict or set(op)!=FIELDS or type(op["version"]) is not int or op["version"]!=1:
        raise GateError("Invalid operation contract")
    for key in ("authority","ledger_id","operation_id","provider"):
        if not isinstance(op[key],str) or not ID.fullmatch(op[key]):
            raise GateError("Invalid operation identifier")
    if op["action"] not in ACTIONS or op["risk"]!="low":
        raise GateError("Only low-risk fixture operations allowed")
    if not isinstance(op["input_sha256"],str) or not HEX.fullmatch(op["input_sha256"]):
        raise GateError("Invalid input hash")
    for key in ("issued_at","expires_at","max_tokens"):
        if type(op[key]) is not int:raise GateError("Expected integer")
    if not 1<=op["max_tokens"]<=100000 or not 0<op["expires_at"]-op["issued_at"]<=300:
        raise GateError("Invalid token or expiry allowance")
    return op

def sign(operation,key):
    validate(operation)
    if type(key) is not bytes or len(key)<32:raise GateError("Expected separate 256-bit authority key")
    return hmac.new(key,canonical(operation),hashlib.sha256).hexdigest()

class Ledger:
    """One budget per private ledger. No refunds when usage is unknown."""
    def __init__(self,path,ledger_id,authority,key,total):
        if not isinstance(ledger_id,str) or not ID.fullmatch(ledger_id) or not isinstance(authority,str) or not ID.fullmatch(authority):
            raise GateError("Invalid ledger or authority ID")
        if type(total) is not int or not 1<=total<=10000000 or type(key) is not bytes or len(key)<32:
            raise GateError("Invalid budget or key")
        self.path=Path(path).absolute()
        if self.path.is_symlink() or not self.path.parent.is_dir() or self.path.parent.is_symlink():
            raise GateError("Ledger must be in a trusted private directory")
        self.ledger_id,self.authority,self.key,self.total=ledger_id,authority,key,total
        with self.transaction() as c:
            c.execute("CREATE TABLE IF NOT EXISTS settings (singleton INTEGER PRIMARY KEY CHECK(singleton=1), ledger_id TEXT NOT NULL, authority TEXT NOT NULL, key_check TEXT NOT NULL, total INTEGER NOT NULL, frozen INTEGER NOT NULL DEFAULT 0)")
            c.execute("CREATE TABLE IF NOT EXISTS operations (id TEXT PRIMARY KEY, operation_hash TEXT NOT NULL, cap INTEGER NOT NULL, state TEXT NOT NULL CHECK(state IN ('reserved','settled','unknown','overrun')), charged INTEGER NOT NULL)")
            key_check=hmac.new(key,b"NAVI fixture ledger identity v1",hashlib.sha256).hexdigest()
            c.execute("INSERT OR IGNORE INTO settings(singleton,ledger_id,authority,key_check,total) VALUES(1,?,?,?,?)",(ledger_id,authority,key_check,total))
            row=c.execute("SELECT ledger_id,authority,key_check,total FROM settings WHERE singleton=1").fetchone()
            if row!=(ledger_id,authority,key_check,total):raise GateError("Ledger identity or budget mismatch")

    @contextlib.contextmanager
    def transaction(self):
        c=sqlite3.connect(self.path,timeout=10,isolation_level=None)
        try:
            c.execute("PRAGMA busy_timeout=10000")
            c.execute("BEGIN IMMEDIATE")
            yield c
            c.execute("COMMIT")
        except BaseException:
            if c.in_transaction:c.execute("ROLLBACK")
            raise
        finally:c.close()

    def reserve(self,operation,signature,*,actual_input,now=None):
        validate(operation)
        now=int(time.time()) if now is None else now
        if type(now) is not int or not operation["issued_at"]<=now<operation["expires_at"]:
            raise GateError("Approval expired or not yet valid")
        if operation["ledger_id"]!=self.ledger_id or operation["authority"]!=self.authority:
            raise GateError("Wrong authority or ledger")
        if digest(actual_input)!=operation["input_sha256"]:
            raise GateError("Operation input does not match approval")
        if not isinstance(signature,str) or not hmac.compare_digest(sign(operation,self.key),signature):
            raise GateError("Invalid operation approval")
        with self.transaction() as c:
            if c.execute("SELECT frozen FROM settings WHERE singleton=1").fetchone()[0]:
                raise GateError("Ledger frozen after reported overrun")
            if c.execute("SELECT 1 FROM operations WHERE id=?",(operation["operation_id"],)).fetchone():
                raise GateError("Approval already consumed")
            used=c.execute("SELECT COALESCE(SUM(charged),0) FROM operations").fetchone()[0]
            cap=operation["max_tokens"]
            if used+cap>self.total:raise GateError("Insufficient unreserved budget")
            c.execute("INSERT INTO operations VALUES(?,?,?,?,?)",(operation["operation_id"],digest(operation),cap,"reserved",cap))
        return {"id":operation["operation_id"],"operation_sha256":digest(operation),"reserved_tokens":cap}

    def settle(self,receipt,reported_tokens=None):
        if type(receipt) is not dict or set(receipt)!={"id","operation_sha256","reserved_tokens"}:
            raise GateError("Invalid receipt")
        if reported_tokens is not None and (type(reported_tokens) is not int or not 0<=reported_tokens<=1000000000):
            raise GateError("Invalid reported usage")
        with self.transaction() as c:
            row=c.execute("SELECT operation_hash,cap,state FROM operations WHERE id=?",(receipt["id"],)).fetchone()
            if not row or row!=(receipt["operation_sha256"],receipt["reserved_tokens"],"reserved"):
                raise GateError("Unknown, altered or already settled reservation")
            cap=row[1]
            state="unknown" if reported_tokens is None else "overrun" if reported_tokens>cap else "settled"
            charged=cap if reported_tokens is None else reported_tokens
            c.execute("UPDATE operations SET state=?,charged=? WHERE id=?",(state,charged,receipt["id"]))
            if state=="overrun":c.execute("UPDATE settings SET frozen=1 WHERE singleton=1")
        return {"status":state,"charged_tokens":charged,"usage_source":"unknown-conservative" if reported_tokens is None else "controller-reported"}

    def status(self):
        with self.transaction() as c:
            used=c.execute("SELECT COALESCE(SUM(charged),0) FROM operations").fetchone()[0]
            frozen=bool(c.execute("SELECT frozen FROM settings WHERE singleton=1").fetchone()[0])
            counts=dict(c.execute("SELECT state,COUNT(*) FROM operations GROUP BY state").fetchall())
        return {"total_tokens":self.total,"charged_or_reserved_tokens":used,"remaining_tokens":max(0,self.total-used),"frozen":frozen,"counts":counts,
                "scope":"Local controller accounting; not actual provider billing or worker sandbox"}

def operation(ledger_id,authority,provider,action,actual_input,max_tokens,*,now=None):
    now=int(time.time()) if now is None else now
    return validate({"version":1,"ledger_id":ledger_id,"authority":authority,"provider":provider,
                     "action":action,"risk":"low","input_sha256":digest(actual_input),"max_tokens":max_tokens,
                     "operation_id":uuid.uuid4().hex,"issued_at":now,"expires_at":now+120})
