# 河流陡峭指数计算脚本 — 设计文档

**日期：** 2026-05-31
**状态：** 待审核

---

## 概述

一个 Python CLI 脚本，从 DEM（数字高程模型）计算河流归一化陡峭指数（ksn）。基于河道陡峭-面积幂律关系：`S = ks * A^(-θ)`，其中 S 为坡度，A 为上游汇水面积，θ 为凹度指数参考值。

## 依赖管理

使用 `uv` 管理 Python 依赖。`pyproject.toml` 中声明 `rasterio`、`richdem`、`numpy`、`scipy`。

## 输入

- **格式：** 单波段 GeoTIFF DEM
- 自动读取 CRS、变换矩阵（transform）、NoData 值

## 输出

所有输出写入用户指定目录（默认 `./output`），以输入文件名加后缀命名。

### 最终输出（始终生成）
- `<stem>_ksn.tif` — ksn 栅格，与输入 DEM 同 CRS、同范围、同分辨率，非河道像元为 NoData
- `<stem>_ksn.csv` — 河道像元表格，字段：row, col, drainage_area, slope, ksn

### 中间输出（通过 `--intermediate` 标志启用）
- `<stem>_filled.tif` — 填洼后 DEM
- `<stem>_flowdir.tif` — D-infinity 流向
- `<stem>_accum.tif` — 流量累积（汇水面积，像元数）
- `<stem>_slope.tif` — 沿河道坡度

## CLI 接口

```bash
python -m river_ksn input.tif \
    -o output_dir/ \
    [--theta VALUE] \
    [--threshold VALUE] \
    [--intermediate] \
    [--quiet]
```

| 参数 | 必需 | 默认 | 说明 |
|------|------|------|------|
| `input` | ✅ | — | DEM GeoTIFF 路径 |
| `-o` / `--output` | 否 | `./output` | 输出目录路径 |
| `--theta` | 否 | 自动拟合 | 凹度指数参考值 θ_ref |
| `--threshold` | 否 | 自动确定 | 河道流量累积阈值（像元数） |
| `--intermediate` | 否 | 不输出 | 输出所有中间栅格 |
| `--quiet` | 否 | — | 减少日志输出 |

## 处理管道

```
DEM GeoTIFF
  │  rasterio
  ▼
┌──────────────────────────────┐
│ 1. load_dem()                │← 读取 DEM、CRS、transform
│ 2. fill_sinks()              │← richdem FillDepressions
│ 3. flow_direction()          │← richdem D-infinity
│ 4. flow_accumulation()       │← richdem 流量累积
│ 5. extract_channels()        │← 阈值二元掩膜
│ 6. compute_slope()           │← richdem 坡度
│ 7. calibrate_theta()         │← log(S) ~ log(A) 线性回归
│ 8. compute_ksn()             │← ksn = S / A^(-θ_ref)
│ 9. export()                  │← GeoTIFF + CSV
└──────────────────────────────┘
```

## 核心算法

### θ 自动拟合（对数斜率-面积回归）

1. 取所有河道像元的汇水面积 A 和坡度 S
2. 对 log(S) 和 log(A) 做最小二乘线性回归（scipy.stats.linregress）
3. 所得斜率即 -θ，取绝对值
4. R² < 0.3 时警告并回退到默认 θ = 0.45

### 河道阈值自动确定

取流量累积分布的第 95 百分位数作为河道阈值。该值在处理平坦地形时偏保守，避免将坡面误识别为河道。

### ksn 计算

对每个河道像元：`ksn = S / (A ^ (-θ_ref))`

非河道像元设为 NaN，输出时写为 NoData。

## 坐标参考

- 栅格输出继承输入 DEM 的 CRS 和 geotransform
- CSV 默认输出行列号坐标；可选添加 `--geo` 标志输出地理坐标

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| DEM 文件不存在或无法打开 | 错误信息 + 退出码 1 |
| DEM 不是单波段 | 提示用户，取第一个波段并警告 |
| CRS 缺失 | 警告后继续（栅格输出无投影） |
| 阈值产生零河道像元 | 错误 + 建议降低阈值 |
| 回归 R² < 0.3 | 警告 + 回退默认 θ=0.45 |
| 输出目录无法创建 | 错误 + 退出 |

## 项目结构

```
河流/
├── pyproject.toml
├── README.md
├── src/
│   └── river_ksn/
│       ├── __init__.py
│       ├── __main__.py          # CLI 入口，argparse
│       ├── pipeline.py          # 管道编排
│       ├── dem.py               # DEM 加载、填洼
│       ├── hydrology.py         # 流向、流量累积
│       ├── channel.py           # 河道提取
│       ├── ksn.py               # θ 拟合、ksn 计算
│       └── export.py            # GeoTIFF/CSV 输出
└── tests/
    ├── __init__.py
    ├── test_pipeline.py         # 端到端集成测试
    ├── test_ksn.py              # θ 拟合、ksn 计算测试
    └── test_export.py           # 输出格式测试
```

## 测试策略

- **端到端测试：** 使用 `richdem` 内嵌示例 DEM 或合成小 DEM，验证完整管道输出合理值
- **单元测试：** θ 回归计算、CSV 格式、阈值自动确定
- **运行方式：** `uv run pytest`

## 技术选型

| 组件 | 选择 | 原因 |
|------|------|------|
| DEM 读写 | `rasterio` | GeoTIFF 标准库 |
| 水文分析 | `richdem` | C++ 后端，速度快，API 简洁 |
| 数值计算 | `numpy` | 基础依赖 |
| 回归 | `scipy.stats.linregress` | 可靠且已广泛使用 |
| 包管理 | `uv` | 用户指定 |
| 测试 | `pytest` | 标准工具 |
