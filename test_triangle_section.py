import numpy as np
from analyzer_ver1 import RCSectionAnalyzer

def test_triangle_section():
    # 1. 初始化分析器
    analyzer = RCSectionAnalyzer()
    print("=== 等腰三角形截面测试 - 初始化完成 ===")
    print(f"默认混凝土类型: {analyzer.concrete_type}, 钢筋类型: {analyzer.steel_type}")
    print(f"混凝土抗压强度设计值: {analyzer.f_cd:.2f} MPa")
    print(f"钢筋屈服强度设计值: {analyzer.f_yd:.2f} MPa\n")

    # 2. 设置材料（C35混凝土 + HRB400钢筋）
    try:
        analyzer.set_materials("C35", "HRB400")
        print("=== 材料参数更新 ===")
        print(f"混凝土类型: {analyzer.concrete_type}, 抗压强度: {analyzer.f_cd:.2f} MPa")
        print(f"钢筋类型: {analyzer.steel_type}, 屈服强度: {analyzer.f_yd:.2f} MPa\n")
    except ValueError as e:
        print(f"材料设置错误: {e}")
        return

    # 3. 定义等腰三角形轮廓点（对称于y=0）
    try:
        # 三角形参数：总高600mm（y[-300, 300]），底部宽600mm（半宽300mm）
        total_height = 600  # 总高(mm)
        bottom_width = 600  # 底部宽(mm)
        cover = 40  # 保护层厚度(mm)
        half_bottom_width = bottom_width / 2  # 底部半宽300mm
        
        # 三角形轮廓关键节点（3个点足够线性插值还原形状）
        # 节点1：底部（y=-300mm，半宽300mm）
        # 节点2：腰部（y=0mm，半宽150mm，线性过渡）
        # 节点3：顶部（y=300mm，半宽0mm，尖点）
        triangle_contour = [
            (-total_height/2, half_bottom_width),  # (-300, 300)
            (0, half_bottom_width/2),              # (0, 150)
            (total_height/2, 0)                    # (300, 0)
        ]
        
        # 钢筋配置：顶部1Φ16（y=300-40=260mm，需确认半宽足够）
        # 底部2Φ20（y=-300+40=-260mm，半宽=300 - (300/300)*260=40mm，足够放置钢筋）
        top_area = 1 * np.pi * (16/2)**2  # 顶部钢筋面积：201.06mm²
        bottom_area = 2 * np.pi * (20/2)**2  # 底部钢筋面积：628.32mm²
        
        # 调用set_section
        analyzer.set_section(
            contour_points=triangle_contour,
            reinforcement={
                "top": {"area": top_area, "depth": cover},
                "bottom": {"area": bottom_area, "depth": cover}
            }
        )
        
        # 计算钢筋实际y坐标
        top_steel_y = total_height/2 - cover  # 300-40=260mm
        bottom_steel_y = -total_height/2 + cover  # -300+40=-260mm
        
        print("=== 等腰三角形截面参数更新 ===")
        print(f"三角形尺寸: 总高{total_height}mm，底部宽{bottom_width}mm")
        print(f"顶部钢筋：1Φ16，面积: {top_area:.2f} mm²，位置: {top_steel_y:.2f}mm（y坐标）")
        print(f"底部钢筋：2Φ20，面积: {bottom_area:.2f} mm²，位置: {bottom_steel_y:.2f}mm（y坐标）")
        print(f"纤维数量: {len(analyzer.fiber_heights)}\n") # type: ignore
    except Exception as e:
        print(f"截面设置错误: {e}")
        return

    # 4. 单工况计算（曲率0.0006，轴向应变0.0001）
    kappa = 0.0006
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
        kappa_end=0.002,  # 三角形截面脆性较强，适当减小最大曲率
        n_steps=200
    )

    if "error" in results:
        print(f"分析出错: {results['error']}")
        return

    # 7. 输出结果并保存
    max_moment = max(results["moments"])
    print("=== 等腰三角形截面分析结果 ===")
    print(f"分析步数: {len(results['kappas'])}")
    print(f"极限弯矩: {max_moment/1e6:.2f} kN·m")
    print(f"破坏模式: {results['failure_mode']}")
    print(f"最终曲率: {results['kappas'][-1]:.6f} 1/m")

    # 保存结果到CSV（区分三角形截面）
    np.savetxt(
        "concrete_section_analysis/results/triangle_section_results.csv",
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
    print("\n结果已保存到 results/triangle_section_results.csv")

if __name__ == "__main__":
    test_triangle_section()