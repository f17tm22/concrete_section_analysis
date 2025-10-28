import json
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(__file__))
from analyzer_ver1 import RCSectionAnalyzer

def load_irregular_section_config(config_file):
    """从JSON配置文件加载不规则对称截面参数"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"配置文件 {config_file} 不存在")
    except json.JSONDecodeError as e:
        raise ValueError(f"配置文件格式错误: {e}")

def analyze_irregular_section_from_config(config_file):
    """从配置文件分析不规则对称截面"""
    # 1. 加载配置文件
    config = load_irregular_section_config(config_file)

    # 2. 初始化分析器
    analyzer = RCSectionAnalyzer()

    # 3. 设置材料
    materials = config['materials']
    analyzer.set_materials(materials['concrete_type'], materials['steel_type'])

    # 4. 解析几何参数
    geometry = config['geometry']
    height = geometry['height']

    # 转换轮廓点格式
    contour_points = []
    for point in geometry['contour_points']:
        contour_points.append((point['y'], point['half_width']))

    # 5. 计算钢筋面积
    reinforcement = config['reinforcement']
    cover = reinforcement['cover_thickness']

    steel_areas = {}
    for layer_name, layer_info in reinforcement['layers'].items():
        count = layer_info['count']
        diameter = layer_info['diameter']
        area = count * np.pi * (diameter / 2) ** 2
        steel_areas[layer_name] = area

    # 6. 设置截面
    analyzer.set_section(
        contour_points=contour_points,
        reinforcement={
            "top": {
                "area": steel_areas['top'],
                "depth": cover if reinforcement['layers']['top'].get('cover_override') is None
                        else reinforcement['layers']['top'].get('cover_override')
            },
            "middle": {
                "area": steel_areas['middle'],
                "depth": cover if reinforcement['layers']['middle'].get('cover_override') is None
                        else reinforcement['layers']['middle'].get('cover_override')
            },
            "bottom": {
                "area": steel_areas['bottom'],
                "depth": cover if reinforcement['layers']['bottom'].get('cover_override') is None
                        else reinforcement['layers']['bottom'].get('cover_override')
            }
        }
    )

    # 7. 执行分析
    analysis_config = config['analysis']

    # 单工况计算
    single_calc = analysis_config.get('single_calculation', {})
    kappa = single_calc.get('kappa', 0.0007)
    epsilon0 = single_calc.get('epsilon0', 0.00015)
    N, M = analyzer.calculate_section_for_epsilon(kappa, epsilon0)

    # 平衡状态求解
    N_target = analysis_config['target_axial_force'] * 1000  # 转换为N
    epsilon0_sol, N_sol, M_sol = analyzer.find_balance_conditions(kappa, N_target)

    # 全过程分析
    curvature_range = analysis_config['curvature_range']
    results = analyzer.analyze_full_range(
        N_target=N_target,
        kappa_start=curvature_range['start'],
        kappa_end=curvature_range['end'],
        n_steps=curvature_range['steps']
    )

    if "error" in results:
        return {"error": results["error"]}

    # 8. 返回结果字典
    max_moment = max(results["moments"])

    # 构建钢筋信息
    reinforcement_info = {}
    for layer_name, layer_info in reinforcement['layers'].items():
        # use .get() to allow missing 'cover_override' in JSON without KeyError
        depth = (cover if layer_info.get('cover_override') is None else layer_info.get('cover_override'))
        reinforcement_info[layer_name] = {
            "count": layer_info['count'],
            "diameter": layer_info['diameter'],
            "area": steel_areas[layer_name],
            "depth": depth
        }

    return {
        "config_info": {
            "config_file": config_file,
            "section_name": config.get('section_name', '未命名截面'),
            "description": config.get('description', ''),
            "version": config.get('version', '1.0')
        },
        "section_info": {
            "type": "不规则对称截面",
            "height": height,
            "contour": contour_points,
            "reinforcement": reinforcement_info
        },
        "materials": {
            "concrete": materials['concrete_type'],
            "steel": materials['steel_type'],
            "f_cd": analyzer.f_cd,
            "f_yd": analyzer.f_yd
        },
        "single_calculation": {
            "kappa": kappa,
            "epsilon0": epsilon0,
            "N": N / 1000,  # kN
            "M": M / 1e6    # kN·m
        },
        "balance_calculation": {
            "N_target": N_target / 1000,  # kN
            "epsilon0_sol": epsilon0_sol,
            "N_sol": N_sol / 1000,  # kN
            "M_sol": M_sol / 1e6    # kN·m
        },
        "full_analysis": {
            "n_steps": len(results['kappas']),
            "max_moment": max_moment / 1e6,  # kN·m
            "failure_mode": results['failure_mode'],
            "final_curvature": results['kappas'][-1],
            "kappas": results['kappas'],
            "moments": [m / 1e6 for m in results['moments']],  # kN·m
            "epsilons0": results['epsilons0'],
            "max_eps_concrete": results['max_eps_concrete'],
            "min_eps_concrete": results['min_eps_concrete']
        }
    }

def test_irregular_section_from_config(config_file="irregular_section_config.json"):
    """从配置文件测试不规则对称截面分析"""
    try:
        results = analyze_irregular_section_from_config(config_file)
    except Exception as e:
        print(f"分析失败: {e}")
        return

    if "error" in results:
        print(f"分析出错: {results['error']}")
        return

    config_info = results['config_info']
    print(f"=== 从配置文件分析不规则对称截面 ===")
    print(f"配置文件: {config_info['config_file']}")
    print(f"截面名称: {config_info['section_name']}")
    print(f"描述: {config_info['description']}")
    print(f"版本: {config_info['version']}\n")

    print("=== 材料信息 ===")
    materials = results['materials']
    print(f"混凝土类型: {materials['concrete']}, 钢筋类型: {materials['steel']}")
    print(f"混凝土抗压强度设计值: {materials['f_cd']:.2f} MPa")
    print(f"钢筋屈服强度设计值: {materials['f_yd']:.2f} MPa\n")

    print("=== 截面参数 ===")
    section_info = results['section_info']
    print(f"截面类型: {section_info['type']}")
    print(f"截面总高: {section_info['height']} mm")
    print(f"轮廓点数量: {len(section_info['contour'])}")

    # 显示钢筋配置
    reinforcement = section_info['reinforcement']
    for layer_name, layer_info in reinforcement.items():
        layer_names = {"top": "顶部", "middle": "中部", "bottom": "底部"}
        print(f"{layer_names[layer_name]}钢筋：{layer_info['count']}Φ{layer_info['diameter']}，"
              f"面积: {layer_info['area']:.2f} mm²，保护层: {layer_info['depth']} mm")
    print()

    single = results['single_calculation']
    print("=== 单工况计算结果 ===")
    print(f"曲率 {single['kappa']} 下的轴力: {single['N']:.2f} kN")
    print(f"曲率 {single['kappa']} 下的弯矩: {single['M']:.2f} kN·m\n")

    balance = results['balance_calculation']
    print("=== 平衡状态求解 ===")
    print(f"目标轴力 {balance['N_target']:.0f} kN 对应的轴向应变: {balance['epsilon0_sol']:.6f}")
    print(f"平衡轴力: {balance['N_sol']:.2f} kN")
    print(f"平衡弯矩: {balance['M_sol']:.2f} kN·m\n")

    full = results['full_analysis']
    print("=== 全过程分析结果 ===")
    print(f"分析步数: {full['n_steps']}")
    print(f"最大弯矩: {full['max_moment']:.2f} kN·m")
    print(f"破坏模式: {full['failure_mode']}")
    print(f"最终曲率: {full['final_curvature']:.6f} 1/m")

    # 保存结果到CSV
    output_filename = f"results/{config_info['section_name'].replace(' ', '_')}_results.csv"
    np.savetxt(
        output_filename,
        np.column_stack([
            full["kappas"],
            full["moments"],
            full["max_eps_concrete"],
            full["min_eps_concrete"]
        ]),
        header="曲率,弯矩(kN·m),最大混凝土应变,最小混凝土应变",
        delimiter=",",
        fmt="%.6f,%.4f,%.6f,%.6f"
    )
    print(f"\n结果已保存到 {output_filename}")

def analyze_irregular_symmetric_section():
    """分析不规则对称截面并返回结果字典"""
    # 1. 初始化分析器
    analyzer = RCSectionAnalyzer()
    
    # 2. 设置材料（C45混凝土 + HRB400钢筋）
    analyzer.set_materials("C45", "HRB400")

    # 3. 定义不规则对称截面轮廓点（关于y=0对称）
    irregular_contour = [
        (-400, 300),   # 底部最宽处：y=-400mm，半宽300mm
        (-300, 280),   # 底部向上收缩：y=-300mm，半宽280mm
        (-200, 200),   # 腰部收窄：y=-200mm，半宽200mm
        (-100, 180),   # 继续收窄：y=-100mm，半宽180mm
        (0, 150),      # 最窄处：y=0mm，半宽150mm
        (100, 180),    # 上半部分对称：y=100mm，半宽180mm
        (200, 200),    # 上半部分对称：y=200mm，半宽200mm
        (300, 220),    # 上半部分略宽：y=300mm，半宽220mm
        (400, 180)     # 顶部收窄：y=400mm，半宽180mm
    ]
    
    # 钢筋配置：根据截面变化布置多排钢筋
    cover = 40  # 保护层厚度
    # 底部钢筋：y=-400+40=-360mm处，3Φ25
    bottom_area = 3 * np.pi * (25/2)**2
    # 腰部钢筋：y=-200+50=-150mm处（避开最窄点），2Φ20
    middle_area = 2 * np.pi * (20/2)**2
    # 顶部钢筋：y=400-40=360mm处，2Φ18
    top_area = 2 * np.pi * (18/2)**2
    
    # 调用set_section设置截面
    analyzer.set_section(
        contour_points=irregular_contour,
        reinforcement={
            "top": {"area": top_area, "depth": cover},
            "middle": {"area": middle_area, "depth": 50},  # 腰部保护层稍大
            "bottom": {"area": bottom_area, "depth": cover}
        }
    )
    
    # 4. 单工况计算（中等曲率）
    kappa = 0.0007
    epsilon0 = 0.00015
    N, M = analyzer.calculate_section_for_epsilon(kappa, epsilon0)

    # 5. 平衡状态求解（目标轴力500kN，小偏心受压）
    N_target = 500 * 1000  # 转换为N
    epsilon0_sol, N_sol, M_sol = analyzer.find_balance_conditions(kappa, N_target)

    # 6. 全过程分析（包含轴力影响）
    results = analyzer.analyze_full_range(
        N_target=500*1000,  # 500kN轴力下的弯矩-曲率关系
        kappa_start=0,
        kappa_end=0.0022,
        n_steps=200
    )

    if "error" in results:
        return {"error": results["error"]}

    # 7. 返回结果字典
    max_moment = max(results["moments"])
    return {
        "section_info": {
            "type": "不规则对称截面",
            "height": 800,  # mm
            "contour": irregular_contour,
            "reinforcement": {
                "top": {"count": 2, "diameter": 18, "area": top_area, "depth": cover},
                "middle": {"count": 2, "diameter": 20, "area": middle_area, "depth": 50},
                "bottom": {"count": 3, "diameter": 25, "area": bottom_area, "depth": cover}
            }
        },
        "materials": {
            "concrete": "C45",
            "steel": "HRB400",
            "f_cd": analyzer.f_cd,
            "f_yd": analyzer.f_yd
        },
        "single_calculation": {
            "kappa": kappa,
            "epsilon0": epsilon0,
            "N": N / 1000,  # kN
            "M": M / 1e6    # kN·m
        },
        "balance_calculation": {
            "N_target": N_target / 1000,  # kN
            "epsilon0_sol": epsilon0_sol,
            "N_sol": N_sol / 1000,  # kN
            "M_sol": M_sol / 1e6    # kN·m
        },
        "full_analysis": {
            "n_steps": len(results['kappas']),
            "max_moment": max_moment / 1e6,  # kN·m
            "failure_mode": results['failure_mode'],
            "final_curvature": results['kappas'][-1],
            "kappas": results['kappas'],
            "moments": [m / 1e6 for m in results['moments']],  # kN·m
            "epsilons0": results['epsilons0'],
            "max_eps_concrete": results['max_eps_concrete'],
            "min_eps_concrete": results['min_eps_concrete']
        }
    }

def test_irregular_symmetric_section():
    """测试函数，打印结果（使用硬编码参数）"""
    results = analyze_irregular_symmetric_section()

    if "error" in results:
        print(f"分析出错: {results['error']}")
        return

    print("=== 不规则对称截面测试 - 初始化完成 ===")
    print(f"默认混凝土类型: {results['materials']['concrete']}, 钢筋类型: {results['materials']['steel']}")
    print(f"混凝土抗压强度设计值: {results['materials']['f_cd']:.2f} MPa")
    print(f"钢筋屈服强度设计值: {results['materials']['f_yd']:.2f} MPa\n")

    print("=== 不规则对称截面参数更新 ===")
    print(f"截面总高: {results['section_info']['height']}mm（y从-400到400mm）")
    top = results['section_info']['reinforcement']['top']
    middle = results['section_info']['reinforcement']['middle']
    bottom = results['section_info']['reinforcement']['bottom']
    print(f"底部钢筋：{bottom['count']}Φ{bottom['diameter']}，面积: {bottom['area']:.2f} mm²，位置: -{400 - bottom['depth']}.00mm")
    print(f"腰部钢筋：{middle['count']}Φ{middle['diameter']}，面积: {middle['area']:.2f} mm²，位置: -{200 - middle['depth']}.00mm")
    print(f"顶部钢筋：{top['count']}Φ{top['diameter']}，面积: {top['area']:.2f} mm²，位置: {400 - top['depth']}.00mm")
    print(f"纤维数量: {len(results['full_analysis']['kappas'])}\n")  # 近似

    single = results['single_calculation']
    print("=== 单工况计算结果 ===")
    print(f"曲率 {single['kappa']} 下的轴力: {single['N']:.2f} kN")
    print(f"曲率 {single['kappa']} 下的弯矩: {single['M']:.2f} kN·m\n")

    balance = results['balance_calculation']
    print("=== 平衡状态求解 ===")
    print(f"目标轴力 {balance['N_target']:.0f}kN 对应的轴向应变: {balance['epsilon0_sol']:.6f}")
    print(f"平衡轴力: {balance['N_sol']:.2f} kN")
    print(f"平衡弯矩: {balance['M_sol']:.2f} kN·m\n")

    full = results['full_analysis']
    print("=== 不规则对称截面分析结果 ===")
    print(f"分析步数: {full['n_steps']}")
    print(f"最大弯矩: {full['max_moment']:.2f} kN·m")
    print(f"破坏模式: {full['failure_mode']}")
    print(f"最终曲率: {full['final_curvature']:.6f} 1/m")

    # 保存结果到CSV
    np.savetxt(
        "concrete_section_analysis/results/irregular_section_results.csv",
        np.column_stack([
            full["kappas"],
            full["moments"],
            full["max_eps_concrete"],
            full["min_eps_concrete"]
        ]),
        header="曲率,弯矩(kN·m),最大混凝土应变,最小混凝土应变",
        delimiter=",",
        fmt="%.6f,%.4f,%.6f,%.6f"
    )
    print("\n结果已保存到 results/irregular_section_results.csv")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # 如果提供了命令行参数，则使用配置文件
        config_file = sys.argv[1]
        print(f"使用配置文件: {config_file}")
        test_irregular_section_from_config(config_file)
    else:
        # 默认使用硬编码参数
        print("使用默认参数进行测试")
        test_irregular_symmetric_section()
