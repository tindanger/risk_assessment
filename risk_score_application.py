#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
风险评分应用模块

功能：
    提供风险评分查询和应用功能，支持多种匹配模式和降级策略。
    处理保险订单数据，查询对应的风险评分和加费系数。
    支持精确匹配、部分匹配（忽略行业2级）、基本匹配（省份和新单续保）、省份匹配和行业1级匹配等多级降级策略。
    提供批量处理和单条查询两种使用模式。
    支持CSV和Excel格式的输入输出。
    集成了行业分类层级处理功能，可自动补充行业层级信息。
    
运行逻辑：
    1. 加载风险评分数据（JSON格式）
    2. 解析订单数据（CSV或Excel格式）
    3. 提取订单的关键信息（省份、城市、行业等）
    4. 补充行业层级信息（行业1级、行业2级等）
    5. 按多级匹配策略查询风险评分：
       - 精确匹配：所有条件完全匹配
       - 部分匹配：忽略行业2级，只匹配其他条件
       - 基本匹配：只匹配省份和新单续保
       - 省份匹配：只匹配省份
       - 行业1级匹配：只匹配行业1级
    6. 根据风险评分计算加费系数（调用fkauto模块）
    7. 输出结果到CSV或Excel文件
    
使用方法：
    1. 命令行运行：
       python risk_score_application.py --risk-data <风险评分JSON文件> --order-data <订单数据文件> --output <输出文件>
    2. 交互式查询：
       python risk_score_application.py --interactive
    3. API调用：
       from risk_score_application import RiskScoreLookup
       lookup = RiskScoreLookup(json_file_path)
       result = lookup.lookup_risk_score(query_data)
    
依赖：
    - pandas: 数据处理和分析
    - json: 读取风险评分数据
    - fkauto: 加费系数计算
    - logging: 日志记录
    - argparse: 命令行参数解析
    - datetime: 时间处理
    - csv: CSV文件处理
    - os: 文件路径操作
    - random: 随机数生成（用于测试）
