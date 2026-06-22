# Experiment Spec

- Topic: SQLite index tradeoffs on the UCI Bike Sharing hourly workload
- Metric: primary_metric
- Direction: minimize
- Time budget seconds: 30

## Trials
- `baseline-seed0`: No secondary indexes, seed 0.
- `baseline-seed1`: No secondary indexes, seed 1.
- `baseline-seed2`: No secondary indexes, seed 2.
- `baseline-seed3`: No secondary indexes, seed 3.
- `ablation-hour-index-seed1`: Add only an hour index.
- `ablation-weather-index-seed2`: Add only a weather and working-day index.
- `ablation-season-index-seed3`: Add only a season and year index.
- `ablation-composite-index-seed4`: Add all three workload-specific indexes.
