#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
风险评估主模块

功能：
    基于预处理后的保险订单数据，计算风险评分并进行多维度分析
    支持按新单续保、伤残、行业、城市等多维度分组分析。
    计算赔付率、出险率、人均赔款等关键风险指标。
    生成风险评分和加费系数，支持Excel和JSON格式输出。
    作为风险评估模型的核心处理阶段。
    提供灵活的配置选项，可通过配置文件调整评分权重和处理逻辑。

运行逻辑：
    1. 加载配置文件，获取评分权重和目录设置
    2. 初始化风险计算器和树分析计算器
    3. 查找并加载最新的预处理数据文件
    4. 计算每条记录的风险评分
    5. 按新单续保、伤残、行业2级、城市进行多维度分组分析
    6. 重新计算分组后的赔付率、出险率、人均赔款等指标
    7. 基于分组后的指标重新计算风险评分
    8. 构建多层级分析树，计算各节点的评分和加费系数
    9. 将结果保存为Excel文件和/或JSON文件
    10. 同时将结果保存到固定路径的JSON文件，供后续应用使用

使用方法：
    1. 直接运行脚本：使用默认配置文件
       python risk_assessment.py
    2. 指定参数运行：
       python risk_assessment.py --config <配置文件> --export-json --json-dir <JSON输出目录> --skip-excel

输入：
    - 预处理后的保险订单数据文件（由data_preprocessing.py生成）
    - 配置文件（包含评分权重、目录设置等）

输出：
    - Excel格式的风险评分结果文件（按分析维度组织的多个工作表）
    - JSON格式的风险评分结果文件（可选）
    - 固定路径的JSON结果文件（供后续应用使用）

依赖：
    - modules.data.cache - 数据缓存模块
    - modules.calculators.risk_calculator - 风险评分计算器
    - modules.calculators.tree_calculator - 树分析计算器
    - modules.utils.file_utils - 文件工具
    - modules.utils.logger - 日志工具
    - yaml, json - 配置和数据格式处理
    - os, sys, glob, re - 文件系统操作
    - datetime - 时间处理
    - argparse - 命令行参数解析
