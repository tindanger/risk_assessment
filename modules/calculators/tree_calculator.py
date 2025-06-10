#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
树形分析计算器模块

功能：
    提供基于树形结构的风险分析功能，支持多维度分层分析。
    构建分析树，计算各节点的风险评分和加费系数。
    将树形结构转换为DataFrame用于后续分析和展示。
    
运行逻辑：
    1. 初始化树形分析计算器，设置配置和日志对象
    2. 根据指定维度（如省份、行业层级）构建分析树
    3. 计算树中各节点的评分（叶子节点取数据平均值，非叶子节点取子节点平均值）
    4. 根据评分计算各节点的加费系数（使用分段函数）
    5. 将树形结构转换为DataFrame，包含各维度值、评分和加费系数
    
使用方法：
    1. 初始化计算器：calculator = TreeAnalysisCalculator(config=config, logger=logger)
    2. 构建分析树：calculator.build_tree(data, dimensions=['省份', '行业1级', '行业2级'])
    3. 计算节点评分：calculator.calculate_tree_scores(score_field='risk_score')
    4. 计算加费系数：calculator.calculate_surcharges()
    5. 转换为DataFrame：df = calculator.tree_to_dataframe(dimensions=['省份', '行业1级', '行业2级'])
    
依赖：
    - pandas: 数据处理和DataFrame操作
    - numpy: 数值计算
"""

import pandas as pd
import numpy as np

class TreeNode:
    """
    树节点类
    用于构建分析树
    """
    def __init__(self, name=None, value=None):
        self.name = name
        self.value = value
        self.children = {}
        self.score = None
        self.surcharge = None
        self.data = None

class TreeAnalysisCalculator:
    """
    树形分析计算器类
    用于进行树形结构的风险分析
    """
    
    def __init__(self, config=None, logger=None):
        """
        初始化树形分析计算器
        
        Args:
            config: 配置信息
            logger: 日志对象
        """
        self.config = config or {}
        self.logger = logger
        self.root = TreeNode("root")
    
    def build_tree(self, data, dimensions):
        """
        根据指定维度构建分析树
        
        Args:
            data: 数据DataFrame
            dimensions: 维度列表，如['省份', '行业1级', '行业2级']
        
        Returns:
            TreeNode: 树的根节点
        """
        if self.logger:
            self.logger.info(f"开始构建分析树，维度: {dimensions}")
        
        # 重置根节点
        self.root = TreeNode("root")
        
        # 遍历数据构建树
        for _, row in data.iterrows():
            current = self.root
            path = []
            
            # 按维度构建路径
            for dim in dimensions:
                if dim in row and pd.notna(row[dim]):
                    value = row[dim]
                    path.append(value)
                    
                    # 如果节点不存在，则创建
                    if value not in current.children:
                        current.children[value] = TreeNode(dim, value)
                    
                    # 移动到子节点
                    current = current.children[value]
            
            # 在叶子节点存储数据
            if not current.children and path:  # 确保是叶子节点且路径非空
                if current.data is None:
                    current.data = []
                current.data.append(row.to_dict())
        
        if self.logger:
            self.logger.info("分析树构建完成")
        
        return self.root
    
    def calculate_tree_scores(self, root=None, score_field='risk_score'):
        """
        计算树中各节点的评分
        
        Args:
            root: 树的根节点，默认为self.root
            score_field: 评分字段名
        
        Returns:
            TreeNode: 计算后的树根节点
        """
        if root is None:
            root = self.root
        
        if self.logger:
            self.logger.info("开始计算树节点评分...")
        
        def calculate_node_score(node):
            # 如果是叶子节点且有数据
            if not node.children and node.data:
                # 从数据中提取评分
                scores = [item.get(score_field, 0) for item in node.data if score_field in item]
                if scores:
                    node.score = np.mean(scores)
                return node.score
            
            # 如果有子节点，递归计算子节点评分
            if node.children:
                scores = []
                for child in node.children.values():
                    child_score = calculate_node_score(child)
                    if child_score is not None:
                        scores.append(child_score)
                
                if scores:
                    node.score = np.mean(scores)
                return node.score
            
            return None
        
        # 计算根节点评分
        calculate_node_score(root)
        
        if self.logger:
            self.logger.info("树节点评分计算完成")
        
        return root
    
    def calculate_surcharges(self, root=None):
        """
        计算树中各节点的加费系数
        
        Args:
            root: 树的根节点，默认为self.root
        
        Returns:
            TreeNode: 计算后的树根节点
        """
        if root is None:
            root = self.root
        
        if self.logger:
            self.logger.info("开始计算加费系数...")
        
        def calculate_node_surcharge(node):
            # 如果节点有评分，计算加费系数
            if node.score is not None:
                node.surcharge = self.calculate_surcharge(node.score)
            
            # 递归计算子节点
            for child in node.children.values():
                calculate_node_surcharge(child)
        
        # 计算根节点及所有子节点的加费系数
        calculate_node_surcharge(root)
        
        if self.logger:
            self.logger.info("加费系数计算完成")
        
        return root
    
    def calculate_surcharge(self, score):
        """
        根据评分计算加费系数
        
        Args:
            score: 风险评分
        
        Returns:
            float: 加费系数
        """
        if score >= 100:
            return 0.0
        elif score <= 0:
            return 1000.0
        
        # 分段计算加费系数
        if score >= 60:
            # 60-100分，较缓慢增长
            base = 40 + (100 - score) * 3
        elif score >= 40:
            # 40-60分，中等速度增长
            base = 160 + (60 - score) * 8
        else:
            # 0-40分，快速增长
            base = 320 + (40 - score) * 17
        
        return round(base / 100, 2)  # 转换为小数并保留两位小数
    
    def tree_to_dataframe(self, root=None, dimensions=None):
        """
        将树转换为DataFrame
        
        Args:
            root: 树的根节点，默认为self.root
            dimensions: 维度列表
        
        Returns:
            pd.DataFrame: 转换后的DataFrame
        """
        if root is None:
            root = self.root
        
        if dimensions is None:
            dimensions = []
        
        if self.logger:
            self.logger.info("开始将树转换为DataFrame...")
        
        # 存储结果的列表
        results = []
        
        def traverse_tree(node, path, values):
            # 如果是叶子节点
            if not node.children:
                # 创建结果行
                row = {}
                for i, dim in enumerate(path):
                    if i < len(dimensions):
                        row[dimensions[i]] = dim
                
                # 添加评分和加费系数
                row['risk_score'] = node.score
                row['surcharge'] = node.surcharge
                
                # 添加其他值
                row.update(values)
                
                results.append(row)
                return
            
            # 递归遍历子节点
            for value, child in node.children.items():
                new_path = path + [value]
                new_values = values.copy()
                if child.score is not None:
                    new_values[f"{child.name}_score"] = child.score
                if child.surcharge is not None:
                    new_values[f"{child.name}_surcharge"] = child.surcharge
                traverse_tree(child, new_path, new_values)
        
        # 从根节点开始遍历
        traverse_tree(root, [], {})
        
        # 转换为DataFrame
        df = pd.DataFrame(results)
        
        if self.logger:
            self.logger.info(f"树转换为DataFrame完成，共 {len(df)} 行")
        
        return df