#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据缓存模块

功能：
    提供风险评估数据的缓存和管理功能，避免重复加载相同数据文件。
    支持CSV文件加载（自动处理UTF-8和GBK编码）。
    提供数据缓存的增删改查操作。
    
运行逻辑：
    1. 初始化缓存对象，设置数据目录和日志对象
    2. 加载数据文件时先检查缓存，如存在则直接返回
    3. 如缓存不存在，则加载文件（自动尝试不同编码）
    4. 将加载的数据存入缓存并返回
    5. 提供获取、设置和清除缓存的方法
    
使用方法：
    1. 初始化缓存：cache = RiskDataCache(data_dir="data_files", logger=logger)
    2. 加载并缓存数据：df = cache.load_data(file_path, key=None)
    3. 获取缓存数据：df = cache.get_data(key)
    4. 设置缓存数据：cache.set_data(key, data)
    5. 清除所有缓存：cache.clear_cache()
    
依赖：
    - os: 文件路径操作
    - pandas: 数据加载和处理
"""

import os
import pandas as pd

class RiskDataCache:
    """
    风险数据缓存类
    用于缓存和管理风险评估数据
    """
    
    def __init__(self, data_dir=None, logger=None):
        """
        初始化数据缓存
        
        Args:
            data_dir: 数据目录
            logger: 日志对象
        """
        self.data_dir = data_dir
        self.logger = logger
        self.data_cache = {}
    
    def load_data(self, file_path, key=None):
        """
        加载数据并缓存
        
        Args:
            file_path: 数据文件路径
            key: 缓存键名，默认为文件名
        
        Returns:
            pd.DataFrame: 加载的数据
        """
        if key is None:
            key = os.path.basename(file_path)
        
        # 检查缓存
        if key in self.data_cache:
            if self.logger:
                self.logger.info(f"从缓存加载数据: {key}")
            return self.data_cache[key]
        
        # 加载数据
        if self.logger:
            self.logger.info(f"加载数据文件: {file_path}")
        
        try:
            # 尝试不同编码加载CSV文件
            try:
                df = pd.read_csv(file_path, encoding='utf-8')
            except UnicodeDecodeError:
                if self.logger:
                    self.logger.info(f"UTF-8编码失败，尝试使用GBK编码...")
                df = pd.read_csv(file_path, encoding='gbk')
            
            # 缓存数据
            self.data_cache[key] = df
            
            if self.logger:
                self.logger.info(f"数据已加载并缓存: {key}, 共 {len(df)} 条记录")
            
            return df
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"加载数据失败: {str(e)}")
            raise
    
    def get_data(self, key):
        """
        获取缓存的数据
        
        Args:
            key: 缓存键名
        
        Returns:
            pd.DataFrame: 缓存的数据，如果不存在则返回None
        """
        return self.data_cache.get(key)
    
    def set_data(self, key, data):
        """
        设置缓存数据
        
        Args:
            key: 缓存键名
            data: 要缓存的数据
        """
        self.data_cache[key] = data
        if self.logger:
            self.logger.info(f"数据已缓存: {key}")
    
    def clear_cache(self):
        """
        清除所有缓存
        """
        self.data_cache.clear()
        if self.logger:
            self.logger.info("缓存已清除")