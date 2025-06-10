"""
风险评分加费自动计算模块 (FK Auto)

功能：
    根据风险评分计算保险加费率，并提供基于地域和行业分类的多层级条件树查询功能。
    支持非线性加费计算，使用指数函数模型：y = 1000 * (e^(-0.046x) - 0.01) * weight。
    提供权重调整功能，可灵活控制加费力度（权重>1.0加大加费，权重<1.0减小加费）。
    支持多层级条件树查询，精确匹配不同地域和行业的加费系数。
    实现了加费计算验证功能，确保计算结果符合预期标准。
    
运行逻辑：
    1. 从配置文件加载加费计算权重（默认为0.5）
    2. 使用指数函数计算非线性加费率：y = 1000 * (e^(-0.046x) - 0.01) * weight
    3. 构建多层级条件树（省份-城市-行业门类-行业大类-行业中类）
    4. 根据输入条件在条件树中查找最长匹配路径，返回对应加费率
    5. 提供验证功能，确保加费计算符合预期标准
    
使用方法：
    1. 导入模块：import fkauto
    2. 直接计算加费率：fkauto.calculate_nonlinear_surcharge(score, weight=None)
    3. 构建条件树：fkauto.build_condition_tree(data_lines, weight=None)
    4. 查询加费率：fkauto.calculate_surcharge(province, city, menlei, dalei, zhonglei)
    5. 验证加费计算：fkauto.verify_surcharge_calculation()
    
依赖：
    - os: 文件路径操作
    - yaml: 读取配置文件
    - math: 指数函数计算
"""

import os
import yaml

# 读取配置文件
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'risk_assessment.yml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

# 获取加费计算权重
def get_surcharge_weight():
    config = load_config()
    return config.get('surcharge_calculation', {}).get('weight', 1.0)

class TreeNode:
    def __init__(self):
        self.children = {}
        self.score = None
        self.surcharge = None

def calculate_nonlinear_surcharge(score, weight=None):
    """
    使用指数函数计算加费率
    y = 1000 * (e^(-0.046x) - 0.01)
    
    参数:
        score: 风险评分(0-100)
        weight: 权重系数，如果为None则从配置文件读取
            - 权重>1.0时：加大加费力度
            - 权重<1.0时：减小加费力度
    
    返回:
        加费率(百分比)
    """
    import math
    
    # 如果未指定权重，则从配置文件读取
    if weight is None:
        weight = get_surcharge_weight()
    
    # 处理边界情况
    if score >= 100:
        return 0.0
    elif score <= 0:
        return 1000.0 * weight
    
    # 使用指数函数计算基础加费率
    # y = 1000 * (e^(-0.046x) - 0.01)
    base_surcharge = 1000 * (math.exp(-0.046 * score) - 0.01)
    
    # 处理接近100分的情况，确保100分时加费为0
    if score > 99.9:
        base_surcharge = 0.0
    
    # 应用权重系数
    weighted_surcharge = base_surcharge * weight
    
    # 确保加费率不超过上限且不小于0
    if weighted_surcharge > 1000.0 * weight:
        weighted_surcharge = 1000.0 * weight
    elif weighted_surcharge < 0:
        weighted_surcharge = 0.0
    
    return round(weighted_surcharge, 1)

def build_condition_tree(data_lines, weight=None):
    """
    根据数据行构建条件树
    
    参数:
        data_lines: 数据行列表
        weight: 加费计算的权重系数，如果为None则从配置文件读取
    """
    # 如果未指定权重，则从配置文件读取
    if weight is None:
        weight = get_surcharge_weight()
    for line in data_lines:
        parts = line.strip().split('\t')
        if len(parts) < 10:
            continue
        
        # 解析省份、城市、门类、大类、中类
        province = parts[0].strip()
        city = parts[1].strip()
        menlei = parts[2].split('|')[0].strip() if parts[2].strip() else ''
        dalei = parts[3].split('|')[0].strip() if parts[3].strip() else ''
        zhonglei = parts[4].split('|')[0].strip() if parts[4].strip() else ''
        score = float(parts[-1])  # 最后一列为评分
        
        # 构建条件路径
        path = []
        if province:
            path.append(province)
        else:
            continue
        if city:
            path.append(city)
        else:
            continue
        for code in [menlei, dalei, zhonglei]:
            if code:
                path.append(code)
            else:
                break  # 后续层级为空则停止
        
        # 插入节点到条件树
        current_node = root
        for code in path:
            if code not in current_node.children:
                current_node.children[code] = TreeNode()
            current_node = current_node.children[code]
        
        # 设置叶节点的评分和加费系数
        current_node.score = score
        current_node.surcharge = calculate_nonlinear_surcharge(score, weight)

