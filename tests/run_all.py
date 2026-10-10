"""Run every test:  python3 tests/run_all.py        (QUICK=1 python3 tests/run_all.py skips the slow ones)"""
import os, sys, unittest
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
suite = unittest.defaultTestLoader.discover(here, pattern="test_*.py")
res = unittest.TextTestRunner(verbosity=2, warnings="ignore").run(suite)
sys.exit(0 if res.wasSuccessful() else 1)
