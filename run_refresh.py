"""Convenient local entry point without requiring an editable installation."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from unanet_pipeline.refresh import main
if __name__=='__main__':
    raise SystemExit(main())