def calculate_surcharge(province, city, menlei, dalei, zhonglei):
    # 提取各层级的代码
    query_path = [province.strip(), city.strip()]
    menlei_code = menlei.split('|')[0].strip() if menlei.strip() else ''
    dalei_code = dalei.split('|')[0].strip() if dalei.strip() else ''
    zhonglei_code = zhonglei.split('|')[0].strip() if zhonglei.strip() else ''
    
    # 构建查询路径
    for code in [menlei_code, dalei_code, zhonglei_code]:
        if code:
            query_path.append(code)
        else:
            break
    
    # 在树中查找最长匹配路径
    current_node = root
    best_surcharge = 0.0  # 默认加费0%
    for code in query_path:
        if code in current_node.children:
            current_node = current_node.children[code]
            if current_node.surcharge is not None:
                best_surcharge = current_node.surcharge
        else:
            break  # 无匹配子节点，终止搜索
    return best_surcharge

# 初始化根节点
root = TreeNode()

# 示例数据（假设数据已读取到data_lines中）
data_lines = [
    "江苏省\t无锡市\tN|水利、环境和公共设施管理业\tN078|公共设施管理业\tN0781|市政设施管理\t0\t19034.4\t0\t14\t0\t0\t0\t3.78563E-05\t0\t100",
    "江苏省\t泰州市\tC|制造业\tC033|金属制品业\tC0331|结构性金属制品制造\t0\t19034.4\t0\t14\t0\t0\t0\t3.78563E-05\t0\t20",
    # ... 其他数据行
]

# 构建条件树（使用默认权重1.0）
build_condition_tree(data_lines)

# 示例查询
province = '江苏省'
city = '泰州市'
menlei = 'C|制造业'
dalei = 'C033|金属制品业'
zhonglei = 'C0331|结构性金属制品制造'

surcharge = calculate_surcharge(province, city, menlei, dalei, zhonglei)
print(f"加费系数: {surcharge}%")

# 验证加费计算是否符合要求的标准
def verify_surcharge_calculation():
    import math
    
    # 测试不同评分下的加费率
    test_scores = [0, 20, 40, 60, 100]
    weights = [0.8, 1.0, 1.2]
    
    # 获取配置文件中的权重
    config_weight = get_surcharge_weight()
    
    print("\n验证加费计算是否符合要求的标准:")
    print("使用公式: y = 1000 * (e^(-0.046x) - 0.01)")
    print(f"\n配置文件中的权重: {config_weight}")
    print("\n默认权重下的加费率(从配置文件读取):")
    print("-" * 40)
    print(f"{'评分':<10}{'加费率':<15}{'期望值':<15}{'是否符合':<10}")
    print("-" * 40)
    
    for score in test_scores:
        # 使用公式计算期望值
        if score >= 100:
            expected = 0.0
        elif score <= 0:
            expected = 1000.0 * config_weight
        else:
            expected = 1000 * (math.exp(-0.046 * score) - 0.01) * config_weight
            if expected < 0:
                expected = 0.0
        expected = round(expected, 1)
        
        # 使用函数计算实际值（从配置文件读取权重）
        actual = calculate_nonlinear_surcharge(score)
        
        # 检查是否符合期望
        is_match = abs(actual - expected) < 0.1
        
        print(f"{score:<10}{actual:<15.1f}{expected:<15.1f}{'✓' if is_match else '✗':<10}")
    
    print("\n不同权重下的加费率(显式指定权重):")
    print("-" * 50)
    print(f"{'评分':<10}{'权重':<10}{'加费率':<15}{'最大加费':<15}")
    print("-" * 50)
    
    for weight in weights:
        for score in [0, 20, 100]:
            actual = calculate_nonlinear_surcharge(score, weight)
            max_surcharge = 1000.0 * weight
            print(f"{score:<10}{weight:<10.1f}{actual:<15.1f}{max_surcharge:<15.1f}")

# 运行验证
if __name__ == "__main__":
    # 打印配置文件中的权重
    config_weight = get_surcharge_weight()
    print(f"配置文件中的权重: {config_weight}")
    
    # 测试使用配置文件中的权重计算加费率
    test_score = 50
    surcharge = calculate_nonlinear_surcharge(test_score)
    print(f"使用配置文件权重计算评分{test_score}的加费率: {surcharge}%")
    
    # 运行完整验证
    verify_surcharge_calculation()