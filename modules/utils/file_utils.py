#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件工具模块

功能：
    提供文件操作相关的工具函数，主要用于保存分析结果到Excel文件，并支持同时导出为JSON格式。
    
运行逻辑：
    1. 创建输出目录（如果不存在）
    2. 生成带时间戳的文件名前缀
    3. 创建结果子目录
    4. 将分析结果保存为Excel文件
    5. 可选择同时将Excel文件导出为JSON格式
    6. 记录文件保存过程的日志信息
    
使用方法：
    save_results_multi(results, output_dir, filename_prefix=None, logger=None, export_json=False, json_output_dir=None)
    
参数说明：
    - results: 分析结果字典 {filename: dataframe}
    - output_dir: 输出目录
    - filename_prefix: 文件名前缀，默认为当前时间戳
    - logger: 日志对象
    - export_json: 是否同时导出为JSON格式
    - json_output_dir: JSON输出目录
    
依赖：
    - os: 文件路径操作
    - pandas: DataFrame保存为Excel
    - datetime: 生成时间戳
    - logging: 日志记录
    - excel_to_json: 导出Excel为JSON格式
"""

import os
import pandas as pd
from datetime import datetime
import logging
from .excel_to_json import export_excel_to_json

def save_results_multi(results, output_dir, filename_prefix=None, logger=None, export_json=False, json_output_dir=None):
    """
    保存多个分析结果到Excel文件
    
    Args:
        results: 分析结果字典 {filename: dataframe}
        output_dir: 输出目录
        filename_prefix: 文件名前缀，默认为当前时间戳
        logger: 日志对象
        export_json: 是否同时导出为JSON格式
        json_output_dir: JSON输出目录，如果为None则在output_dir下创建json_export子目录
    
    Returns:
        list: 保存的文件路径列表
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"创建输出目录: {output_dir}")
    
    # 生成时间戳作为文件名前缀
    if filename_prefix is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_prefix = f"分析结果_{timestamp}"
    
    # 创建输出目录
    result_dir = os.path.join(output_dir, filename_prefix)
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    
    # 保存结果
    saved_files = []
    for name, df in results.items():
        # 构建文件路径
        file_path = os.path.join(result_dir, f"{name}.xlsx")
        
        # 保存为Excel
        df.to_excel(file_path, index=False)
        logger.info(f"结果已保存: {file_path}")
        saved_files.append(file_path)
    
    # 如果需要，同时导出为JSON格式
    if export_json:
        # 确定JSON输出目录
        if json_output_dir is None:
            json_output_dir = os.path.join(result_dir, "json_export")
        
        # 导出为JSON
        json_files = export_excel_to_json(saved_files, json_output_dir, logger)
        logger.info(f"已导出 {len(json_files)} 个JSON文件到 {json_output_dir}")
    
    return saved_files