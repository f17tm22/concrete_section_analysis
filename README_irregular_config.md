# 不规则对称截面分析配置文件说明

## 概述

本配置文件系统允许用户通过JSON格式文件定义不规则对称截面的各项参数，进行混凝土截面分析。

## 文件格式

配置文件使用JSON格式，包含以下主要部分：

### 1. 基本信息
```json
{
  "description": "配置文件描述",
  "version": "1.0",
  "section_name": "截面名称"
}
```

### 2. 材料参数
```json
"materials": {
  "concrete_type": "C45",  // 混凝土等级 (C30, C35, C40, C45, C50, C55, C60)
  "steel_type": "HRB400"   // 钢筋等级 (HRB400, HRB500, HPB300)
}
```

### 3. 几何参数
```json
"geometry": {
  "height": 800,  // 截面总高度 (mm)
  "contour_points": [
    {"y": -400, "half_width": 300, "description": "底部最宽处"},
    {"y": -300, "half_width": 280, "description": "底部向上收缩"},
    // ... 更多轮廓点
  ]
}
```

**轮廓点说明：**
- `y`: 垂直坐标 (mm)，截面中心为0
- `half_width`: 该高度处的半宽度 (mm)
- `description`: 可选的描述信息

### 4. 钢筋配置
```json
"reinforcement": {
  "cover_thickness": 40,  // 默认保护层厚度 (mm)
  "layers": {
    "top": {
      "count": 2,        // 钢筋数量
      "diameter": 18,    // 钢筋直径 (mm)
      "cover_override": null  // 覆盖默认保护层，为null则使用默认值
    },
    "middle": {
      "count": 2,
      "diameter": 20,
      "cover_override": 50  // 使用自定义保护层
    },
    "bottom": {
      "count": 3,
      "diameter": 25,
      "cover_override": null
    }
  }
}
```

### 5. 分析参数
```json
"analysis": {
  "target_axial_force": 500,  // 目标轴力 (kN)
  "curvature_range": {
    "start": 0.0,     // 起始曲率 (1/m)
    "end": 0.0022,    // 结束曲率 (1/m)
    "steps": 200      // 分析步数
  },
  "single_calculation": {
    "kappa": 0.0007,     // 单工况曲率 (1/m)
    "epsilon0": 0.00015   // 单工况轴向应变
  }
}
```

## 使用方法

### 1. 创建配置文件
复制 `irregular_section_config.json` 并根据需要修改参数。

### 2. 命令行运行
```bash
# 使用默认配置文件
python irregular_section.py

# 使用自定义配置文件
python irregular_section.py my_section_config.json
```

### 3. 在GUI中使用
配置文件路径可以在GUI中指定，用于加载自定义截面参数。

## 示例配置文件

项目中提供了 `irregular_section_config.json` 作为示例，包含了一个典型的不规则对称截面配置。

## 输出结果

分析结果将保存为CSV文件在 `results/` 目录中，包含：
- 曲率-弯矩关系
- 混凝土应变分布
- 分析过程中的各种参数

## 注意事项

1. 轮廓点应按y坐标从负到正排序
2. 至少需要定义顶部(top)、中部(middle)、底部(bottom)三层钢筋
3. 保护层厚度应根据规范要求设置
4. 分析参数可根据具体需求调整

## 扩展功能

配置文件系统支持：
- 自定义截面名称和描述
- 灵活的钢筋配置
- 可调节的分析参数
- 版本控制