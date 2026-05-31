# River KSN — River Steepness Index Calculator

Calculate the river normalized steepness index (ksn) from a DEM (Digital Elevation Model).

## Installation

```bash
uv sync
```

## Usage

```bash
# Auto-determine theta and channel threshold
python -m river_ksn path/to/dem.tif -o results/

# Specify parameters
python -m river_ksn dem.tif -o results/ --theta 0.45 --threshold 500

# Export intermediate rasters
python -m river_ksn dem.tif --intermediate
```

## Output

- `<stem>_ksn.tif` — ksn raster (GeoTIFF)
- `<stem>_ksn.csv` — Channel cell table (row, col, drainage_area, slope, ksn)
- With `--intermediate`: filled DEM, flow accumulation, slope

## Method

Based on the channel steepness-area power-law relationship: `S = ks * A^(-θ)`

- Flow direction algorithm: D-infinity (Tarboton, 1997)
- Sink filling algorithm: Wang & Liu (2006)
- Auto theta calibration: log-log slope-area least squares regression
- Channel threshold: 95th percentile of flow accumulation

## Dependencies

- richdem — hydrological analysis
- rasterio — GeoTIFF I/O
- numpy, scipy — numerical computing and regression