"""

import os
import sys
import argparse
import yaml
import glob
import re
import json
from datetime import datetime
from modules.data.cache import RiskDataCache
from modules.calculators.risk_calculator import RiskScoreCalculator
from modules.calculators.tree_calculator import TreeAnalysisCalculator
from modules.utils.file_utils import save_results_multi
from modules.utils.logger import setup_logger, get_logger

def load_config(config_file):
    """加载配置文件
    
    Args:
        config_file: 配置文件路径
    
    Returns:
        dict: 配置信息
    """
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def find_latest_processed_file(processed_dir, prefix='processed_data'):
    """查找最新的处理后数据文件
    
    Args:
        processed_dir: 处理后数据文件目录
        prefix: 文件名前缀
    
    Returns:
        str: 最新处理后数据文件的完整路径
    """
    # 支持的文件类型
    file_patterns = [f"{prefix}_*.csv", f"{prefix}.csv"]
    
    all_files = []
    for pattern in file_patterns:
        all_files.extend(glob.glob(os.path.join(processed_dir, pattern)))
    
    if not all_files:
        return None
    
    # 从文件名中提取日期
    latest_file = None
    latest_date = None
    
    date_pattern = re.compile(r'(\d{8}_\d{6})')
    
    for file_path in all_files:
        file_name = os.path.basename(file_path)
        
        # 如果是默认文件名，直接返回
        if file_name == f"{prefix}.csv":
            return file_path
        
        match = date_pattern.search(file_name)
        
        if match:
            date_str = match.group(1)
            try:
                file_date = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                
                if latest_date is None or file_date > latest_date:
                    latest_date = file_date
                    latest_file = file_path
            except ValueError:
                # 日期格式不正确，跳过
                continue
    
    return latest_file

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='风险评估工具')
    parser.add_argument('--config', type=str, default='config/risk_assessment.yml', help='配置文件路径')
    parser.add_argument('--export-json', action='store_true', help='是否同时导出JSON格式')
    parser.add_argument('--json-dir', type=str, help='JSON输出目录，默认为在输出目录下创建json_export子目录')
    parser.add_argument('--skip-excel', action='store_true', help='跳过Excel文件生成，只生成JSON文件')
    args = parser.parse_args()
    
    # 设置日志
    logger = setup_logger()
    
    try:
        logger.info("=== 开始风险评估 ===")
        
        # 加载配置
        config_file = args.config
        if not os.path.exists(config_file):
            logger.error(f"配置文件不存在: {config_file}")
            return 1
        
        config = load_config(config_file)
        logger.info(f"配置已加载: {config_file}")
        
        # 初始化数据缓存
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                              config['directories']['original_data_files'])
        data_cache = RiskDataCache(data_dir, logger)
        
        # 初始化计算器
        risk_calculator = RiskScoreCalculator(config, logger)
        tree_calculator = TreeAnalysisCalculator(config, logger)
        
        # 加载数据
        processed_data_dir = os.path.join(data_dir, 'processed')
        
        # 查找最新的处理后数据文件
        processed_data_file = find_latest_processed_file(processed_data_dir)
        
        if not processed_data_file:
            logger.error(f"未找到处理后的数据文件，请检查目录: {processed_data_dir}")
            logger.info("请先运行 data_preprocessing.py 生成预处理数据")
            return 1
        
        logger.info(f"找到最新处理后数据文件: {processed_data_file}")
        
        data = data_cache.load_data(processed_data_file, 'processed_data')
        logger.info(f"数据已加载，共 {len(data)} 条记录")
        
        # 计算风险评分
        scored_data = risk_calculator.calculate_scores(data)
        logger.info("风险评分计算完成")
        
        # 准备结果
        results = {}
        
        # 仅保留新单续保 伤残 行业2级 城市 评分相关结果
        # 多维度分析
        multi_dim_analysis = scored_data.groupby(['新单续保', '伤残', '行业2级', '城市']).agg({
            'risk_score': 'mean',
            '已赚保费': 'sum',
            '累计赔付金额': 'sum',
            '最终承保人数': 'sum',
            '报案数量': 'sum'
            # 移除所有需要重新计算的指标
        }).reset_index()
        
        # 基于分组后的数据重新计算各项指标
        # 计算赔付率
        multi_dim_analysis['claim_rate'] = multi_dim_analysis['累计赔付金额'] / multi_dim_analysis['已赚保费']
        
        # 计算出险率
        multi_dim_analysis['incident_rate'] = multi_dim_analysis['报案数量'] / multi_dim_analysis['最终承保人数']
        
        # 计算人均赔款
        multi_dim_analysis['avg_claim_per_person'] = multi_dim_analysis['累计赔付金额'] / multi_dim_analysis['最终承保人数']
        
        # 人均赔款归一化
        max_claim_per_person = multi_dim_analysis['avg_claim_per_person'].max()
        if max_claim_per_person > 0:
            multi_dim_analysis['avg_claim_norm'] = multi_dim_analysis['avg_claim_per_person'] / max_claim_per_person
        else:
            multi_dim_analysis['avg_claim_norm'] = 0.0
        
        # 基于分组后的已赚保费重新计算占比校准
        total_premium = multi_dim_analysis['已赚保费'].sum()
        if total_premium > 0:
            multi_dim_analysis['premium_share'] = multi_dim_analysis['已赚保费'] / total_premium
        else:
            multi_dim_analysis['premium_share'] = 0
            
        # 重新计算风险评分
        # 获取权重
        alpha = risk_calculator.alpha  # 赔付率权重
        beta = risk_calculator.beta    # 占比校准权重
        gamma = risk_calculator.gamma  # 出险率权重
        delta = risk_calculator.delta  # 人均赔款归一化权重
        
        # 计算加权和
        weighted_sum = (
            alpha * multi_dim_analysis['claim_rate'] +
            beta * multi_dim_analysis['premium_share'] +
            gamma * multi_dim_analysis['incident_rate'] +
            delta * multi_dim_analysis['avg_claim_norm']
        )
        
        # 计算风险评分
        multi_dim_analysis['risk_score'] = 100 - weighted_sum * 100
        
        # 处理NaN和无穷大的值
        multi_dim_analysis['risk_score'] = multi_dim_analysis['risk_score'].fillna(50)
        multi_dim_analysis['risk_score'] = multi_dim_analysis['risk_score'].replace([float('inf'), float('-inf')], 50)
        
        # 确保评分在0-100范围内
        multi_dim_analysis['risk_score'] = multi_dim_analysis['risk_score'].clip(0, 100)
        
        # 四舍五入到整数
        multi_dim_analysis['risk_score'] = multi_dim_analysis['risk_score'].round().astype(int)
            
        # 重命名英文字段为中文
        field_mapping = {
            'claim_rate': '赔付率',
            'incident_rate': '出险率',
            'avg_claim_per_person': '人均赔款',
            'premium_share': '占比校准',
            'avg_claim_norm': '人均赔款归一化'
        }
        multi_dim_analysis = multi_dim_analysis.rename(columns=field_mapping)
        
        results['新单续保+伤残+行业2级+城市分析'] = multi_dim_analysis
        
        # 保存结果
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                config['directories']['output'])
        
        # 确定是否导出JSON（优先使用命令行参数，其次使用配置文件）
        export_json = args.export_json
        if not export_json and 'json_export' in config and 'enabled' in config['json_export']:
            export_json = config['json_export']['enabled']
        
        # 确定JSON输出目录
        json_output_dir = args.json_dir
        if json_output_dir is None and export_json and 'json_export' in config and 'subdirectory' in config['json_export']:
            json_output_dir = os.path.join(output_dir, config['json_export']['subdirectory'])
        
        # 确定是否跳过Excel文件生成（优先使用命令行参数，其次使用配置文件）
        skip_excel = args.skip_excel
        if not skip_excel and 'json_export' in config and 'skip_excel' in config['json_export']:
            skip_excel = config['json_export']['skip_excel']
        
        # 保存结果
        if not skip_excel:
            saved_files = save_results_multi(
                results, 
                output_dir, 
                None,  # 使用默认时间戳作为文件名前缀
                logger,
                export_json,  # 是否同时导出JSON
                json_output_dir  # JSON输出目录
            )
            logger.info(f"结果已保存到 {output_dir}")
        else:
            logger.info("已跳过Excel文件生成")
            saved_files = []
        
        # 导出固定路径的JSON结果
        fixed_json_dir = "d:\\JQB_Model\\risk_assessment\\risk_score"
        if not os.path.exists(fixed_json_dir):
            os.makedirs(fixed_json_dir)
            logger.info(f"创建固定JSON输出目录: {fixed_json_dir}")
        
        # 将结果转换为JSON格式
        json_data = {}
        for name, df in results.items():
            # 在保存JSON前对风险评分进行四舍五入处理
            if 'risk_score' in df.columns:
                df['risk_score'] = df['risk_score'].round().astype(int)
            json_data[name] = df.to_dict(orient='records')
        
        # 保存为固定名称的JSON文件
        fixed_json_path = os.path.join(fixed_json_dir, "last_risk_score.json")
        with open(fixed_json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)
        logger.info(f"结果已导出为固定路径JSON文件: {fixed_json_path}")
        
        if export_json:
            logger.info("结果已同时导出为JSON格式")
        
        logger.info("=== 风险评估完成 ===")
        return 0
        
    except Exception as e:
        logger.error(f"风险评估失败: {str(e)}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    sys.exit(main())