# day01/sensor_sim/tests/test_simulate.py
from pathlib import Path
from sensor_sim.simulate import generate_sensor_data, save_csv
import pandas as pd

def test_row_count_and_columns(tmp_path: Path):
    df = generate_sensor_data(rate=5, duration=10, seed=42)
    assert len(df) == 50
    assert set(["timestamp", "temperature_C", "humidity_pct"]).issubset(df.columns)

    out = tmp_path / "out.csv"
    save_csv(df, out)
    df2 = pd.read_csv(out)
    assert len(df2) == 50

def test_value_ranges():
    df = generate_sensor_data(rate=10, duration=5, seed=1)
    assert df["temperature_C"].between(10, 45).all()
    assert df["humidity_pct"].between(0, 100).all()