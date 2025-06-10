import pandas as pd
import json
from collections import OrderedDict

# 读取 CSV 文件（尝试不同编码）
csv_file = "国民行业分类_利宝.csv"  # 你的 CSV 文件路径
try:
    df = pd.read_csv(csv_file, encoding="utf-8")  # 如果 utf-8 失败，尝试 gbk
except UnicodeDecodeError:
    df = pd.read_csv(csv_file, encoding="gbk")

# 存储所有节点，使用 OrderedDict 保持顺序
nodes = OrderedDict()
root = []

# 第一步：创建所有节点
for _, row in df.iterrows():
    code = row["CODECODE"]
    name = row["国民经济行业类型"]
    level = row["等级"]
    
    node = OrderedDict({
        "name": name,
        "code": code,
        "level": level,
        "children": []
    })
    
    nodes[code] = node

# 第二步：建立父子关系
# 创建一个按层级分组的字典，用于查找父级
level_groups = {}
for code, node in nodes.items():
    level = node["level"]
    if level not in level_groups:
        level_groups[level] = []
    level_groups[level].append((code, node))

# 为每个节点找到其父级
for code, node in nodes.items():
    level = node["level"]
    
    if level == 1:
        continue  # 1级行业没有父级
    
    # 查找父级：在上一级中找到代码是当前代码前缀的节点
    parent_level = level - 1
    if parent_level in level_groups:
        for parent_code, parent_node in level_groups[parent_level]:
            # 检查当前代码是否以父级代码开头
            if code.startswith(parent_code):
                parent_node["children"].append(node)
                break

# 第三步：将没有父级的节点添加到root
for code, node in nodes.items():
    level = node["level"]
    if level == 1:  # 只有1级行业才应该在root级别
        root.append(node)

# 转换为 JSON
json_output = json.dumps(root, ensure_ascii=False, indent=4)

# 保存 JSON 文件
json_file = "国民行业分类_利宝.json"
with open(json_file, "w", encoding="utf-8") as f:
    f.write(json_output)

print(f"转换完成，JSON 文件已保存为 {json_file}")
