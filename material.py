class Material:
    """材料本构关系定义（符合GB 50010-2010规范）"""
    @staticmethod
    def concrete_stress(epsilon, f_cd, eps0, epsu, E_c):
        """混凝土受压应力-应变关系（GB 50010-2010）"""
        if epsilon >= 0:  # 受拉区混凝土，此处仅处理受压
            return 0.0
        epsilon = abs(epsilon)  # 转为绝对值计算
        
        # 上升段：抛物线（ε ≤ ε0）
        if epsilon <= eps0:
            return f_cd * (2 * (epsilon / eps0) - (epsilon / eps0) ** 2)
        # 下降段：斜直线（ε0 < ε ≤ εu）
        elif epsilon <= epsu:
            return f_cd * (1 - 0.8 * (epsilon - eps0) / (epsu - eps0))
        # 超过极限压应变：混凝土压碎
        else:
            return 0.0
    
    @staticmethod
    def concrete_tensile_stress(epsilon, f_td, E_c, eps_t0, eps_tu):
        """混凝土受拉应力-应变关系（GB 50010-2010）"""
        if epsilon <= 0:  # 受压区混凝土，此处仅处理受拉
            return 0.0
        
        # 上升段：线性（ε ≤ ε_t0）
        if epsilon <= eps_t0:
            return E_c * epsilon
        # 下降段：斜直线（ε_t0 < ε ≤ ε_tu）
        elif epsilon <= eps_tu:
            return f_td * (1 - 1.7 * (epsilon - eps_t0) / (eps_tu - eps_t0))
        # 超过极限拉应变：混凝土开裂
        else:
            return 0.0
    
    @staticmethod
    def steel_stress(epsilon, f_yd, E_s):
        """钢筋应力-应变关系（GB 50010-2010，有明显屈服点钢筋）"""
        sigma = E_s * epsilon
        # 受拉屈服
        if sigma > f_yd:
            return f_yd
        # 受压屈服
        elif sigma < -f_yd:
            return -f_yd
        # 弹性阶段
        else:
            return sigma