"""

import json
import pandas as pd
import os
import logging
import argparse
from datetime import datetime
import csv
import random

# 导入加费计算模块
import fkauto

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RiskScoreLookup:
    def __init__(self, json_file_path):
        """
        初始化风险评分查询类
        
        Args:
            json_file_path: JSON文件路径，包含风险评分数据
        """
        self.json_file_path = json_file_path
        self.risk_data = None
        self.load_risk_data()
    
    def load_risk_data(self):
        """
        加载风险评分数据
        """
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 将JSON数据转换为DataFrame以便于查询
                # 检查数据结构，确定正确的键
                if 'Sheet1' in data:
                    self.risk_data = pd.DataFrame(data['Sheet1'])
                elif '新单续保+伤残+行业2级+城市分析' in data:
                    self.risk_data = pd.DataFrame(data['新单续保+伤残+行业2级+城市分析'])
                else:
                    # 尝试使用第一个键
                    first_key = list(data.keys())[0]
                    self.risk_data = pd.DataFrame(data[first_key])
                
                logger.info(f"成功加载风险评分数据，共{len(self.risk_data)}条记录")
                # 显示数据的列名
                logger.info(f"数据列名: {', '.join(self.risk_data.columns)}")
        except Exception as e:
            logger.error(f"加载风险评分数据失败: {e}")
            raise
    
    def get_unique_values(self, column_name):
        """
        获取指定列的唯一值
        
        Args:
            column_name: 列名
        
        Returns:
            唯一值列表
        """
        if self.risk_data is None:
            logger.error("风险评分数据未加载")
            return []
        
        if column_name not in self.risk_data.columns:
            logger.warning(f"列名 {column_name} 不存在")
            return []
        
        return sorted(self.risk_data[column_name].unique().tolist())
    
    def lookup_risk_score(self, query_data):
        """
        查询风险评分
        
        Args:
            query_data: 包含查询条件的字典，例如：
                {
                    '新单续保': '新单',
                    '伤残': '十级伤残:10%',
                    '行业1级': 'C|制造业',
                    '省份': '江苏省',
                    '行业2级': 'C034|通用设备制造业'
                }
        
        Returns:
            匹配的风险评分记录，如果没有完全匹配，则返回最接近的记录
        """
        if self.risk_data is None:
            logger.error("风险评分数据未加载")
            return None
        
        # 创建查询条件
        query_conditions = []
        for key, value in query_data.items():
            if key in self.risk_data.columns:
                query_conditions.append(f"{key} == '{value}'")
        
        # 如果没有有效的查询条件，返回None
        if not query_conditions:
            logger.warning("没有有效的查询条件")
            return None
        
        # 构建查询表达式
        query_expr = ' & '.join(query_conditions)
        
        try:
            # 尝试精确匹配
            result = self.risk_data.query(query_expr)
            
            if len(result) > 0:
                logger.info(f"找到{len(result)}条精确匹配记录")
                return {
                    'match_type': '精确匹配',
                    'records': result.to_dict('records'),
                    'avg_score': result['risk_score'].mean()
                }
            else:
                logger.info("未找到精确匹配记录，尝试部分匹配")
                
                # 如果没有精确匹配，尝试部分匹配
                # 移除行业2级条件，只匹配行业1级
                if '行业2级' in query_data and '行业1级' in query_data:
                    partial_conditions = [cond for cond in query_conditions if '行业2级' not in cond]
                    partial_query = ' & '.join(partial_conditions)
                    result = self.risk_data.query(partial_query)
                    
                    if len(result) > 0:
                        logger.info(f"找到{len(result)}条行业1级匹配记录")
                        # 按行业1级分组并计算平均风险评分
                        avg_score = result['risk_score'].mean()
                        logger.info(f"行业1级平均风险评分: {avg_score}")
                        return {
                            'match_type': '行业1级匹配',
                            'records': result.to_dict('records'),
                            'avg_score': avg_score
                        }
                
                # 如果仍然没有匹配，只匹配省份和新单续保
                basic_conditions = []
                for key in ['省份', '新单续保']:
                    if key in query_data:
                        basic_conditions.append(f"{key} == '{query_data[key]}'")
                
                if basic_conditions:
                    basic_query = ' & '.join(basic_conditions)
                    result = self.risk_data.query(basic_query)
                    
                    if len(result) > 0:
                        logger.info(f"找到{len(result)}条基本匹配记录")
                        avg_score = result['risk_score'].mean()
                        logger.info(f"基本匹配平均风险评分: {avg_score}")
                        return {
                            'match_type': '基本匹配',
                            'records': result.to_dict('records'),
                            'avg_score': avg_score
                        }
                
                # 如果仍然没有匹配，只匹配省份
                if '省份' in query_data:
                    province_query = f"省份 == '{query_data['省份']}'"  
                    result = self.risk_data.query(province_query)
                    
                    if len(result) > 0:
                        logger.info(f"找到{len(result)}条省份匹配记录")
                        avg_score = result['risk_score'].mean()
                        logger.info(f"省份匹配平均风险评分: {avg_score}")
                        return {
                            'match_type': '省份匹配',
                            'records': result.to_dict('records'),
                            'avg_score': avg_score
                        }
                
                # 如果仍然没有匹配，只匹配行业1级
                if '行业1级' in query_data:
                    industry_query = f"行业1级 == '{query_data['行业1级']}'"  
                    result = self.risk_data.query(industry_query)
                    
                    if len(result) > 0:
                        logger.info(f"找到{len(result)}条行业匹配记录")
                        avg_score = result['risk_score'].mean()
                        logger.info(f"行业匹配平均风险评分: {avg_score}")
                        return {
                            'match_type': '行业匹配',
                            'records': result.to_dict('records'),
                            'avg_score': avg_score
                        }
                
                logger.warning("未找到任何匹配记录")
                return None
                
        except Exception as e:
            logger.error(f"查询风险评分时出错: {e}")
            return None

class DataGenerator:
    """
    数据生成器，用于生成模拟数据
    """
    def __init__(self, risk_lookup):
        self.risk_lookup = risk_lookup
        self.provinces = self.risk_lookup.get_unique_values('省份')
        self.industries_l1 = self.risk_lookup.get_unique_values('行业1级')
        self.industries_l2 = {}
        self.disabilities = self.risk_lookup.get_unique_values('伤残')
        self.policy_types = self.risk_lookup.get_unique_values('新单续保')
        
        # 为每个行业1级获取对应的行业2级
        for industry_l1 in self.industries_l1:
            industry_l1_data = self.risk_lookup.risk_data[self.risk_lookup.risk_data['行业1级'] == industry_l1]
            self.industries_l2[industry_l1] = industry_l1_data['行业2级'].unique().tolist()
    
    def generate_sample_data(self, num_samples=100):
        """
        生成样本数据
        
        Args:
            num_samples: 样本数量
        
        Returns:
            样本数据列表
        """
        samples = []
        for _ in range(num_samples):
            # 随机选择省份、行业、伤残等级和新单续保类型
            province = random.choice(self.provinces)
            industry_l1 = random.choice(self.industries_l1)
            industry_l2 = random.choice(self.industries_l2[industry_l1]) if industry_l1 in self.industries_l2 and self.industries_l2[industry_l1] else ''
            disability = random.choice(self.disabilities)
            policy_type = random.choice(self.policy_types)
            
            # 生成随机保额
            insured_amount = round(random.uniform(10000, 1000000), 2)
            
            sample = {
                '省份': province,
                '行业1级': industry_l1,
                '行业2级': industry_l2,
                '伤残': disability,
                '新单续保': policy_type,
                '保额': insured_amount
            }
            samples.append(sample)
        
        return samples
    
    def save_to_csv(self, samples, output_file):
        """
        将样本数据保存为CSV文件
        
        Args:
            samples: 样本数据列表
            output_file: 输出文件路径
        """
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=samples[0].keys())
                writer.writeheader()
                writer.writerows(samples)
            logger.info(f"成功将{len(samples)}条样本数据保存到{output_file}")
        except Exception as e:
            logger.error(f"保存样本数据失败: {e}")

class RiskScoreApplication:
    """
    风险评分应用，用于加载数据并查询风险评分
    """
    def __init__(self, risk_lookup):
        self.risk_lookup = risk_lookup
    
    def load_data_from_csv(self, csv_file):
        """
        从CSV文件加载数据
        
        Args:
            csv_file: CSV文件路径
        
        Returns:
            加载的数据列表
        """
        try:
            data = []
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(row)
            logger.info(f"成功从{csv_file}加载{len(data)}条数据")
            return data
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            return []
    
    def process_data(self, data):
        """
        处理数据，为每条数据查询风险评分
        
        Args:
            data: 数据列表
        
        Returns:
            处理后的数据列表，包含风险评分
        """
        processed_data = []
        for i, item in enumerate(data):
            logger.info(f"处理第{i+1}/{len(data)}条数据: {item}")
            
            # 构建查询条件
            query_data = {
                '省份': item['省份'],
                '行业1级': item['行业1级'],
                '行业2级': item['行业2级'] if '行业2级' in item else '',
                '伤残': item['伤残'],
                '新单续保': item['新单续保']
            }
            
            # 查询风险评分
            result = self.risk_lookup.lookup_risk_score(query_data)
            
            # 添加风险评分到原始数据
            processed_item = item.copy()
            if result:
                processed_item['风险评分'] = result['avg_score']
                processed_item['匹配类型'] = result['match_type']
                processed_item['匹配记录数'] = len(result['records'])
            else:
                processed_item['风险评分'] = 50  # 默认风险评分
                processed_item['匹配类型'] = '无匹配'
                processed_item['匹配记录数'] = 0
            
            processed_data.append(processed_item)
        
        return processed_data
    
    def save_results_to_csv(self, data, output_file):
        """
        将处理结果保存为CSV文件
        
        Args:
            data: 处理后的数据列表
            output_file: 输出文件路径
        """
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            logger.info(f"成功将{len(data)}条处理结果保存到{output_file}")
        except Exception as e:
            logger.error(f"保存处理结果失败: {e}")
    
    def run(self, input_file, output_file):
        """
        运行风险评分应用
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
        """
        # 加载数据
        data = self.load_data_from_csv(input_file)
        if not data:
            logger.error("没有加载到数据，退出处理")
            return
        
        # 处理数据
        processed_data = self.process_data(data)
        
        # 保存结果
        self.save_results_to_csv(processed_data, output_file)
        
        # 统计结果
        self.analyze_results(processed_data)
    
    def analyze_results(self, data):
        """
        分析处理结果
        
        Args:
            data: 处理后的数据列表
        """
        # 统计匹配类型分布
        match_types = {}
        for item in data:
            match_type = item['匹配类型']
            match_types[match_type] = match_types.get(match_type, 0) + 1
        
        logger.info("\n匹配类型分布:")
        for match_type, count in match_types.items():
            logger.info(f"  {match_type}: {count}条 ({count/len(data)*100:.2f}%)")
        
        # 统计风险评分分布
        risk_scores = [float(item['风险评分']) for item in data]
        avg_score = sum(risk_scores) / len(risk_scores)
        min_score = min(risk_scores)
        max_score = max(risk_scores)
        
        logger.info("\n风险评分统计:")
        logger.info(f"  平均风险评分: {avg_score:.2f}")
        logger.info(f"  最低风险评分: {min_score:.2f}")
        logger.info(f"  最高风险评分: {max_score:.2f}")
        
        # 按省份统计平均风险评分
        province_scores = {}
        for item in data:
            province = item['省份']
            score = float(item['风险评分'])
            if province not in province_scores:
                province_scores[province] = []
            province_scores[province].append(score)
        
        logger.info("\n按省份统计平均风险评分:")
        for province, scores in province_scores.items():
            avg = sum(scores) / len(scores)
            logger.info(f"  {province}: {avg:.2f}")

class ExactMatchApplication:
    """
    精确匹配应用，用于将test.json中的订单与last_risk_score.json中的风险评分进行精确匹配
    """
    def __init__(self):
        # 固定路径
        self.test_data_path = "d:\\JQB_Model\\risk_assessment\\data_files\\json\\test.json"
        self.risk_score_path = "d:\\JQB_Model\\risk_assessment\\risk_score\\last_risk_score.json"
        self.industry_json_path = "d:\\JQB_Model\\risk_assessment\\industry_classification\\国民行业分类_利宝.json"
        self.test_data = None
        self.risk_score_data = None
        self.industry_lookup = None
        
        # 加载数据
        self.load_data()
        self.load_industry_classification()
    
    def load_data(self):
        """
        加载测试数据和风险评分数据
        """
        try:
            # 加载测试数据
            with open(self.test_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.test_data = pd.DataFrame(data['Sheet1'])
                logger.info(f"成功加载测试数据，共{len(self.test_data)}条记录")
                logger.info(f"测试数据列名: {', '.join(self.test_data.columns)}")
            
            # 加载风险评分数据
            with open(self.risk_score_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 获取第一个键
                first_key = list(data.keys())[0]
                self.risk_score_data = pd.DataFrame(data[first_key])
                logger.info(f"成功加载风险评分数据，共{len(self.risk_score_data)}条记录")
                logger.info(f"风险评分数据列名: {', '.join(self.risk_score_data.columns)}")
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            raise
    
    def load_industry_classification(self):
        """
        加载行业分类数据并构建查找字典
        """
        try:
            with open(self.industry_json_path, 'r', encoding='utf-8') as f:
                industry_data = json.load(f)
                logger.info(f"成功加载行业分类数据")
                
                # 构建行业代码查找字典
                self.industry_lookup = self.build_industry_lookup(industry_data)
                logger.info(f"成功构建行业查找字典，共{len(self.industry_lookup)}个行业代码")
        except Exception as e:
            logger.error(f"加载行业分类数据失败: {e}")
            raise
    
    def build_industry_lookup(self, industry_data):
        """
        构建行业代码查找字典
        
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
    
    def get_industry_hierarchy(self, industry_code):
        """
        获取行业层级信息
        
        Args:
            industry_code: 行业代码
        
        Returns:
            dict: 包含1-4级行业信息
        """
        result = {
            '行业1级': '',
            '行业2级': '',
            '行业3级': '',
            '行业4级': ''
        }
        
        if not industry_code or industry_code not in self.industry_lookup:
            return result
        
        hierarchy = self.industry_lookup[industry_code]['hierarchy']
        
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
    
    def match_records(self):
        """
        对每个订单进行精确匹配
        """
        results = []
        
        # 添加行业层级列
        self.test_data['行业1级'] = ''
        self.test_data['行业2级'] = ''
        self.test_data['行业3级'] = ''
        self.test_data['行业4级'] = ''
        
        # 先处理行业层级
        for index, row in self.test_data.iterrows():
            industry_code = str(row['行业']).strip()
            
            # 获取行业层级信息
            hierarchy_info = self.get_industry_hierarchy(industry_code)
            
            # 更新数据
            self.test_data.at[index, '行业1级'] = hierarchy_info['行业1级']
            self.test_data.at[index, '行业2级'] = hierarchy_info['行业2级']
            self.test_data.at[index, '行业3级'] = hierarchy_info['行业3级']
            self.test_data.at[index, '行业4级'] = hierarchy_info['行业4级']
        
        logger.info("行业层级补全完成")
        
        # 进行精确匹配
        for _, order in self.test_data.iterrows():
            # 提取匹配字段
            match_fields = {}
            
            # 提取订单信息
            order_id = order['订单编号']
            policy_type = order['新单续保']
            disability = order['伤残']
            city = order['城市']
            industry_l2 = order['行业2级']
            
            # 构建匹配条件
            match_conditions = []
            
            # 添加新单续保条件
            if '新单续保' in self.risk_score_data.columns and policy_type:
                match_conditions.append(f"新单续保 == '{policy_type}'")
                match_fields['新单续保'] = policy_type
            
            # 添加伤残条件
            if '伤残' in self.risk_score_data.columns and disability:
                match_conditions.append(f"伤残 == '{disability}'")
                match_fields['伤残'] = disability
            
            # 添加城市条件
            if '城市' in self.risk_score_data.columns and city:
                match_conditions.append(f"城市 == '{city}'")
                match_fields['城市'] = city
            
            # 添加行业2级条件
            if '行业2级' in self.risk_score_data.columns and industry_l2:
                match_conditions.append(f"行业2级 == '{industry_l2}'")
                match_fields['行业2级'] = industry_l2
            
            # 构建查询表达式
            query_expr = ' & '.join(match_conditions) if match_conditions else ""
            
            # 查询结果
            result = {}
            result['订单编号'] = order_id
            
            # 复制匹配字段到结果中
            for key, value in match_fields.items():
                result[key] = value
            
            # 如果有查询条件，尝试精确匹配
            if query_expr:
                try:
                    matched_records = self.risk_score_data.query(query_expr)
                    
                    if len(matched_records) > 0:
                        # 找到匹配记录
                        result['匹配状态'] = '精确匹配'
                        risk_score = matched_records['risk_score'].iloc[0]
                        
                        # 确保风险评分是数值类型
                        try:
                            risk_score = float(risk_score)
                            result['风险评分'] = risk_score
                            
                            # 计算加费率
                            surcharge = fkauto.calculate_nonlinear_surcharge(risk_score)
                            result['加费率'] = surcharge
                        except (ValueError, TypeError):
                            result['风险评分'] = risk_score
                            logger.warning(f"订单 {order_id} 的风险评分 {risk_score} 不是有效的数值，无法计算加费率")
                        
                        result['匹配记录数'] = len(matched_records)
                    else:
                        # 没有找到精确匹配，尝试部分匹配
                        # 移除行业2级条件，只匹配新单续保、伤残和城市
                        partial_conditions = [cond for cond in match_conditions if '行业2级' not in cond]
                        if partial_conditions:
                            partial_query = ' & '.join(partial_conditions)
                            partial_matched = self.risk_score_data.query(partial_query)
                            
                            if len(partial_matched) > 0:
                                result['匹配状态'] = '部分匹配(无行业)'
                                risk_score = partial_matched['risk_score'].mean()
                                
                                # 确保风险评分是数值类型
                                try:
                                    risk_score = float(risk_score)
                                    result['风险评分'] = risk_score
                                    
                                    # 计算加费率
                                    surcharge = fkauto.calculate_nonlinear_surcharge(risk_score)
                                    result['加费率'] = surcharge
                                except (ValueError, TypeError):
                                    result['风险评分'] = risk_score
                                    logger.warning(f"订单 {order_id} 的风险评分 {risk_score} 不是有效的数值，无法计算加费率")
                                
                                result['匹配记录数'] = len(partial_matched)
                            else:
                                result['匹配状态'] = '无匹配'
                                result['风险评分'] = '无匹配'
                                result['匹配记录数'] = 0
                        else:
                            result['匹配状态'] = '无匹配'
                            result['风险评分'] = '无匹配'
                            result['匹配记录数'] = 0
                except Exception as e:
                    logger.error(f"查询风险评分时出错: {e}")
                    result['匹配状态'] = '查询错误'
                    result['风险评分'] = '无匹配'
                    result['匹配记录数'] = 0
            else:
                # 没有查询条件
                result['匹配状态'] = '无查询条件'
                result['风险评分'] = '无匹配'
                result['匹配记录数'] = 0
            
            results.append(result)
            
            # 打印每个订单的评分结果和加费率
            surcharge_info = f", 加费率: {result.get('加费率', '无')}%" if '加费率' in result else ""
            logger.info(f"订单 {order_id} 的评分结果: {result['匹配状态']}, 风险评分: {result['风险评分']}{surcharge_info}")
        
        # 统计匹配结果
        match_stats = {}
        for result in results:
            status = result['匹配状态']
            match_stats[status] = match_stats.get(status, 0) + 1
        
        logger.info("匹配统计结果:")
        for status, count in match_stats.items():
            logger.info(f"  {status}: {count}条 ({count/len(results)*100:.2f}%)")
        
        return results

