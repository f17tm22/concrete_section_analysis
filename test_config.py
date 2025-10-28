#!/usr/bin/env python3
"""
不规则对称截面配置文件测试脚本
演示如何使用JSON配置文件进行截面分析
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from irregular_section import analyze_irregular_section_from_config

def test_config_files():
    """测试多个配置文件"""
    config_files = [
        "irregular_section_config.json"
    ]

    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"\n{'='*60}")
            print(f"测试配置文件: {config_file}")
            print(f"{'='*60}")

            try:
                results = analyze_irregular_section_from_config(config_file)

                if "error" in results:
                    print(f"❌ 分析失败: {results['error']}")
                else:
                    print("✅ 分析成功!")
                    print(f"截面名称: {results['config_info']['section_name']}")
                    print(f"最大弯矩: {results['full_analysis']['max_moment']:.2f} kN·m")
                    print(f"破坏模式: {results['full_analysis']['failure_mode']}")

            except Exception as e:
                print(f"❌ 处理配置文件时出错: {e}")
        else:
            print(f"⚠️  配置文件不存在: {config_file}")

def create_custom_config_example():
    """创建自定义配置文件的示例"""
    custom_config = {
        "description": "自定义不规则截面示例",
        "version": "1.0",
        "section_name": "自定义截面",

        "materials": {
            "concrete_type": "C40",
            "steel_type": "HRB500"
        },

        "geometry": {
            "height": 600,
            "contour_points": [
                {"y": -300, "half_width": 200, "description": "底部"},
                {"y": -150, "half_width": 180, "description": "中下部"},
                {"y": 0, "half_width": 150, "description": "中部"},
                {"y": 150, "half_width": 180, "description": "中上部"},
                {"y": 300, "half_width": 200, "description": "顶部"}
            ]
        },

        "reinforcement": {
            "cover_thickness": 30,
            "layers": {
                "top": {
                    "count": 3,
                    "diameter": 20,
                    "cover_override": None
                },
                "middle": {
                    "count": 2,
                    "diameter": 18,
                    "cover_override": 40
                },
                "bottom": {
                    "count": 4,
                    "diameter": 22,
                    "cover_override": None
                }
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

    import json
    with open("custom_irregular_config.json", 'w', encoding='utf-8') as f:
        json.dump(custom_config, f, indent=2, ensure_ascii=False)

    print("已创建自定义配置文件: custom_irregular_config.json")

if __name__ == "__main__":
    print("不规则对称截面配置文件测试")
    print("=" * 40)

    # 测试现有配置文件
    test_config_files()

    # 创建自定义配置示例
    print(f"\n{'='*60}")
    print("创建自定义配置文件示例")
    print(f"{'='*60}")
    create_custom_config_example()

    print("\n测试完成！")
    print("您可以：")
    print("1. 修改 irregular_section_config.json 来自定义参数")
    print("2. 使用 custom_irregular_config.json 作为新配置的模板")
    print("3. 在GUI中集成配置文件选择功能")