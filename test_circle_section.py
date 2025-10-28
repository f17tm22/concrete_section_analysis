import numpy as np
from analyzer_ver1 import RCSectionAnalyzer

def test_circle_section():
    # 1. 初始化分析器
    analyzer = RCSectionAnalyzer()
    print("=== 圆形截面测试 - 初始化完成 ===")
    print(f"默认混凝土类型: {analyzer.concrete_type}, 钢筋类型: {analyzer.steel_type}")
    print(f"混凝土抗压强度设计值: {analyzer.f_cd:.2f} MPa")
    print(f"钢筋屈服强度设计值: {analyzer.f_yd:.2f} MPa\n")

    # 2. 设置材料（C40混凝土 + HRB500钢筋）
    try:
        analyzer.set_materials("C40", "HRB500")
        print("=== 材料参数更新 ===")
        print(f"混凝土类型: {analyzer.concrete_type}, 抗压强度: {analyzer.f_cd:.2f} MPa")
        print(f"钢筋类型: {analyzer.steel_type}, 屈服强度: {analyzer.f_yd:.2f} MPa\n")
    except ValueError as e:
        print(f"材料设置错误: {e}")
        return

    # 3. 定义圆形截面轮廓点（对称于y=0）
    try:
        # 圆形参数：直径300mm → 半径r=150mm，y范围[-150, 150]mm
        r = 150  # 圆半径(mm)
        cover = 40  # 保护层厚度(mm)
        
        # 生成轮廓点：取10个点覆盖y范围，确保形状精准（越多越精确）
        y_coords = np.linspace(-r, r, 10)  # y从-150到150mm
        circle_contour = []
        for y in y_coords:
            # 圆方程：x² + y² = r² → 半宽x = √(r² - y²)
            half_width = np.sqrt(r**2 - y**2)
            circle_contour.append((y, half_width))
        
        # 钢筋配置：顶部2Φ18（y=150-40=110mm），底部2Φ22（y=-150+40=-110mm）
        top_area = 2 * np.pi * (18/2)**2  # 顶部钢筋面积：2×254.47=508.94mm²
        bottom_area = 2 * np.pi * (22/2)**2  # 底部钢筋面积：2×380.13=760.27mm²
        
        # 调用set_section（适配analyzer_ver1的轮廓点参数）
        analyzer.set_section(
            contour_points=circle_contour,
            reinforcement={
                "top": {"area": top_area, "depth": cover},  # depth=保护层厚度
                "bottom": {"area": bottom_area, "depth": cover}
            }
        )
        
        print("=== 圆形截面参数更新 ===")
        print(f"圆形截面直径: {2*r}mm（半径{r}mm）")
        print(f"顶部钢筋：2Φ18，面积: {top_area:.2f} mm²，位置: {110:.2f}mm（y坐标）")
        print(f"底部钢筋：2Φ22，面积: {bottom_area:.2f} mm²，位置: {-110:.2f}mm（y坐标）")
        print(f"纤维数量: {len(analyzer.fiber_heights)}\n") # type: ignore
    except Exception as e:
        print(f"截面设置错误: {e}")
        return

    # 4. 单工况计算（曲率0.0005，轴向应变0.0001）
    kappa = 0.0005
    epsilon0 = 0.0001
    N, M = analyzer.calculate_section_for_epsilon(kappa, epsilon0)
    print("=== 单工况计算结果 ===")
    print(f"曲率 {kappa} 下的轴力: {N/1000:.2f} kN")
    print(f"曲率 {kappa} 下的弯矩: {M/1e6:.2f} kN·m\n")

    # 5. 平衡状态求解（目标轴力0kN）
    N_target = 0
    epsilon0_sol, N_sol, M_sol = analyzer.find_balance_conditions(kappa, N_target)
    print("=== 平衡状态求解 ===")
    print(f"目标轴力 {N_target}kN 对应的轴向应变: {epsilon0_sol:.6f}")
    print(f"平衡轴力: {N_sol/1000:.2f} kN（接近0为正常）")
    print(f"平衡弯矩: {M_sol/1e6:.2f} kN·m\n")

    # 6. 全过程分析（纯弯，200步）
    print("=== 开始全过程分析（约3-5秒） ===")
    results = analyzer.analyze_full_range(
        N_target=0,
        kappa_start=0,
        kappa_end=0.0025,  # 圆形截面延性较好，适当增大最大曲率
        n_steps=200
    )

    if "error" in results:
        print(f"分析出错: {results['error']}")
        return

    # 7. 输出结果并保存
    max_moment = max(results["moments"])
    print("=== 圆形截面分析结果 ===")
    print(f"分析步数: {len(results['kappas'])}")
    print(f"极限弯矩: {max_moment/1e6:.2f} kN·m")
    print(f"破坏模式: {results['failure_mode']}")
    print(f"最终曲率: {results['kappas'][-1]:.6f} 1/m")

    # 保存结果到CSV（区分圆形截面）
    np.savetxt(
        "concrete_section_analysis/results/circle_section_results.csv",
        np.column_stack([
            results["kappas"],
            np.array(results["moments"])/1e6,
            results["max_eps_concrete"],
            results["min_eps_concrete"]
        ]),
        header="曲率,弯矩(kN·m),最大混凝土应变,最小混凝土应变",
        delimiter=",",
        fmt="%.6f,%.4f,%.6f,%.6f"
    )
    print("\n结果已保存到 results/circle_section_results.csv")

if __name__ == "__main__":
    test_circle_section()