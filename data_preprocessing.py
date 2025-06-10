#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据预处理模块

功能：
    处理原始保险订单数据，补充行业分类层级信息，并保存为标准化格式。
    自动查找最新订单数据，支持CSV和Excel格式。
    根据行业代码补充完整的行业层级信息（1-4级）。
    进行数据质量检查，确保数据完整性和准确性。
    作为风险评估模型的数据准备阶段。
    支持多种保险公司的行业分类标准。

运行逻辑：
    1. 自动查找最新的订单数据文件（支持CSV和Excel格式）
    2. 加载行业分类JSON文件，构建行业代码查找字典
    3. 根据原始数据中的行业代码，补充完整的行业层级信息（1-4级）
    4. 删除原始行业字段，保留层级化的行业信息
    5. 保存处理后的数据到指定输出文件
    6. 进行数据质量检查，包括行业层级补全率和关键字段完整率

使用方法：
    1. 直接运行脚本：自动查找最新数据文件并处理
       python data_preprocessing.py
    2. 指定参数运行：自定义输入、行业分类和输出文件路径
       python data_preprocessing.py --input <输入文件> --industry <行业分类文件> --output <输出文件>

输入：
    - 原始订单数据文件（CSV或Excel格式）
    - 行业分类JSON文件（包含行业代码、名称、层级关系）

输出：
    - 处理后的CSV文件，包含补充的行业层级信息
    - 详细的处理日志，包括数据质量检查结果

依赖：
    - pandas: 数据处理和分析
    - json: 解析行业分类文件
    - os, sys: 文件路径操作
    - datetime: 时间戳生成
    - logging: 日志记录
    - glob, re: 文件查找和模式匹配
    - argparse: 命令行参数解析
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime
import logging
import glob
import re

def setup_logger():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def find_latest_data_file(data_dir, prefix='order_data'):
    """查找最新的数据文件
    
    Args:
        data_dir: 数据文件目录
        prefix: 文件名前缀
    
    Returns:
        str: 最新数据文件的完整路径
    """
    # 支持的文件类型
    file_patterns = [f"{prefix}_*.csv", f"{prefix}_*.xlsx"]
    
    all_files = []
    for pattern in file_patterns:
        all_files.extend(glob.glob(os.path.join(data_dir, pattern)))
    
    if not all_files:
        return None
    
    # 从文件名中提取日期
    latest_file = None
    latest_date = None
    
    date_pattern = re.compile(r'(\d{8})')
    
    for file_path in all_files:
        file_name = os.path.basename(file_path)
        match = date_pattern.search(file_name)
        
        if match:
            date_str = match.group(1)
            try:
                file_date = datetime.strptime(date_str, '%Y%m%d')
                
                if latest_date is None or file_date > latest_date:
                    latest_date = file_date
                    latest_file = file_path
            except ValueError:
                # 日期格式不正确，跳过
                continue
    
    return latest_file

