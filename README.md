# 风险评估系统

## 项目介绍

风险评估系统是一个用于保险业务风险分析和评分的工具，通过对保险订单数据进行多维度分析，计算风险评分，帮助业务决策。系统基于Python开发，支持数据预处理、风险评分计算、多维度分析、加费系数计算和结果导出等功能。系统设计灵活，支持多种保险公司的行业分类标准和配置选项。

## 主要功能

- **数据预处理**：处理原始订单数据，进行清洗、转换和行业分类层级补充
- **风险评分计算**：基于赔付率、出险率、人均赔款等指标计算风险评分
- **多维度分析**：按新单续保、伤残、行业分类、城市等维度进行分组分析
- **加费系数计算**：基于风险评分计算加费系数，支持非线性计算和权重调整
- **结果导出**：支持Excel和JSON格式的结果导出
- **风险评分应用**：提供风险评分查询和应用功能，支持多种匹配模式和降级策略

## 系统架构

```
风险评估系统
├── risk_assessment.py      # 主程序入口，风险评估主模块
├── data_preprocessing.py   # 数据预处理模块
├── risk_score_application.py # 风险评分应用模块
├── fkauto.py              # 风险评分加费自动计算模块
├── excel_to_json.py       # Excel到JSON转换工具
├── modules/                # 核心模块
│   ├── calculators/        # 计算器模块
│   │   ├── risk_calculator.py  # 风险评分计算器
│   │   └── tree_calculator.py  # 树形分析计算器
│   ├── data/               # 数据处理模块
│   │   └── cache.py        # 数据缓存
│   └── utils/              # 工具模块
│       ├── excel_to_json.py  # Excel到JSON转换工具
│       ├── file_utils.py   # 文件处理工具
│       └── logger.py       # 日志工具
├── config/                 # 配置文件
│   └── risk_assessment.yml # 主配置文件
├── data_files/             # 数据文件目录
│   ├── order_data_*.csv    # 订单数据文件
│   └── processed/          # 处理后的数据
├── industry_classification/ # 行业分类数据
├── risk_score/             # 风险评分结果
└── Logs/                   # 日志文件
```

## 核心模块说明

### risk_assessment.py
风险评估主模块，用于计算风险评分并进行多维度分析。支持分组分析、指标计算、生成风险评分和加费系数，提供灵活的配置选项，支持Excel和JSON输出（按分析维度组织的多个工作表）。

### data_preprocessing.py
数据预处理模块，用于处理原始保险订单数据、补充行业分类层级信息并保存为标准化格式。确保数据完整性和准确性，支持多种保险公司的行业分类标准。

### risk_score_application.py
风险评分应用模块，提供风险评分查询和应用功能。支持多种匹配模式（精确匹配、行业层级降级匹配、基本匹配）、批量处理和单条查询，处理订单数据，查询风险评分和加费系数。

### fkauto.py
风险评分加费自动计算模块，支持非线性计算、权重调整、多层级条件树查询和计算验证。实现了基于条件树的加费系数查询和计算功能。

## 安装指南

### 系统要求

- Python 3.8 或更高版本
- 依赖包：
  - pandas >= 1.3.0
  - numpy >= 1.21.0
  - PyYAML >= 5.4.1
  - chardet >= 4.0.0
  - openpyxl >= 3.0.7

### 安装步骤

1. 克隆或下载项目到本地
2. 安装依赖包：

```bash
pip install -r requirements.txt
```

## 使用方法

### 数据预处理

首先需要运行数据预处理脚本，处理原始订单数据：

```bash
python data_preprocessing.py [--input-file 文件路径] [--output-dir 输出目录]
```

参数说明：
- `--input-file`：指定输入文件路径，默认自动查找最新的订单数据文件
- `--output-dir`：指定输出目录，默认为 `data_files/processed`

### 风险评估

运行风险评估主程序：

```bash
python risk_assessment.py [--config 配置文件路径] [--export-json] [--json-dir 目录] [--skip-excel]
```

参数说明：
- `--config`：指定配置文件路径，默认为 `config/risk_assessment.yml`
- `--export-json`：同时导出JSON格式结果
- `--json-dir`：指定JSON输出目录
- `--skip-excel`：跳过Excel文件生成，只生成JSON文件

### 风险评分应用

运行风险评分应用程序：

```bash
python risk_score_application.py [--input-file 输入文件] [--output-file 输出文件] [--match-mode 匹配模式]
```

