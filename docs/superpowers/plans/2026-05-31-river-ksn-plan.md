# 河流陡峭指数计算脚本 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现一个 CLI 工具，从 DEM GeoTIFF 计算河流归一化陡峭指数（ksn），输出 GeoTIFF 栅格和 CSV 表格。

**Architecture:** 线性处理管道：加载 DEM → 填洼 → D-infinity 流向 → 流量累积 → 河道提取 → 坡度 → θ 拟合 → ksn 计算 → 导出。通过 argparse 提供 CLI，模块按职责拆分为 6 个文件，每个对外暴露 1-3 个纯函数。

**Tech Stack:** Python 3.10+, richdem（水文分析）, rasterio（GeoTIFF 读写）, numpy, scipy（线性回归）, pytest, uv（包管理）

---

### Task 1: 项目初始化

**Files:**
- Create: `pyproject.toml`
- Create: `src/river_ksn/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[project]
name = "river-ksn"
version = "0.1.0"
description = "Calculate river normalized steepness index (ksn) from DEM"
requires-python = ">=3.10"
dependencies = [
    "rasterio>=1.3",
    "richdem>=0.3",
    "numpy>=1.24",
    "scipy>=1.10",
]

[project.scripts]
river-ksn = "river_ksn.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: 创建目录结构和空 `__init__.py`**

```bash
mkdir -p src/river_ksn
mkdir -p tests
```

创建空文件 `src/river_ksn/__init__.py` 和 `tests/__init__.py`。

- [ ] **Step 3: 用 uv 同步依赖并验证**

```bash
uv sync
```
Expected: 创建 `.venv`，安装 `rasterio`, `richdem`, `numpy`, `scipy`，无错误。

- [ ] **Step 4: 验证 Python 可导入基础库**

```bash
uv run python -c "import richdem as rd; import rasterio; import numpy; import scipy; print('OK')"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock src/ tests/ .python-version
git commit -m "feat: initialize project with uv and dependencies"
```

> **Note:** 如果 `uv.lock` 或 `.python-version` 未生成（uv 版本差异），跳过添加不存在的文件，只 commit 存在的。

---

### Task 2: DEM 加载与填洼模块

**Files:**
- Create: `src/river_ksn/dem.py`
- Test: `tests/test_dem.py`

- [ ] **Step 1: 写失败的测试**

`tests/test_dem.py`:

```python
import numpy as np
from river_ksn.dem import load_dem, fill_dem


def test_load_dem_returns_array(tmp_path):
    """load_dem 应该返回一个 richdem/numpy 数组"""
    import rasterio
    dem_path = tmp_path / "test.tif"
    data = np.array([
        [10.0, 11.0, 12.0],
        [9.0, 8.0, 13.0],
        [8.0, 7.0, 14.0],
    ], dtype=np.float32)
    with rasterio.open(
        str(dem_path), 'w',
        driver='GTiff',
        height=3, width=3,
        count=1, dtype='float32',
        crs='EPSG:4326',
        transform=rasterio.transform.from_origin(0, 0, 1, 1),
    ) as dst:
        dst.write(data, 1)

    dem = load_dem(str(dem_path))
    assert dem.shape == (3, 3)
    assert np.allclose(dem, data)


def test_fill_dem_preserves_shape():
    """填洼后形状应与输入一致"""
    import richdem as rd
    data = np.array([
        [5.0, 5.0, 5.0],
        [5.0, 1.0, 5.0],
        [5.0, 5.0, 5.0],
    ], dtype=np.float64)
    dem = rd.rdarray(data, no_data=-9999)
    filled = fill_dem(dem)
    assert filled.shape == (3, 3)
    assert np.all(filled >= data)  # 填洼不会降低高程
```

- [ ] **Step 2: 运行测试验证失败**

```bash
uv run pytest tests/test_dem.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'river_ksn.dem'`

- [ ] **Step 3: 实现最小 DEM 模块**

`src/river_ksn/dem.py`:

```python
"""DEM loading and depression filling."""

import richdem as rd