def load_data_file(file_path, logger):
    """加载数据文件，支持CSV和Excel格式
    
    Args:
        file_path: 数据文件路径
        logger: 日志对象
    
    Returns:
        DataFrame: 加载的数据
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    
    logger.info(f"加载数据文件: {file_path}")
    
    try:
        if file_ext == '.csv':
            try:
                df = pd.read_csv(file_path, encoding='utf-8')
            except UnicodeDecodeError:
                logger.info("UTF-8编码失败，尝试使用GBK编码...")
                df = pd.read_csv(file_path, encoding='gbk')
        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        else:
            logger.error(f"不支持的文件类型: {file_ext}")
            return None
        
        logger.info(f"数据加载完成，共 {len(df)} 条记录")
        logger.info(f"数据列名: {list(df.columns)}")
        return df
    except Exception as e:
        logger.error(f"加载数据文件失败: {str(e)}")
        return None

def load_industry_classification(json_file_path):
    """加载行业分类JSON文件
    
    Args:
        json_file_path: 行业分类JSON文件路径
    
    Returns:
        dict: 行业分类数据
    """
    with open(json_file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_industry_lookup(industry_data):
    """构建行业代码查找字典
    
    Args:
        industry_data: 行业分类数据
    
    Returns:
        dict: {code: {name, level, parent_code, hierarchy}}
    """
    lookup = {}
    
    def traverse(items, parent_code=None, parent_hierarchy=None):
        for item in items:
            code = item['code']
            name = item['name']
            level = item['level']
            
            # 构建层级路径
            if parent_hierarchy:
                hierarchy = parent_hierarchy + [{'code': code, 'name': name, 'level': level}]
            else:
                hierarchy = [{'code': code, 'name': name, 'level': level}]
            
            lookup[code] = {
                'name': name,
                'level': level,
                'parent_code': parent_code,
                'hierarchy': hierarchy
            }
            
            # 递归处理子级
            if 'children' in item and item['children']:
                traverse(item['children'], code, hierarchy)
    
    traverse(industry_data)
    return lookup

def get_industry_hierarchy(industry_code, industry_lookup):
    """获取行业层级信息
    
    Args:
        industry_code: 行业代码
        industry_lookup: 行业查找字典
    
    Returns:
        dict: 包含1-4级行业信息
    """
    result = {
        '行业1级': '',
        '行业2级': '',
        '行业3级': '',
        '行业4级': ''
    }
    
    if industry_code not in industry_lookup:
        return result
    
    hierarchy = industry_lookup[industry_code]['hierarchy']
    
    # 填充各级行业信息
    for item in hierarchy:
        level = item['level']
        code = item['code']
        name = item['name']
        
        if level == 1:
            result['行业1级'] = f"{code}|{name}"
        elif level == 2:
            result['行业2级'] = f"{code}|{name}"
        elif level == 3:
            result['行业3级'] = f"{code}|{name}"
        elif level == 4:
            result['行业4级'] = f"{code}|{name}"
    
    return result

def process_data(input_file, industry_json_file, output_file, logger):
    """处理数据
    
    Args:
        input_file: 输入文件路径
        industry_json_file: 行业分类JSON文件路径
        output_file: 输出CSV文件路径
        logger: 日志对象
    """
    logger.info("开始数据预处理...")
    
    # 加载行业分类数据
    logger.info("加载行业分类数据...")
    industry_data = load_industry_classification(industry_json_file)
    industry_lookup = build_industry_lookup(industry_data)
    logger.info(f"行业分类数据加载完成，共 {len(industry_lookup)} 个行业代码")
    
    # 加载原始数据
    logger.info("加载原始数据...")
    df = load_data_file(input_file, logger)
    
    if df is None:
        logger.error("数据加载失败，处理终止")
        return False
    
    # 处理行业层级
    logger.info("开始行业层级补全...")
    
    # 初始化新列
    df['行业1级'] = ''
    df['行业2级'] = ''
    df['行业3级'] = ''
    df['行业4级'] = ''
    
    # 逐行处理
    processed_count = 0
    matched_count = 0
    
    for index, row in df.iterrows():
        industry_code = str(row['行业']).strip()
        
        # 获取行业层级信息
        hierarchy_info = get_industry_hierarchy(industry_code, industry_lookup)
        
        # 更新数据
        df.at[index, '行业1级'] = hierarchy_info['行业1级']
        df.at[index, '行业2级'] = hierarchy_info['行业2级']
        df.at[index, '行业3级'] = hierarchy_info['行业3级']
        df.at[index, '行业4级'] = hierarchy_info['行业4级']
        
        if hierarchy_info['行业1级']:  # 如果找到匹配的行业
            matched_count += 1
        
        processed_count += 1
        
        # 每处理1000条记录输出一次进度
        if processed_count % 1000 == 0:
            logger.info(f"已处理 {processed_count}/{len(df)} 条记录")
    
    logger.info(f"行业层级补全完成，匹配成功 {matched_count}/{len(df)} 条记录")
    
    # 删除原始行业字段
    if '行业' in df.columns:
        df = df.drop('行业', axis=1)
        logger.info("已删除原始行业字段")
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"创建输出目录: {output_dir}")
    
    # 保存处理后的数据
    logger.info("保存预处理后的数据...")
    df.to_csv(output_file, index=False, encoding='utf-8')
    
    # 验证保存的文件
    if os.path.exists(output_file):
        file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
        logger.info(f"文件保存成功: {output_file}")
        logger.info(f"文件大小: {file_size:.2f} MB")
    else:
        logger.error("文件保存失败")
        return False
    
    # 数据质量检查
    logger.info("=== 数据质量检查 ===")
    
    # 检查行业层级补全情况
    industry_levels = ['行业1级', '行业2级', '行业3级', '行业4级']
    for level in industry_levels:
        if level in df.columns:
            non_empty_count = df[level].notna().sum()
            non_empty_rate = non_empty_count / len(df) * 100
            logger.info(f"{level} 补全率: {non_empty_rate:.2f}% ({non_empty_count}/{len(df)})")
    
    # 检查关键字段的数据完整性
    key_fields = ['已赚保费', '累计赔付金额', '最终承保人数', '报案数量']
    for field in key_fields:
        if field in df.columns:
            non_null_count = df[field].notna().sum()
            non_null_rate = non_null_count / len(df) * 100
            logger.info(f"{field} 完整率: {non_null_rate:.2f}% ({non_null_count}/{len(df)})")
    
    logger.info("=== 数据预处理完成 ===")
    logger.info(f"预处理后的数据文件: {output_file}")
    
    return True

def main():
    """主函数：执行数据预处理并保存结果"""
    # 设置日志
    logger = setup_logger()
    
    try:
        logger.info("=== 开始数据预处理 ===")
        
        # 基础路径
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, 'data_files')
        industry_json_file = os.path.join(base_dir, 'industry_classification', '国民行业分类_利宝.json')
        
        # 使用时间戳创建唯一的输出文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(data_dir, 'processed', f'processed_data_{timestamp}.csv')
        
        # 自动查找最新的数据文件
        input_file = find_latest_data_file(data_dir)
        
        if not input_file:
            logger.error(f"未找到数据文件，请检查目录: {data_dir}")
            return False
        
        logger.info(f"找到最新数据文件: {input_file}")
        
        # 检查行业分类文件是否存在
        if not os.path.exists(industry_json_file):
            logger.error(f"行业分类文件不存在: {industry_json_file}")
            return False
        
        # 执行数据处理
        success = process_data(input_file, industry_json_file, output_file, logger)
        
        return success
        
    except Exception as e:
        logger.error(f"数据预处理失败: {str(e)}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='数据预处理脚本')
    parser.add_argument('--input', type=str, help='输入文件路径，如不指定则自动查找最新数据文件')
    parser.add_argument('--industry', type=str, help='行业分类JSON文件路径')
    parser.add_argument('--output', type=str, help='输出CSV文件路径，如不指定则自动生成带时间戳的文件名')
    
    args = parser.parse_args()
    
    # 设置日志
    logger = setup_logger()
    
    try:
        # 基础路径
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, 'data_files')
        
        # 处理输入文件路径
        input_file = args.input if args.input else find_latest_data_file(data_dir)
        if not input_file:
            logger.error(f"未找到数据文件，请检查目录: {data_dir}")
            sys.exit(1)
        
        # 处理行业分类文件路径
        industry_json_file = args.industry if args.industry else os.path.join(base_dir, 'industry_classification', '国民行业分类_利宝.json')
        if not os.path.exists(industry_json_file):
            logger.error(f"行业分类文件不存在: {industry_json_file}")
            sys.exit(1)
        
        # 处理输出文件路径
        if args.output:
            output_file = args.output
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(data_dir, 'processed', f'processed_data_{timestamp}.csv')
        
        # 执行数据处理
        success = process_data(input_file, industry_json_file, output_file, logger)
        
        if success:
            print("\n数据预处理完成！")
            print("\n使用方法:")
            print("  python data_preprocessing.py  # 自动查找最新数据文件并处理")
            print("  python data_preprocessing.py --input <输入文件> --industry <行业分类文件> --output <输出文件>  # 自定义路径")
        else:
            print("\n数据预处理失败！")
            sys.exit(1)
    except Exception as e:
        logger.error(f"处理失败: {e}")
        sys.exit(1)