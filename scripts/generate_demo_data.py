from pathlib import Path
import json, sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.retail import run_demo_session
p = Path(__file__).resolve().parents[1] / "data" / "sample" / "session.json"
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(run_demo_session(30), indent=2))
print("Wrote", p)