def load_dem(path: str) -> rd.rdarray:
    """Load a DEM from a GeoTIFF file.

    Args:
        path: Path to the GeoTIFF DEM file.

    Returns:
        RichDEM array with elevation data.

    Raises:
        FileNotFoundError: If the file does not exist.
        RuntimeError: If the file cannot be read as a DEM.
    """
    return rd.LoadGDAL(path)


def fill_dem(dem: rd.rdarray) -> rd.rdarray:
    """Fill sinks/depressions in a DEM.

    Uses Wang & Liu (2006) algorithm via richdem.

    Args:
        dem: RichDEM array of elevation values.

    Returns:
        Filled DEM with same shape as input.
    """
    return rd.FillDepressions(dem, epsilon=True, in_place=False)
```

- [ ] **Step 4: 运行测试验证通过**

```bash
uv run pytest tests/test_dem.py -v
```
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/river_ksn/dem.py tests/test_dem.py
git commit -m "feat: add DEM loading and sink filling"
```

---

### Task 3: 水文分析模块

**Files:**
- Create: `src/river_ksn/hydrology.py`

- [ ] **Step 1: 实现水文分析函数**（纯管道函数，集成测试在 Task 9 覆盖）

`src/river_ksn/hydrology.py`:

```python
"""Hydrological analysis: flow direction and accumulation."""

import richdem as rd


def compute_flow_accumulation(dem: rd.rdarray) -> rd.rdarray:
    """Compute D-infinity flow accumulation.

    Args:
        dem: Filled DEM (should already have depressions filled).

    Returns:
        Flow accumulation array (number of upstream cells).
    """
    return rd.FlowAccumulation(dem, method='Dinf')
```

- [ ] **Step 2: Commit**

```bash
git add src/river_ksn/hydrology.py
git commit -m "feat: add D-infinity flow accumulation"
```

---

### Task 4: 河道提取模块

**Files:**
- Create: `src/river_ksn/channel.py`
- Test: `tests/test_channel.py`

- [ ] **Step 1: 写失败的测试**

`tests/test_channel.py`:

```python
import numpy as np
from river_ksn.channel import auto_threshold, extract_channels


def test_auto_threshold_returns_reasonable_value():
    """自动阈值应在流量累积值范围内"""
    flow_accum = np.array([
        [0, 0, 1, 2, 5],
        [0, 0, 3, 8, 20],
        [0, 0, 2, 6, 100],
    ], dtype=np.float64)
    threshold = auto_threshold(flow_accum, percentile=80)
    expected = np.percentile(flow_accum[flow_accum > 0], 80)
    assert np.isclose(threshold, expected)
    assert threshold > 0


def test_extract_channels_returns_boolean_mask():
    """河道提取返回布尔掩膜"""
    flow_accum = np.array([
        [0, 0, 5, 10],
        [0, 3, 8, 15],
    ], dtype=np.float64)
    mask = extract_channels(flow_accum, threshold=5)
    assert mask.dtype == bool
    assert mask.shape == (2, 4)
    assert mask[0, 2]   # 5
    assert mask[0, 3]   # 10
    assert mask[1, 2]   # 8
    assert mask[1, 3]   # 15
    assert not mask[0, 0]  # 0
    assert not mask[0, 1]  # 0
    assert not mask[1, 0]  # 0
    assert not mask[1, 1]  # 3
```

- [ ] **Step 2: 运行测试验证失败**

```bash
uv run pytest tests/test_channel.py -v
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现河道提取模块**

`src/river_ksn/channel.py`:

```python
"""Channel network extraction from flow accumulation."""

import numpy as np


def auto_threshold(flow_accum: np.ndarray, percentile: float = 95.0) -> float:
    """Determine a flow accumulation threshold for channel initiation.

    Uses the specified percentile of non-zero flow accumulation values.

    Args:
        flow_accum: Flow accumulation array.
        percentile: Percentile to use (default 95).

    Returns:
        Threshold value in cell count units.
    """
    nonzero = flow_accum[flow_accum > 0]
    if len(nonzero) == 0:
        return 1.0
    return float(np.percentile(nonzero, percentile))


