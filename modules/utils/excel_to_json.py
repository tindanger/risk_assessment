#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Excel到JSON转换工具模块

功能：
    将Excel文件（包括多个工作表）转换为JSON格式并保存到指定目录。
    支持单个文件转换和批量文件转换。
    
运行逻辑：
    1. 读取Excel文件（支持多个工作表）
    2. 将每个工作表转换为字典列表
    3. 将所有工作表数据组织为嵌套字典结构
    4. 生成带时间戳的JSON文件名
    5. 将数据保存为JSON文件
    6. 记录转换过程的日志信息
    
使用方法：
    1. 单个文件转换：excel_to_json(excel_file, json_output_dir=None, logger=None)
    2. 批量文件转换：export_excel_to_json(excel_files, json_output_dir=None, logger=None)
    
依赖：
    - os: 文件路径操作
    - json: JSON序列化
    - pandas: Excel文件读取和数据处理
    - datetime: 生成时间戳
    - logging: 日志记录
"""

import os
import json
import pandas as pd
from datetime import datetime
import logging

def excel_to_json(excel_file, json_output_dir=None, logger=None):
    """
    将Excel文件转换为JSON格式并保存
    
    Args:
        excel_file: Excel文件路径
        json_output_dir: JSON输出目录，如果为None则使用与Excel相同的目录
        logger: 日志对象
    
    Returns:
        str: 生成的JSON文件路径
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    # 获取Excel文件名（不含扩展名）
    excel_basename = os.path.basename(excel_file)
    excel_name = os.path.splitext(excel_basename)[0]
    
    # 确定JSON输出目录
    if json_output_dir is None:
        json_output_dir = os.path.join(os.path.dirname(excel_file), "json_export")
    
    # 创建输出目录（如果不存在）
    if not os.path.exists(json_output_dir):
        os.makedirs(json_output_dir)
        logger.info(f"创建JSON输出目录: {json_output_dir}")
    
    # 读取Excel文件
    logger.info(f"读取Excel文件: {excel_file}")
    try:
        # 读取所有sheet
        excel_data = pd.read_excel(excel_file, sheet_name=None)
        
        # 转换为JSON格式
        result = {}
        for sheet_name, df in excel_data.items():
            # 将DataFrame转换为字典列表
            sheet_data = df.to_dict(orient='records')
            result[sheet_name] = sheet_data
        
        # 生成JSON文件路径
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = os.path.join(json_output_dir, f"{excel_name}_{timestamp}.json")
        
        # 保存JSON文件
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        
        logger.info(f"Excel文件已转换为JSON格式并保存: {json_file}")
        return json_file
    
    except Exception as e:
        logger.error(f"Excel转JSON失败: {str(e)}")
        return None

def export_excel_to_json(excel_files, json_output_dir=None, logger=None):
    """
    批量将Excel文件转换为JSON格式并保存
    
    Args:
        excel_files: Excel文件路径列表
        json_output_dir: JSON输出目录
        logger: 日志对象
    
    Returns:
        list: 生成的JSON文件路径列表
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    json_files = []
    for excel_file in excel_files:
        json_file = excel_to_json(excel_file, json_output_dir, logger)
        if json_file:
            json_files.append(json_file)
    
    return json_files