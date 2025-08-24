# day02/sensim/tests/test_core.py
import sys
from pathlib import Path
# 获取项目根目录路径
project_root = str(Path(__file__).resolve().parent.parent)
sys.path.append(project_root)
from sensim.core import generate_dataframe, stream_to_csv, SimConfig
import pandas as pd

def test_generate_dataframe_shape_and_cols():
    df = generate_dataframe(rate=5, duration=10, seed=42)
    assert len(df) == 50
    assert set(["timestamp", "temperature_C", "humidity_pct"]).issubset(df.columns)

def test_stream_to_csv(tmp_path: Path):
    out = tmp_path / "s.csv"
    cfg = SimConfig(rate=10, duration=2, seed=1, out=out)
    # 禁用实时睡眠，加速测试
    stream_to_csv(cfg, print_stdout=False, realtime=False)
    df = pd.read_csv(out)
    assert len(df) == 20
    assert df["humidity_pct"].between(0, 100).all()