def extract_channels(
    flow_accum: np.ndarray, threshold: float
) -> np.ndarray:
    """Extract channel cells based on flow accumulation threshold.

    Args:
        flow_accum: Flow accumulation array.
        threshold: Minimum flow accumulation for a cell to be considered channel.

    Returns:
        Boolean mask where True indicates a channel cell.
    """
    return flow_accum >= threshold
```

- [ ] **Step 4: 运行测试验证通过**

```bash
uv run pytest tests/test_channel.py -v
```
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/river_ksn/channel.py tests/test_channel.py
git commit -m "feat: add channel extraction and auto threshold"
```

---

### Task 5: KSN 计算模块

**Files:**
- Create: `src/river_ksn/ksn.py`
- Test: `tests/test_ksn.py`

- [ ] **Step 1: 写失败的测试**

`tests/test_ksn.py`:

```python
import numpy as np
from river_ksn.ksn import calibrate_theta, compute_ksn


def test_calibrate_theta_perfect_power_law():
    """对完美幂律数据拟合应得到准确的 θ 和高 R²"""
    np.random.seed(42)
    area = np.logspace(1, 4, 100)  # 10 到 10000
    slope = 10.0 * (area ** (-0.5))
    mask = np.ones(len(area), dtype=bool)

    theta, r2 = calibrate_theta(area, slope, mask)
    assert np.isclose(theta, 0.5, atol=0.01), f"Got theta={theta}"
    assert r2 > 0.99, f"Got R²={r2}"


def test_calibrate_theta_ignores_invalid():
    """拟合时应忽略无效值（零或负面积/坡度）"""
    area = np.array([0, -1, 100, 1000, 10000], dtype=np.float64)
    slope = np.array([1, 1, 3.16, 1.0, 0.316], dtype=np.float64)
    mask = np.array([True, True, True, True, True])
    theta, r2 = calibrate_theta(area, slope, mask)
    assert np.isclose(theta, 0.5, atol=0.01)


def test_compute_ksn_correct_formula():
    """ksn = S / A^(-theta)"""
    area = np.array([100.0, 1000.0, 10000.0], dtype=np.float64)
    slope = np.array([1.0, 1.0, 1.0], dtype=np.float64)
    channel_mask = np.array([True, True, True])

    theta = 0.5
    ksn = compute_ksn(slope, area, theta, channel_mask)
    expected = slope / (area ** (-theta))
    assert np.allclose(ksn, expected)


def test_compute_ksn_nan_outside_channels():
    """非河道像元应为 NaN"""
    area = np.array([[10.0, 100.0], [1000.0, 10000.0]], dtype=np.float64)
    slope = np.array([[1.0, 1.0], [1.0, 1.0]], dtype=np.float64)
    channel_mask = np.array([[False, True], [True, False]])

    ksn = compute_ksn(slope, area, 0.45, channel_mask)
    assert np.isnan(ksn[0, 0])
    assert np.isnan(ksn[1, 1])
    assert not np.isnan(ksn[0, 1])
    assert not np.isnan(ksn[1, 0])
```

- [ ] **Step 2: 运行测试验证失败**

```bash
uv run pytest tests/test_ksn.py -v
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 KSN 模块**

`src/river_ksn/ksn.py`:

```python
"""KSN (normalized channel steepness index) computation."""

import numpy as np
from scipy import stats


def compute_slope(dem: "rd.rdarray") -> np.ndarray:
    """Compute slope from DEM using richdem.

    Uses the 'slope_riserun' method.

    Args:
        dem: Filled DEM array.

    Returns:
        Slope array (rise/run).
    """
    import richdem as rd
    return np.array(rd.TerrainAttribute(dem, 'slope_riserun'))


