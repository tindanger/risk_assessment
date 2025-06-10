#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日志工具模块

功能：
    提供日志设置和获取功能，支持同时输出到文件和控制台。
    使用单例模式管理全局日志对象，确保整个应用使用统一的日志配置。
    
运行逻辑：
    1. 创建日志目录（如果不存在）
    2. 生成带时间戳的日志文件名
    3. 配置日志格式和处理器（文件和控制台输出）
    4. 初始化全局日志对象
    5. 提供获取日志对象的接口，确保单例模式
    
使用方法：
    1. 初始化日志：logger = setup_logger(log_dir="Logs", log_level=logging.INFO)
    2. 获取日志对象：logger = get_logger()
    3. 记录日志：logger.info("信息"), logger.error("错误"), logger.warning("警告")
    
依赖：
    - os: 文件路径操作
    - sys: 标准输出流
    - logging: 日志功能
    - datetime: 生成时间戳
"""

import os
import sys
import logging
from datetime import datetime

# 全局日志对象
_logger = None

def setup_logger(log_dir="Logs", log_level=logging.INFO):
    """
    设置日志
    
    Args:
        log_dir: 日志目录
        log_level: 日志级别
    
    Returns:
        logging.Logger: 日志对象
    """
    global _logger
    
    # 创建日志目录
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 生成日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"risk_assessment_{timestamp}.log")
    
    # 配置日志
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 获取日志对象
    _logger = logging.getLogger("risk_assessment")
    _logger.info(f"日志已设置，日志文件: {log_file}")
    
    return _logger

def get_logger():
    """
    获取日志对象
    
    Returns:
        logging.Logger: 日志对象
    """
    global _logger
    
    # 如果日志对象未初始化，则初始化
    if _logger is None:
        _logger = setup_logger()
    
    return _logger