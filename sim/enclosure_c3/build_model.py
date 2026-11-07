"""Build confirmed installed C3 geometry, leaving historical C2 artifacts intact."""
from pathlib import Path
import importlib.util
import sys

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'enclosure'
sys.path.insert(0,str(SOURCE))
spec=importlib.util.spec_from_file_location('enclosure_builder',SOURCE/'build_model.py')
builder=importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
builder.HERE=HERE
builder.POD_CAD=HERE/'source/installed_c3'

if __name__=='__main__':builder.main()