def calibrate_theta(
    area: np.ndarray,
    slope: np.ndarray,
    channel_mask: np.ndarray,
) -> tuple[float, float]:
    """Calibrate concavity index (theta) via log-log linear regression.

    Fits: log(S) = log(ks) - theta * log(A)

    Args:
        area: Drainage area (flow accumulation in cell units).
        slope: Channel slope.
        channel_mask: Boolean mask of channel cells.

    Returns:
        Tuple of (theta, r_squared).
    """
    a = area[channel_mask]
    s = slope[channel_mask]

    valid = (
        (a > 0)
        & (s > 0)
        & np.isfinite(np.log(a))
        & np.isfinite(np.log(s))
    )
    log_a = np.log(a[valid])
    log_s = np.log(s[valid])

    if len(log_a) < 3:
        return 0.45, 0.0

    result = stats.linregress(log_a, log_s)
    theta = float(abs(result.slope))
    r_squared = float(result.rvalue ** 2)
    return theta, r_squared


def compute_ksn(
    slope: np.ndarray,
    area: np.ndarray,
    theta_ref: float,
    channel_mask: np.ndarray,
) -> np.ndarray:
    """Compute normalized channel steepness index.

    ksn = S / A^(-theta_ref)

    Args:
        slope: Slope array.
        area: Drainage area (flow accumulation in cell units).
        theta_ref: Reference concavity index.
        channel_mask: Boolean mask of channel cells.

    Returns:
        ksn array, NaN for non-channel cells.
    """
    ksn = np.full_like(slope, np.nan, dtype=np.float64)
    valid = channel_mask & (area > 0) & (slope > 0)
    ksn[valid] = slope[valid] / (area[valid] ** (-theta_ref))
    return ksn
```

- [ ] **Step 4: 运行测试验证通过**

```bash
uv run pytest tests/test_ksn.py -v
```
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/river_ksn/ksn.py tests/test_ksn.py
git commit -m "feat: add ksn computation and theta calibration"
```

---

### Task 6: 导出模块

**Files:**
- Create: `src/river_ksn/export.py`
- Test: `tests/test_export.py`

- [ ] **Step 1: 写失败的测试**

`tests/test_export.py`:

```python
import numpy as np
import csv
from river_ksn.export import export_geotiff, export_csv


def test_export_geotiff_creates_file(tmp_path):
    """导出 GeoTIFF 应创建有效文件"""
    import rasterio
    dem_path = tmp_path / "dem.tif"
    data = np.array([
        [10, 20, 30],
        [15, 25, 35],
    ], dtype=np.float32)
    with rasterio.open(
        str(dem_path), 'w',
        driver='GTiff', height=2, width=3,
        count=1, dtype='float32',
        crs='EPSG:4326',
        transform=rasterio.transform.from_origin(0, 0, 30, 30),
    ) as dst:
        dst.write(data, 1)

    ksn = np.array([
        [np.nan, 50.0, np.nan],
        [60.0, np.nan, 70.0],
    ], dtype=np.float64)

    out_path = tmp_path / "ksn.tif"
    export_geotiff(ksn, str(dem_path), str(out_path))

    assert out_path.exists()
    with rasterio.open(str(out_path)) as src:
        out_data = src.read(1)
        assert src.crs == 'EPSG:4326'
        assert out_data[0, 0] == -9999.0
        assert out_data[0, 1] == 50.0


def test_export_csv_writes_correct_format(tmp_path):
    """CSV 应包含正确的列和行"""
    area = np.array([[100.0, 200.0], [300.0, 400.0]], dtype=np.float64)
    slope = np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float64)
    ksn = np.array([[10.0, np.nan], [30.0, 40.0]], dtype=np.float64)
    channel_mask = np.array([[True, False], [True, True]])

    out_path = tmp_path / "ksn.csv"
    export_csv(area, slope, ksn, channel_mask, str(out_path))

    assert out_path.exists()
    with open(out_path, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert reader.fieldnames == ['row', 'col', 'drainage_area', 'slope', 'ksn']
        assert len(rows) == 3

        assert float(rows[0]['row']) == 0
        assert float(rows[0]['col']) == 0
        assert float(rows[0]['ksn']) == 10.0
```

- [ ] **Step 2: 运行测试验证失败**

