# River KSN — River Steepness Index Calculator

Calculate the river normalized steepness index (ksn) from a DEM (Digital Elevation Model).

## Installation

```bash
# Install as a global CLI tool (requires Python 3.10+)
uv tool install . --python 3.10

# Or run directly from the project directory
uv run river-ksn --help
```

## Usage

```bash
# Auto-determine theta and channel threshold
river-ksn path/to/dem.tif -o results/

# Specify parameters
river-ksn dem.tif -o results/ --theta 0.45 --threshold 500

# Export intermediate rasters
river-ksn dem.tif --intermediate

# Or if running from project source:
uv run river-ksn dem.tif -o results/
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
