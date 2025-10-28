# 钢筋混凝土截面分析GUI - 文件上传功能使用说明

## 功能概述

GUI界面现在支持上传JSON配置文件来分析不规则对称截面。用户可以选择预定义的配置文件或自定义配置文件来进行截面分析。

## 使用步骤

### 1. 启动GUI
```bash
cd concrete_section_analysis
python gui_irregular.py
```

### 2. 选择截面类型
- 在"截面参数"组中，将"截面类型"从"矩形截面"切换到"不规则对称截面"
- 切换后，"JSON配置文件"控件将被启用

### 3. 选择配置文件
- 点击"浏览..."按钮打开文件选择对话框
- 选择一个JSON格式的配置文件（扩展名.json）
- 或者直接在文本框中输入配置文件路径

### 4. 配置分析参数
- 设置目标轴力（kN）
- 设置分析步数
- 材料参数会自动从配置文件中读取

### 5. 开始分析
- 点击"开始分析"按钮
- 分析结果将在右侧面板中显示，包括：
  - 结果摘要
  - 弯矩-曲率曲线
  - 应变发展曲线
  - 中和轴应变曲线

## JSON配置文件格式

配置文件应包含以下结构：

```json
{
  "description": "截面描述",
  "version": "1.0",
  "section_name": "截面名称",
  "materials": {
    "concrete_type": "C40",
    "steel_type": "HRB500"
  },
  "geometry": {
    "height": 600,
    "contour_points": [
      {"y": -300, "half_width": 200, "description": "底部"},
      {"y": 0, "half_width": 150, "description": "中部"},
      {"y": 300, "half_width": 200, "description": "顶部"}
    ]
  },
  "reinforcement": {
    "cover_thickness": 30,
    "layers": {
      "top": {"count": 3, "diameter": 20, "cover_override": null},
      "middle": {"count": 2, "diameter": 18, "cover_override": 40},
      "bottom": {"count": 4, "diameter": 22, "cover_override": null}
    }
  },
  "analysis": {
    "target_axial_force": 300,
    "curvature_range": {
      "start": 0.0,
      "end": 0.0015,
      "steps": 150
    },
    "single_calculation": {
      "kappa": 0.0005,
      "epsilon0": 0.0001
    }
  }
}
```

## 示例配置文件

项目中包含以下示例配置文件：
- `custom_irregular_config.json` - 自定义不规则截面示例
- `irregular_section_config.json` - 默认不规则截面配置

## 注意事项

1. JSON文件必须是有效的JSON格式
2. 路径中的反斜杠在Windows系统上需要转义或使用正斜杠
3. 配置文件中的材料类型必须是系统支持的类型
4. 几何参数的单位为毫米，力参数的单位为千牛

## 故障排除

- 如果文件选择对话框无法打开，检查文件权限
- 如果分析失败，检查JSON文件格式和参数有效性
- 如果出现字体警告，这是正常的，不影响功能