import numpy as np
from analyzer_ver1 import RCSectionAnalyzer

def test_rc_section_analyzer():
    # 1. 初始化分析器
    analyzer = RCSectionAnalyzer()
    print("=== 初始化完成 ===")
    print(f"默认混凝土类型: {analyzer.concrete_type}, 钢筋类型: {analyzer.steel_type}")
    print(f"混凝土抗压强度设计值: {analyzer.f_cd:.2f} MPa")
    print(f"钢筋屈服强度设计值: {analyzer.f_yd:.2f} MPa\n")

    # 2. 测试材料参数设置
    try:
        analyzer.set_materials("C40", "HRB500")
        print("=== 材料参数更新 ===")
        print(f"更新后混凝土类型: {analyzer.concrete_type}, 抗压强度: {analyzer.f_cd:.2f} MPa")
        print(f"更新后钢筋类型: {analyzer.steel_type}, 屈服强度: {analyzer.f_yd:.2f} MPa\n")
    except ValueError as e:
        print(f"材料设置错误: {e}")

    # 3. 测试截面参数设置（改为T形对称截面）
    try:
        # T形截面参数（对称截面）：
        # 翼缘宽度600mm，翼缘厚度150mm，腹板宽度300mm，总高度600mm
        # 钢筋配置：顶部3Φ20（翼缘顶部），底部4Φ25（腹板底部），保护层厚度40mm
        top_area = 3 * np.pi * (20/2)**2  # 顶部钢筋面积
        bottom_area = 4 * np.pi * (25/2)** 2  # 底部钢筋面积
        
        # 非矩形截面参数（假设分析仪支持T形截面定义）
        analyzer.set_section(
            # T形截面参数：[翼缘宽, 翼缘厚, 腹板宽, 总高]
            dimensions=[600, 150, 300, 600],
            reinforcement={
                # 顶部钢筋位于翼缘顶部：保护层40mm
                "top": {"area": top_area, "depth": 40},
                # 底部钢筋位于截面底部：总高 - 保护层 = 600 - 40 = 560mm处
                "bottom": {"area": bottom_area, "depth": 560}
            }
        )
        print("=== 截面参数更新（T形对称截面） ===")
        print(f"T形截面尺寸: 翼缘{analyzer.dimensions[0]}×{analyzer.dimensions[1]}mm, "
              f"腹板{analyzer.dimensions[2]}×{analyzer.dimensions[3]}mm")
        print(f"顶部钢筋面积: {analyzer.reinforcement['top']['area']:.2f} mm²")
        print(f"底部钢筋面积: {analyzer.reinforcement['bottom']['area']:.2f} mm²")
        print(f"纤维数量: {len(analyzer.fiber_heights)}, 顶部钢筋位置: {analyzer.steel_positions[0]:.2f}mm\n")
    except Exception as e:
        print(f"截面设置错误: {e}")

    # 4. 测试单工况计算
    kappa = 0.0005  # 曲率
    epsilon0 = 0.0001  # 轴向应变
    N, M = analyzer.calculate_section_for_epsilon(kappa, epsilon0)
    print("=== 单工况计算结果 ===")
    print(f"曲率 {kappa} 下的轴力: {N/1000:.2f} kN")  # 转换为kN
    print(f"曲率 {kappa} 下的弯矩: {M/1e6:.2f} kN·m\n")  # 转换为kN·m

    # 5. 测试平衡状态求解
    N_target = 0  # 目标轴力: 0kN
    epsilon0_sol, N_sol, M_sol = analyzer.find_balance_conditions(kappa, N_target)
    print("=== 平衡状态求解 ===")
    print(f"目标轴力 {N_target}kN 对应的轴向应变: {epsilon0_sol:.6f}")
    print(f"平衡状态下的轴力: {N_sol/1000:.2f} kN")
    print(f"平衡状态下的弯矩: {M_sol/1e6:.2f} kN·m\n")

    # 6. 测试全过程分析
    print("=== 开始全过程分析 (可能需要几秒) ===")
    results = analyzer.analyze_full_range(
        N_target=0,  # 轴力0kN
        kappa_start=0,
        kappa_end=0.002,
        n_steps=200
    )

    if "error" in results:
        print(f"分析出错: {results['error']}")
        return

    print("=== 全过程分析结果 ===")
    print(f"分析步数: {len(results['kappas'])}")
    print(f"最大弯矩: {max(results['moments'])/1e6:.2f} kN·m")
    print(f"破坏模式: {results['failure_mode']}")
    print(f"最终曲率: {results['kappas'][-1]:.6f}")

    # 7. 简单保存结果到文件
    np.savetxt(
        "concrete_section_analysis/results/t_section_analysis_results.csv",
        np.column_stack([
            results['kappas'],
            np.array(results['moments'])/1e6,  # 转换为kN·m
            results['max_eps_concrete'],
            results['min_eps_concrete']
        ]),
        header="曲率,弯矩(kN·m),最大混凝土应变,最小混凝土应变",
        delimiter=",",
        fmt="%.6f,%.4f,%.6f,%.6f"
    )
    print("\n结果已保存到 results/t_section_analysis_results.csv")

if __name__ == "__main__":
    test_rc_section_analyzer()