"""Fixed test gates; project code must be trusted, never a sandbox."""
import pathlib
import re
import subprocess
import sys
import unittest

def unittest_gate(directory):
    suite=unittest.defaultTestLoader.discover(directory)
    count=suite.countTestCases()
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    print("Discovered tests:",count,"Executed non-skipped tests:",result.testsRun-len(result.skipped))
    return 0 if count>0 and result.testsRun>len(result.skipped) and result.wasSuccessful() else 1

def node_gate(paths):
    # Explicit arguments, no shell or project-configured flags.
    result=subprocess.run(["node","--test","--test-reporter=tap",*paths],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False)
    sys.stdout.buffer.write(result.stdout)
    sys.stdout.buffer.flush()
    counts=re.findall(rb"(?m)^# pass ([0-9]+)\r?$",result.stdout)
    return 0 if result.returncode==0 and counts and int(counts[-1])>0 else 1

def main():
    if len(sys.argv)<3:return 2
    if sys.argv[1]=="python" and len(sys.argv)==3:return unittest_gate(sys.argv[2])
    if sys.argv[1]=="node":return node_gate(sys.argv[2:])
    return 2

if __name__=="__main__":
    raise SystemExit(main())