```bash
uv run pytest tests/test_export.py -v
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现导出模块**

`src/river_ksn/export.py`:

```python
"""Export results to GeoTIFF and CSV."""

import csv
import numpy as np
import rasterio


def export_geotiff(
    array: np.ndarray,
    input_path: str,
    output_path: str,
    nodata: float = -9999.0,
) -> None:
    """Export a 2D array as a GeoTIFF.

    Inherits CRS, transform, and dimensions from the input DEM.

    Args:
        array: 2D array of values (NaN will be replaced with nodata).
        input_path: Path to the reference DEM for geospatial metadata.
        output_path: Path where the GeoTIFF will be written.
        nodata: Value to use for NaN/no-data cells.
    """
    with rasterio.open(input_path) as src:
        profile = src.profile.copy()

    profile.update(dtype='float32', nodata=nodata)
    out = np.where(np.isnan(array), nodata, array).astype('float32')

    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(out, 1)


def export_csv(
    area: np.ndarray,
    slope: np.ndarray,
    ksn: np.ndarray,
    channel_mask: np.ndarray,
    output_path: str,
) -> None:
    """Export channel cell data as CSV.

    Args:
        area: Drainage area array.
        slope: Slope array.
        ksn: KSN array.
        channel_mask: Boolean mask of channel cells.
        output_path: Path where the CSV will be written.
    """
    rows, cols = np.where(channel_mask)
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['row', 'col', 'drainage_area', 'slope', 'ksn'])
        for r, c in zip(rows, cols):
            writer.writerow([r, c, area[r, c], slope[r, c], ksn[r, c]])
```

- [ ] **Step 4: 运行测试验证通过**

```bash
uv run pytest tests/test_export.py -v
```
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/river_ksn/export.py tests/test_export.py
git commit -m "feat: add GeoTIFF and CSV export"
```

---

### Task 7: 管道编排模块

**Files:**
- Create: `src/river_ksn/pipeline.py`

- [ ] **Step 1: 实现管道编排**

`src/river_ksn/pipeline.py`:

