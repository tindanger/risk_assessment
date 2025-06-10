#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Excel转JSON工具

功能：
    将Excel文件转换为JSON格式，支持单个工作表的转换
    主要用于风险评估模型中的数据格式转换需求

运行逻辑：
    1. 读取指定的Excel文件
    2. 将Excel数据转换为字典格式
    3. 将字典数据保存为JSON文件
    4. 提供日志记录转换过程

使用方法：
    直接运行脚本，将使用默认路径的Excel文件转换为JSON
    也可以导入excel_to_json函数到其他模块中使用

依赖：
    pandas - 用于读取Excel文件
    json - 用于JSON格式转换
    os - 用于文件路径操作
    logging - 用于日志记录
"""

import pandas as pd
import json
import os
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def excel_to_json(excel_file, json_file):
    """
    将Excel文件转换为JSON格式
    
    Args:
        excel_file: Excel文件路径
        json_file: 输出的JSON文件路径
    """
    try:
        # 读取Excel文件
        logger.info(f"读取Excel文件: {excel_file}")
        df = pd.read_excel(excel_file)
        
        # 显示数据信息
        logger.info(f"数据形状: {df.shape}")
        logger.info(f"数据列名: {', '.join(df.columns)}")
        
        # 转换为字典
        data = {'Sheet1': df.to_dict('records')}
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(json_file), exist_ok=True)
        
        # 保存为JSON文件
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"已将Excel文件转换为JSON并保存到: {json_file}")
        return True
    except Exception as e:
        logger.error(f"转换失败: {e}")
        return False

if __name__ == "__main__":
    # 设置文件路径
    excel_file = os.path.join('d:\\JQB_Model\\risk_assessment\\data_files', 'test.xlsx')
    output_dir = os.path.join('d:\\JQB_Model\\risk_assessment\\data_files', 'json')
    os.makedirs(output_dir, exist_ok=True)
    json_file = os.path.join(output_dir, 'test.json')
    
    # 执行转换
    excel_to_json(excel_file, json_file)