参数说明：
- `--input-file`：指定输入文件路径
- `--output-file`：指定输出文件路径
- `--match-mode`：指定匹配模式，可选值：exact（精确匹配）、industry（行业降级匹配）、basic（基本匹配）

## 配置说明

配置文件位于 `config/risk_assessment.yml`，主要配置项包括：

### 风险评分权重

```yaml
scoring_weights:
  alpha: 0.7  # 赔付率权重
  beta: 0.2   # 占比校准权重
  gamma: 0.05  # 出险率权重
  delta: 0.05  # 人均赔款归一化权重
```

### 目录配置

```yaml
directories:
  original_data_files: "data_files"  # 订单数据文件目录
  logs: "Logs"  # 日志文件目录
  industry_json: "industry_classification"  # 行业分类JSON文件目录
  output: "output"  # 输出目录
```

### 文件命名配置

```yaml
file_patterns:
  order_data_prefix: "order_data"  # 订单数据文件前缀
  industry_json_pattern:  # 行业分类JSON文件匹配模式
    LB: "国民行业分类_利宝"
    PA: "国民行业分类_平安"
  output_filename: "评分结果.xlsx"  # 输出文件名
```

### JSON导出配置

```yaml
json_export:
  enabled: false  # 是否默认启用JSON导出
  subdirectory: "json_export"  # JSON导出子目录名
  skip_excel: true  # 是否默认跳过Excel文件生成
```

### 加费计算配置

```yaml
surcharge_calculation:
  weight: 0.5 # 加费计算的权重系数，默认为1.0
  # 权重>1.0时：加大加费力度
  # 权重<1.0时：减小加费力度
```

### 保险公司配置

```yaml
insurance_company:
  active: "LB"  # 当前激活的保险公司配置 [LB: 利宝, PA: 平安]
  
  # 利宝保险配置
  LB:
    amount_levels:  # 保额等级配置（单位：元）
      min: 100000
      max: 1000000
      step: 100000
    disability_levels:  # 伤残等级配置
      - "十级伤残:3%"
      - "十级伤残:5%"
      - "十级伤残:10%"
  
  # 平安保险配置
  PA:
    amount_levels:  # 保额等级配置（单位：元）
      min: 10000
      max: 1200000
      step: 10000
    disability_levels:  # 伤残等级配置
      - "工标:1%"
      - "工标:3%"
      - "工标:10%"
      - "行标:10%"
```

## 风险评分计算逻辑

风险评分基于以下指标计算：

1. **赔付率**：累计赔付金额 / 已赚保费
2. **出险率**：报案数量 / 最终承保人数
3. **人均赔款**：累计赔付金额 / 最终承保人数
4. **占比校准**：已赚保费 / 总已赚保费

计算公式：

```
风险评分 = 100 - (各项指标 × 权重之和) × 100
```

评分范围：0-100，数值越高风险越低。

## 加费系数计算逻辑

加费系数基于风险评分计算，使用非线性函数进行转换，支持权重调整：

1. 基于风险评分计算基础加费率
2. 应用权重系数调整加费力度
3. 使用条件树查询多层级条件下的加费系数

## 输出结果

系统输出两种格式的结果：

1. **Excel文件**：保存在 `output` 目录下，包含多个工作表，每个工作表对应一个分析维度
2. **JSON文件**：保存在 `risk_score` 目录下，固定文件名为 `last_risk_score.json`

## 日志

系统运行日志保存在 `Logs` 目录下，文件名格式为 `risk_assessment_YYYYMMDD_HHMMSS.log`。

## 常见问题

1. **找不到处理后的数据文件**
   - 请先运行 `data_preprocessing.py` 生成预处理数据

2. **配置文件不存在**
   - 检查 `config/risk_assessment.yml` 文件是否存在

3. **数据格式错误**
   - 确保原始数据文件格式正确，包含必要的字段

4. **匹配不到风险评分**
   - 检查匹配条件是否正确
   - 尝试使用不同的匹配模式（精确匹配、行业降级匹配、基本匹配）

## 维护与更新

定期检查和更新以下内容：

1. 风险评分权重配置
2. 行业分类数据
3. 加费计算权重
4. 依赖包版本

## 开发者说明

系统代码已添加详细的顶部注释，包括功能说明、运行逻辑、使用方法和依赖说明，便于开发者理解和维护代码。主要文件包括：

- **risk_assessment.py**：风险评估主模块
- **data_preprocessing.py**：数据预处理模块
- **risk_score_application.py**：风险评分应用模块
- **fkauto.py**：风险评分加费自动计算模块