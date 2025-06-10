#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
风险评分计算器模块

功能：
    提供风险评分计算功能，基于多个风险指标综合评估。
    计算赔付率、出险率、人均赔款等关键指标。
    根据配置的权重计算综合风险评分。
    
运行逻辑：
    1. 初始化风险评分计算器，设置配置和日志对象
    2. 从配置中获取各指标权重（赔付率、占比校准、出险率、人均赔款）
    3. 计算各项风险指标（赔付率、出险率、人均赔款、保费占比）
    4. 对人均赔款进行归一化处理
    5. 根据权重计算综合风险评分（100 - 加权和 × 100）
    6. 处理异常值并确保评分在0-100范围内
    
使用方法：
    1. 初始化计算器：calculator = RiskScoreCalculator(config=config, logger=logger)
    2. 计算风险评分：result_df = calculator.calculate_scores(data_df)
    
依赖：
    - pandas: 数据处理和DataFrame操作
    - numpy: 数值计算
"""

import pandas as pd
import numpy as np

class RiskScoreCalculator:
    """
    风险评分计算器类
    用于计算风险评分
    """
    
    def __init__(self, config=None, logger=None):
        """
        初始化风险评分计算器
        
        Args:
            config: 配置信息
            logger: 日志对象
        """
        self.config = config or {}
        self.logger = logger
        
        # 从配置中获取权重
        weights = self.config.get('scoring_weights', {})
        self.alpha = weights.get('alpha', 0.7)  # 赔付率权重
        self.beta = weights.get('beta', 0.2)    # 占比校准权重
        self.gamma = weights.get('gamma', 0.05)  # 出险率权重
        self.delta = weights.get('delta', 0.05)  # 人均赔款归一化权重
    
    def calculate_scores(self, data):
        """
        计算风险评分
        
        Args:
            data: 包含风险数据的DataFrame
        
        Returns:
            pd.DataFrame: 包含风险评分的DataFrame
        """
        if self.logger:
            self.logger.info("开始计算风险评分...")
        
        # 复制数据，避免修改原始数据
        result = data.copy()
        
        # 计算风险评分
        try:
            # 计算赔付率
            if '累计赔付金额' in result.columns and '已赚保费' in result.columns:
                result['claim_rate'] = result['累计赔付金额'] / result['已赚保费']
            
            # 计算出险率
            if '报案数量' in result.columns and '最终承保人数' in result.columns:
                result['incident_rate'] = result['报案数量'] / result['最终承保人数']
            
            # 计算人均赔款
            if '累计赔付金额' in result.columns and '最终承保人数' in result.columns:
                result['avg_claim_per_person'] = result['累计赔付金额'] / result['最终承保人数']
            
            # 计算占比校准
            if '已赚保费' in result.columns:
                total_premium = result['已赚保费'].sum()
                if total_premium > 0:
                    result['premium_share'] = result['已赚保费'] / total_premium
                else:
                    result['premium_share'] = 0
            
            # 归一化处理
            # 只对人均赔款进行归一化，赔付率和出险率不进行归一化
            if 'avg_claim_per_person' in result.columns:
                max_claim_per_person = result['avg_claim_per_person'].max()
                if max_claim_per_person > 0:
                    # 人均赔款归一化 = 人均赔款/最大人均赔款
                    result['avg_claim_norm'] = result['avg_claim_per_person'] / max_claim_per_person
                else:
                    result['avg_claim_norm'] = 0.0
            
            # 占比校准不需要归一化，直接使用
            result['premium_share_norm'] = result.get('premium_share', 1)
            
            # 计算综合风险评分
            # 风险评分 = 100 - (各项指标 × 权重之和) × 100
            # 评分范围：0-100，数值越高风险越低
            weighted_sum = (
                self.alpha * result.get('claim_rate', 0) +
                self.beta * result.get('premium_share_norm', 1) +
                self.gamma * result.get('incident_rate', 0) +
                self.delta * result.get('avg_claim_norm', 0)
            )
            
            # 修正公式：风险评分 = 100 - (各项指标 × 权重之和) × 100
            result['risk_score'] = 100 - weighted_sum * 100
            
            # 处理NaN和无穷大的值
            result['risk_score'] = result['risk_score'].fillna(50)  # 使用中间值50填充NaN
            result['risk_score'] = result['risk_score'].replace([float('inf'), float('-inf')], 50)  # 处理无穷大的值
            
            # 确保评分在0-100范围内
            result['risk_score'] = result['risk_score'].clip(0, 100)
            
            # 四舍五入到整数
            result['risk_score'] = result['risk_score'].round().astype(int)
            
            if self.logger:
                self.logger.info(f"风险评分计算完成，共 {len(result)} 条记录")
            
            return result
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"风险评分计算失败: {str(e)}")
            raise