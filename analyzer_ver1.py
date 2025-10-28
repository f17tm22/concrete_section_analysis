import numpy as np
from scipy.optimize import fsolve
from scipy.interpolate import interp1d  # 新增：用于截面轮廓插值
from material import Material


class RCSectionAnalyzer:
    """钢筋混凝土截面分析器"""
    # 修正混凝土类型重复定义
    CONCRETE_TYPES = {
        "C20": {"f_ck": 20, "description": "混凝土强度等级C20"},
        "C25": {"f_ck": 25, "description": "混凝土强度等级C25"},
        "C30": {"f_ck": 30, "description": "混凝土强度等级C30"},
        "C35": {"f_ck": 35, "description": "混凝土强度等级C35"},
        "C40": {"f_ck": 40, "description": "混凝土强度等级C40"},
        "C45": {"f_ck": 45, "description": "混凝土强度等级C45"},
        "C50": {"f_ck": 50, "description": "混凝土强度等级C50"},
        "C55": {"f_ck": 55, "description": "混凝土强度等级C55"},
        "C60": {"f_ck": 60, "description": "混凝土强度等级C60"},
        "C65": {"f_ck": 65, "description": "混凝土强度等级C65"},
        "C70": {"f_ck": 70, "description": "混凝土强度等级C70"},
        "C75": {"f_ck": 75, "description": "混凝土强度等级C75"},
        "C80": {"f_ck": 80, "description": "混凝土强度等级C80"}
    }
    
    STEEL_TYPES = {
        "HPB300": {"f_yk": 300, "description": "光圆钢筋HPB300"},
        "HRB335": {"f_yk": 335, "description": "带肋钢筋HRB335"},
        "HRB400": {"f_yk": 400, "description": "带肋钢筋HRB400"},
        "HRB500": {"f_yk": 500, "description": "带肋钢筋HRB500"},
        "RRB400": {"f_yk": 400, "description": "余热处理带肋钢筋RRB400"}
    }
    
    def __init__(self):
        # 材料参数初始化（保持不变）
        self.concrete_type = "C30"
        self.steel_type = "HRB400"
        self.f_cd = None
        self.f_td = None
        self.E_c = None
        self.eps0 = None
        self.epsu = None
        self.eps_t0 = None
        self.eps_tu = None
        self.f_yd = None
        self.E_s = 2.0e5
        
        # 截面参数修改：支持对称轮廓
        self.section_type = "symmetric"  # 改为对称截面类型
        # 对称轮廓点：[(y坐标, 半宽), ...]，y=0为中和轴
        self.symmetric_contour = [
            (-250, 150),  # 底部点（y=-250mm处，半宽150mm）
            (250, 150)    # 顶部点（y=250mm处，半宽150mm）—— 等效原矩形截面
        ]
        self.reinforcement = {
            "top": {"area": 3*314, "depth": 50},  # 顶部钢筋：面积和保护层厚度
            "bottom": {"area": 3*314, "depth": 50}
        }
        
        # 分析参数（保持不变）
        self.n_fibers = 50
        self.fiber_heights = None
        self.fiber_areas = None
        self.steel_positions = []
        self.steel_areas = []
        
        # 初始化材料和截面
        self._initialize_materials()
        self._initialize_section()
    
    # _calc_concrete_params、_initialize_materials 方法保持不变
    def _calc_concrete_params(self):
        """
        根据所选混凝土等级计算并设置混凝土的力学参数（单位：MPa / 无量纲）。
        这些值为常用经验值，可根据规范或更精确的模型调整。
        """
        f_ck = self.CONCRETE_TYPES[self.concrete_type]["f_ck"]
        # 设计值或模型值（可按规范修改）
        self.f_cd = float(f_ck)               # 轴心抗压强度近似（MPa）
        self.f_td = max(0.2 * f_ck, 0.0)      # 抗拉强度的近似值（MPa）
        self.E_c = 3.0e4                      # 混凝土弹性模量约 30 GPa (MPa 单位系)
        # 应变参数（经验值）
        self.eps0 = 0.002     # 峰值压应变
        self.epsu = 0.0035    # 极限压应变
        self.eps_t0 = 1e-4    # 拉切开始应变
        self.eps_tu = 1e-3    # 拉开裂极限应变

    def _initialize_materials(self):
        """
        初始化材料相关参数（混凝土和钢筋），确保后续计算可用。
        """
        # 计算混凝土相关参数
        self._calc_concrete_params()

        # 钢筋设计强度（取特征强度除以部分系数 gamma_s）
        f_yk = self.STEEL_TYPES[self.steel_type]["f_yk"]
        gamma_s = 1.15
        self.f_yd = float(f_yk) / gamma_s

    def _initialize_section(self):
        """基于对称轮廓点初始化截面纤维和钢筋位置"""
        # 1. 提取轮廓点并排序
        sorted_contour = sorted(self.symmetric_contour, key=lambda x: x[0])
        y_coords_contour = np.array([p[0] for p in sorted_contour])
        half_widths = np.array([p[1] for p in sorted_contour])
        min_y, max_y = y_coords_contour[0], y_coords_contour[-1]
        
        # 2. 生成纤维高度坐标（覆盖整个截面高度）
        self.fiber_heights = np.linspace(min_y, max_y, self.n_fibers)
        dy = self.fiber_heights[1] - self.fiber_heights[0]  # 纤维高度间隔
        
        # 3. 插值计算每个纤维位置的半宽
        interp_func = interp1d(
            y_coords_contour, 
            half_widths, 
            kind='linear', 
            fill_value="extrapolate"
        )
        half_width_fibers = interp_func(self.fiber_heights)
        full_width_fibers = 2 * half_width_fibers  # 对称截面全宽
        
        # 4. 计算纤维面积（宽度×高度间隔）
        self.fiber_areas = full_width_fibers * dy
        
        # 5. 计算钢筋位置（基于轮廓边缘和保护层厚度）
        self.steel_positions = []
        self.steel_areas = []
        
        # 顶部钢筋位置：轮廓顶部y坐标 - 保护层厚度
        top_pos = max_y - self.reinforcement["top"]["depth"]
        self.steel_positions.append(top_pos)
        self.steel_areas.append(self.reinforcement["top"]["area"])
        
        # 底部钢筋位置：轮廓底部y坐标 + 保护层厚度
        bottom_pos = min_y + self.reinforcement["bottom"]["depth"]
        self.steel_positions.append(bottom_pos)
        self.steel_areas.append(self.reinforcement["bottom"]["area"])
    
    def set_materials(self, concrete_type, steel_type):
        """保持不变"""
        if concrete_type not in self.CONCRETE_TYPES:
            raise ValueError(f"未知的混凝土类型: {concrete_type}")
        if steel_type not in self.STEEL_TYPES:
            raise ValueError(f"未知的钢筋类型: {steel_type}")
        self.concrete_type = concrete_type
        self.steel_type = steel_type
        self._initialize_materials()
    
    def set_section(self, contour_points, reinforcement):
        if len(contour_points) == 2 and all(isinstance(p, (int, float)) for p in contour_points):
            # rectangular section
            width, height = contour_points
            sorted_contour = [(-height/2, width/2), (height/2, width/2)]
        else:
            # irregular section
            sorted_contour = sorted(contour_points, key=lambda x: x[0])
            y_coords = [p[0] for p in sorted_contour]
            min_y, max_y = y_coords[0], y_coords[-1]
            
            # 检查对称性（中和轴y=0）
            if not np.isclose(-min_y, max_y, atol=1e-3):
                raise ValueError("截面轮廓必须关于中和轴（y=0）对称")
            # 检查半宽非负
            if any(p[1] < 0 for p in sorted_contour):
                raise ValueError("截面半宽不能为负值")
        
        self.symmetric_contour = sorted_contour
        self.reinforcement = reinforcement
        self._initialize_section()
    
    # calculate_section_for_epsilon、find_balance_conditions、analyze_full_range 方法保持不变
    def calculate_section_for_epsilon(self, kappa, epsilon0):
        fiber_epsilons = epsilon0 + kappa * self.fiber_heights
        
        concrete_stresses = np.array([
            Material.concrete_stress(eps, self.f_cd, self.eps0, self.epsu, self.E_c) 
            for eps in fiber_epsilons
        ])
        tensile_stresses = np.array([
            Material.concrete_tensile_stress(eps, self.f_td, self.E_c, self.eps_t0, self.eps_tu)
            for eps in fiber_epsilons
        ])
        total_stresses = concrete_stresses + tensile_stresses
        
        N_concrete = np.sum(total_stresses * self.fiber_areas)
        M_concrete = np.sum(total_stresses * self.fiber_areas * self.fiber_heights)
        
        N_steel = 0.0
        M_steel = 0.0
        for i, pos in enumerate(self.steel_positions):
            eps = epsilon0 + kappa * pos
            stress = Material.steel_stress(eps, self.f_yd, self.E_s)
            area = self.steel_areas[i]
            N_steel += stress * area
            M_steel += stress * area * pos
        
        return N_concrete + N_steel, M_concrete + M_steel
    
    def find_balance_conditions(self, kappa, N_target):
        def equilibrium_equation(epsilon0):
            N, _ = self.calculate_section_for_epsilon(kappa, epsilon0)
            return N - N_target
        
        # 使用合适的初始猜测：对于受压，epsilon0 为负
        initial_guess = -0.001 if N_target > 0 else 0.001
        epsilon0_sol = fsolve(equilibrium_equation, initial_guess)[0]
        N, M = self.calculate_section_for_epsilon(kappa, epsilon0_sol)
        return epsilon0_sol, N, M
    
    def analyze_full_range(self, N_target=0, kappa_start=0, kappa_end=0.001, n_steps=100):
        kappas = np.linspace(kappa_start, kappa_end, n_steps)
        moments = []
        epsilons0 = []
        max_eps_concrete = []
        min_eps_concrete = []
        
        for kappa in kappas:
            try:
                epsilon0, N, M = self.find_balance_conditions(kappa, N_target)
                epsilons0.append(epsilon0)
                moments.append(M)
                
                fiber_epsilons = epsilon0 + kappa * self.fiber_heights
                max_eps_concrete.append(np.max(fiber_epsilons))
                min_eps_concrete.append(np.min(fiber_epsilons))
                
                if np.min(fiber_epsilons) <= -self.epsu:
                    return {
                        "kappas": kappas[:len(moments)],
                        "moments": moments,
                        "epsilons0": epsilons0,
                        "max_eps_concrete": max_eps_concrete,
                        "min_eps_concrete": min_eps_concrete,
                        "failure_mode": f"混凝土达到极限压应变 {self.epsu:.6f}"
                    }
            except Exception as e:
                print(f"在曲率 {kappa} 处无法收敛: {str(e)}")
                break
        
        return {
            "kappas": kappas[:len(moments)],
            "moments": moments,
            "epsilons0": epsilons0,
            "max_eps_concrete": max_eps_concrete,
            "min_eps_concrete": min_eps_concrete,
            "failure_mode": "未达到破坏条件"
        }