```python
"""End-to-end pipeline orchestration for ksn calculation."""

import os
import sys
import logging
import numpy as np
import richdem as rd

from river_ksn.dem import load_dem, fill_dem
from river_ksn.hydrology import compute_flow_accumulation
from river_ksn.channel import auto_threshold, extract_channels
from river_ksn.ksn import compute_slope, calibrate_theta, compute_ksn
from river_ksn.export import export_geotiff, export_csv

logger = logging.getLogger(__name__)

DEFAULT_THETA = 0.45


def _to_array(arr):
    """Convert rdarray or ndarray to plain numpy array."""
    if isinstance(arr, np.ndarray):
        return arr
    if isinstance(arr, rd.rdarray):
        return np.asarray(arr, dtype=np.float64)
    return np.asarray(arr, dtype=np.float64)


def run_pipeline(
    input_path: str,
    output_dir: str = "./output",
    theta: float | None = None,
    threshold: float | None = None,
    intermediate: bool = False,
) -> None:
    """Run the full ksn calculation pipeline."""
    if not os.path.isfile(input_path):
        logger.error("DEM file not found: %s", input_path)
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(input_path))[0]

    # 1. Load
    logger.info("Loading DEM: %s", input_path)
    dem = load_dem(input_path)

    # 2. Fill
    logger.info("Filling depressions...")
    dem_filled = fill_dem(dem)
    if intermediate:
        fp = os.path.join(output_dir, f"{stem}_filled.tif")
        export_geotiff(_to_array(dem_filled), input_path, fp)

    # 3. Flow accumulation
    logger.info("Computing D-infinity flow accumulation...")
    flow_accum = compute_flow_accumulation(dem_filled)
    fa = _to_array(flow_accum)
    logger.info("Flow accum range: %.0f - %.0f", fa.min(), fa.max())
    if intermediate:
        export_geotiff(fa, input_path, os.path.join(output_dir, f"{stem}_accum.tif"))

    # 4. Channel extraction
    if threshold is None:
        threshold = auto_threshold(fa)
        logger.info("Auto threshold: %.1f cells", threshold)
    else:
        logger.info("User threshold: %.1f cells", threshold)

    channel_mask = extract_channels(fa, threshold)
    n_channels = int(np.sum(channel_mask))
    logger.info("Channel cells: %d", n_channels)
    if n_channels == 0:
        logger.error(
            "No channel cells found with threshold %.0f. "
            "Try a lower --threshold value.", threshold
        )
        sys.exit(1)

    # 5. Slope
    logger.info("Computing slope...")
    slope = compute_slope(dem_filled)
    sl = _to_array(slope)
    if intermediate:
        export_geotiff(sl, input_path, os.path.join(output_dir, f"{stem}_slope.tif"))

    # 6. Calibrate theta
    if theta is None:
        theta_fit, r2 = calibrate_theta(fa, sl, channel_mask)
        logger.info("Calibrated theta: %.4f (R²=%.4f)", theta_fit, r2)
        if r2 < 0.3:
            logger.warning(
                "R²=%.4f is low (< 0.3). Falling back to default theta=%.2f",
                r2, DEFAULT_THETA,
            )
            theta_ref = DEFAULT_THETA
        else:
            theta_ref = theta_fit
    else:
        theta_ref = theta
        logger.info("Using user-specified theta: %.4f", theta_ref)

    # 7. Compute ksn
    logger.info("Computing ksn (theta_ref=%.4f)...", theta_ref)
    ksn = compute_ksn(sl, fa, theta_ref, channel_mask)

    # 8. Export
    tif_path = os.path.join(output_dir, f"{stem}_ksn.tif")
    csv_path = os.path.join(output_dir, f"{stem}_ksn.csv")
    logger.info("Exporting ksn GeoTIFF: %s", tif_path)
    export_geotiff(ksn, input_path, tif_path)
    logger.info("Exporting ksn CSV: %s", csv_path)
    export_csv(fa, sl, ksn, channel_mask, csv_path)
    logger.info("Done.")
```

- [ ] **Step 2: 验证模块无导入错误**

```bash
uv run python -c "from river_ksn.pipeline import run_pipeline; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/river_ksn/pipeline.py
git commit -m "feat: add pipeline orchestration"
```

---

### Task 8: CLI 入口

**Files:**
- Create: `src/river_ksn/__main__.py`

- [ ] **Step 1: 实现 CLI**

`src/river_ksn/__main__.py`:

```python
"""CLI entry point for river ksn calculation."""

import argparse
import logging
import sys

from river_ksn.pipeline import run_pipeline


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Calculate river normalized steepness index (ksn) from DEM",
    )
    parser.add_argument(
        "input",
        help="Path to input DEM GeoTIFF file",
    )
    parser.add_argument(
        "-o", "--output",
        default="./output",
        help="Output directory (default: ./output)",
    )
    parser.add_argument(
        "--theta",
        type=float,
        default=None,
        help="Reference concavity index (auto-calibrated if omitted)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Flow accumulation threshold for channel definition (auto if omitted)",
    )
    parser.add_argument(
        "--intermediate",
        action="store_true",
        help="Export intermediate rasters (filled DEM, flow accumulation, slope)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress messages",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    run_pipeline(
        input_path=args.input,
        output_dir=args.output,
        theta=args.theta,
        threshold=args.threshold,
        intermediate=args.intermediate,
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证 CLI 帮助输出**

```bash
uv run python -m river_ksn --help
```
Expected: 显示完整的帮助信息，列出所有参数。

- [ ] **Step 3: Commit**

```bash
git add src/river_ksn/__main__.py
git commit -m "feat: add CLI entry point"
```

---

### Task 9: 端到端集成测试

**Files:**
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: 写集成测试**

`tests/test_pipeline.py`:

```python
"""End-to-end integration tests for the ksn pipeline."""

import os
import csv
import numpy as np
import rasterio

from river_ksn.pipeline import run_pipeline


