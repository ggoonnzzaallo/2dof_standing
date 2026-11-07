"""Run the existing physical-model checks against C3, not the saved C2 model."""
from pathlib import Path
import importlib.util
import sys

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'enclosure'
sys.path.insert(0,str(SOURCE))
spec=importlib.util.spec_from_file_location('enclosure_checks',SOURCE/'check_model.py')
checks=importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
checks.HERE=HERE

if __name__=='__main__':checks.main()
