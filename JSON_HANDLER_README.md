# JSON文件上传和处理接口使用指南

## 概述

`json_file_handler.py` 模块提供了完整的JSON文件上传和处理功能，专门用于处理不规则截面分析的配置文件。该模块包含文件验证、预处理、错误处理等功能。

## 主要功能

### 1. JSON文件验证
- 结构完整性检查
- 数据类型验证
- 材料参数有效性验证
- 几何参数合理性检查

### 2. 文件预处理
- 自动计算钢筋面积
- 添加材料计算参数
- 几何数据验证和优化

### 3. 错误处理
- 详细的错误信息
- 文件权限检查
- JSON格式验证
- 文件大小限制

## 类和方法

### JSONFileHandler 类

#### 方法

- `validate_json_structure(data)`: 验证JSON数据结构
- `load_json_file(file_path)`: 加载和验证JSON文件
- `preprocess_config_data(data)`: 预处理配置数据
- `save_processed_config(data, output_path)`: 保存处理后的配置
- `get_config_summary(data)`: 获取配置摘要

### FileUploadProcessor 类

#### 初始化参数

- `upload_dir`: 上传文件目录（默认: "uploads"）
- `processed_dir`: 处理后文件目录（默认: "processed"）

#### 方法

- `process_uploaded_file(file_path)`: 处理上传的文件
- `get_supported_formats()`: 获取支持的文件格式信息
- `cleanup_old_files(days)`: 清理旧文件

## 使用示例

### 基本使用

```python
from json_file_handler import JSONFileHandler, FileUploadProcessor

# 创建处理器
handler = JSONFileHandler()
processor = FileUploadProcessor()

# 处理上传的文件
result = processor.process_uploaded_file("path/to/config.json")

if result["success"]:
    print("文件处理成功")
    print(f"摘要: {result['summary']}")
    print(f"处理后文件: {result['processed_file']}")
else:
    print(f"处理失败: {result['message']}")
```

### 单独验证JSON结构

```python
import json

# 加载JSON数据
with open("config.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

# 验证结构
is_valid, message = handler.validate_json_structure(data)
print(f"验证结果: {is_valid} - {message}")
```

### 预处理配置数据

```python
# 预处理数据
processed_data = handler.preprocess_config_data(raw_data)

# 数据现在包含了计算字段
print(processed_data["materials"]["calculated_params"])
print(processed_data["reinforcement"]["calculated_areas"])
```

## JSON文件格式要求

### 必需字段

```json
{
  "materials": {
    "concrete_type": "C30|C40|C45|C50|C55|C60",
    "steel_type": "HRB400|HRB500|HPB300"
  },
  "geometry": {
    "height": 600,
    "contour_points": [
      {
        "y": 0,
        "half_width": 150
      }
    ]
  },
  "reinforcement": {
    "cover_thickness": 30,
    "layers": {
      "top": {
        "count": 3,
        "diameter": 20
      },
      "middle": {
        "count": 2,
        "diameter": 18
      },
      "bottom": {
        "count": 4,
        "diameter": 22
      }
    }
  },
  "analysis": {
    "target_axial_force": 300,
    "curvature_range": {
      "start": 0.0,
      "end": 0.0015,
      "steps": 150
    }
  }
}
```

### 可选字段

```json
{
  "section_name": "截面名称",
  "description": "截面描述",
  "version": "1.0",
  "reinforcement": {
    "layers": {
      "top|middle|bottom": {
        "cover_override": 40
      }
    }
  },
  "analysis": {
    "single_calculation": {
      "kappa": 0.0005,
      "epsilon0": 0.0001
    }
  }
}
```

## 命令行使用

```bash
# 处理单个文件
python json_file_handler.py config.json

# 指定输出路径
python json_file_handler.py config.json --output processed_config.json

# 详细输出
python json_file_handler.py config.json --verbose
```

## 测试

运行测试脚本验证功能：

```bash
python test_json_handler.py
```

## 错误处理

模块提供了详细的错误信息：

- 文件不存在
- JSON格式错误
- 结构验证失败
- 权限问题
- 文件过大

## 文件大小限制

- 最大文件大小：10MB
- 支持编码：UTF-8
- 文件类型：仅限 .json

## 目录结构

```
project/
├── json_file_handler.py      # 主处理模块
├── test_json_handler.py      # 测试脚本
├── uploads/                  # 上传文件目录（自动创建）
├── processed/                # 处理后文件目录（自动创建）
└── custom_irregular_config.json  # 示例配置文件
```

## 集成到GUI

该模块已经集成到GUI中，当用户选择JSON文件时会自动调用处理功能：

```python
# 在GUI中的使用
if params["section_type"] == "irregular":
    config_file = params.get("config_file")
    if config_file:
        # 使用FileUploadProcessor处理文件
        processor = FileUploadProcessor()
        result = processor.process_uploaded_file(config_file)

        if result["success"]:
            # 处理成功，使用result["data"]进行分析
            results = analyze_irregular_section_from_config_data(result["data"])
        else:
            # 处理失败，显示错误信息
            QMessageBox.critical(self, "文件处理错误", result["message"])
```

## 注意事项

1. 确保Python环境已安装必要的依赖包
2. 文件路径使用正斜杠或正确转义反斜杠
3. JSON文件必须是有效的UTF-8编码
4. 定期清理上传和处理目录中的旧文件

## 扩展功能

模块设计支持扩展：

- 添加新的材料类型验证
- 实现自定义验证规则
- 支持批量文件处理
- 添加文件压缩/解压功能