def test_pipeline_synthetic_dem(tmp_path):
    """使用合成小 DEM 运行完整管道，验证输出文件存在且合理"""
    output_dir = tmp_path / "output"
    size = 50
    dem_path = tmp_path / "dem.tif"

    xs = np.arange(size, dtype=np.float64).reshape(1, -1)
    ys = np.arange(size, dtype=np.float64).reshape(-1, 1)
    center = size / 2.0
    dist = np.sqrt((xs - center) ** 2 + (ys - center) ** 2)

    slope_x = (xs - center) * 2.0
    slope_y = (ys - center) * 2.0

    dem = 100.0 + slope_x + slope_y + dist * 0.5
    dem = dem.astype(np.float32)

    with rasterio.open(
        str(dem_path), 'w',
        driver='GTiff', height=size, width=size,
        count=1, dtype='float32',
        crs='EPSG:4326',
        transform=rasterio.transform.from_origin(0, 0, 30, 30),
    ) as dst:
        dst.write(dem, 1)

    run_pipeline(
        input_path=str(dem_path),
        output_dir=str(output_dir),
        theta=0.45,
        threshold=5,
        intermediate=True,
    )

    stem = "dem"
    for suffix in ["_ksn.tif", "_ksn.csv", "_filled.tif", "_accum.tif", "_slope.tif"]:
        path = output_dir / f"{stem}{suffix}"
        assert path.exists(), f"Missing: {path}"

    with rasterio.open(str(output_dir / "dem_ksn.tif")) as src:
        ksn_data = src.read(1)
        assert ksn_data.shape == (size, size)
        assert src.crs == 'EPSG:4326'
        valid = ksn_data[ksn_data != src.nodata]
        assert len(valid) > 0, "No valid ksn values"

    with open(output_dir / "dem_ksn.csv", 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) > 0
        assert 'ksn' in reader.fieldnames
        for row in rows:
            assert float(row['ksn']) > 0, f"ksn should be positive, got {row['ksn']}"
```

- [ ] **Step 2: 运行集成测试**

```bash
uv run pytest tests/test_pipeline.py -v
```
Expected: 1 passed（可能较慢，约 30-60 秒）。

- [ ] **Step 3: Commit**

```bash
git add tests/test_pipeline.py
git commit -m "test: add end-to-end pipeline integration test"
```

---

### Task 10: 运行全部测试并最终验证

- [ ] **Step 1: 运行全部测试**

```bash
uv run pytest tests/ -v
```
Expected: 全部通过（预计 10 个测试）。

- [ ] **Step 2: 验证 CLI 帮助输出完整**

```bash
uv run python -m river_ksn --help
```

- [ ] **Step 3: 写 README**

`README.md`:

```markdown
# River KSN — 河流陡峭指数计算工具

从 DEM（数字高程模型）计算河流归一化陡峭指数（ksn）。

## 安装

```bash
uv sync
```

## 用法

```bash
# 自动确定 θ 和河道阈值
python -m river_ksn path/to/dem.tif -o results/

# 指定参数
python -m river_ksn dem.tif -o results/ --theta 0.45 --threshold 500

# 输出中间栅格
python -m river_ksn dem.tif --intermediate
```

## 输出

- `<stem>_ksn.tif` — ksn 栅格（GeoTIFF）
- `<stem>_ksn.csv` — 河道像元表格（row, col, drainage_area, slope, ksn）
- `--intermediate` 额外输出: filled DEM, flow accumulation, slope

## 方法

基于河道陡峭-面积幂律关系：`S = ks * A^(-θ)`

- 流向算法：D-infinity（Tarboton, 1997）
- 填洼算法：Wang & Liu (2006)
- θ 自动拟合：对数斜率-面积最小二乘回归
- 河道阈值：流量累积第 95 百分位数

## 依赖

- richdem — 水文分析
- rasterio — GeoTIFF 读写
- numpy, scipy — 数值计算与回归
```

- [ ] **Step 4: 最终 commit**

```bash
git add README.md
git commit -m "docs: add README with usage instructions"
```