def parse_args():
    """
    解析命令行参数
    
    Returns:
        解析后的参数
    """
    parser = argparse.ArgumentParser(description='风险评分应用')
    parser.add_argument('--json-file', type=str, help='JSON文件路径')
    parser.add_argument('--generate-data', action='store_true', help='生成样本数据')
    parser.add_argument('--num-samples', type=int, default=100, help='样本数量')
    parser.add_argument('--input-file', type=str, help='输入文件路径')
    parser.add_argument('--output-file', type=str, help='输出文件路径')
    parser.add_argument('--exact-match', action='store_true', help='使用固定路径进行精确匹配')
    
    return parser.parse_args()

def main():
    # 解析命令行参数
    args = parse_args()
    
    # 如果指定了精确匹配模式
    if args.exact_match:
        logger.info("使用固定路径进行精确匹配")
        app = ExactMatchApplication()
        results = app.match_records()
        logger.info(f"精确匹配完成，共处理{len(results)}条记录")
        return
    
    # 设置JSON文件路径
    if args.json_file:
        json_file_path = args.json_file
    else:
        json_file_path = os.path.join('output', 'json_export', '新单续保+伤残+行业1级+省份+行业2级分析_20250604_171753.json')
    
    json_file_path = os.path.abspath(json_file_path)
    
    # 检查文件是否存在
    if not os.path.exists(json_file_path):
        logger.error(f"文件不存在: {json_file_path}")
        return
    
    # 初始化风险评分查询类
    risk_lookup = RiskScoreLookup(json_file_path)
    
    # 如果需要生成样本数据
    if args.generate_data:
        # 设置输出文件路径
        if args.output_file:
            output_file = args.output_file
        else:
            output_file = os.path.join('output', 'sample_data.csv')
        
        output_file = os.path.abspath(output_file)
        
        # 生成样本数据
        data_generator = DataGenerator(risk_lookup)
        samples = data_generator.generate_sample_data(args.num_samples)
        data_generator.save_to_csv(samples, output_file)
        
        logger.info(f"样本数据已生成并保存到{output_file}")
        return
    
    # 如果需要处理数据
    if args.input_file:
        # 设置输入文件路径
        input_file = os.path.abspath(args.input_file)
        
        # 设置输出文件路径
        if args.output_file:
            output_file = args.output_file
        else:
            output_file = os.path.join('output', 'processed_data.csv')
        
        output_file = os.path.abspath(output_file)
        
        # 运行风险评分应用
        app = RiskScoreApplication(risk_lookup)
        app.run(input_file, output_file)
        
        logger.info(f"数据处理完成，结果已保存到{output_file}")
    else:
        # 如果没有指定输入文件，则生成样本数据并处理
        logger.info("未指定输入文件，将生成样本数据并处理")
        
        # 生成样本数据
        sample_file = os.path.join('output', 'sample_data.csv')
        sample_file = os.path.abspath(sample_file)
        
        data_generator = DataGenerator(risk_lookup)
        samples = data_generator.generate_sample_data(args.num_samples)
        data_generator.save_to_csv(samples, sample_file)
        
        # 设置输出文件路径
        if args.output_file:
            output_file = args.output_file
        else:
            output_file = os.path.join('output', 'processed_data.csv')
        
        output_file = os.path.abspath(output_file)
        
        # 运行风险评分应用
        app = RiskScoreApplication(risk_lookup)
        app.run(sample_file, output_file)
        
        logger.info(f"数据处理完成，结果已保存到{output_file}")

if __name__ == "__main__":
    logger.info("=== 开始风险评分应用 ===")
    # 默认使用精确匹配模式
    app = ExactMatchApplication()
    results = app.match_records()
    logger.info(f"精确匹配完成，共处理{len(results)}条记录")
    logger.info("=== 风险评分应用完成 ===")