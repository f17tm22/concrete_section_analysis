import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGroupBox, QLabel, QComboBox, QSpinBox, 
                            QDoubleSpinBox, QPushButton, QGridLayout, QTabWidget,
                            QMessageBox, QSplitter, QFileDialog, QLineEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
import matplotlib
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import sys
import os
sys.path.append(os.path.dirname(__file__))
from analyzer_ver1 import RCSectionAnalyzer
from irregular_section import analyze_irregular_section_from_config

# 配置matplotlib字体设置
matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Liberation Sans', 'Arial Unicode MS', 'Microsoft YaHei', 'SimHei', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
matplotlib.rcParams['axes.labelsize'] = 12
matplotlib.rcParams['xtick.labelsize'] = 10
matplotlib.rcParams['ytick.labelsize'] = 10
matplotlib.rcParams['legend.fontsize'] = 10

# 禁用字体缺失警告
import warnings
warnings.filterwarnings("ignore", message=".*Glyph.*missing from font.*")


class AnalysisThread(QThread):
    """分析线程类，用于在后台执行耗时的分析任务"""
    analysis_done = pyqtSignal(dict)  # 分析完成信号，传递结果字典
    
    def __init__(self, analyzer, params):
        super().__init__()
        self.analyzer = analyzer
        self.params = params  # 分析所需参数
        
    def run(self):
        """线程执行函数，包含耗时的分析逻辑"""
        try:
            # 检查截面类型
            if self.params.get("section_type") == "irregular":
                # 不规则截面分析 - 从配置文件读取
                config_file = self.params.get("config_file")
                if not config_file:
                    results = {"error": "未选择不规则截面配置文件"}
                else:
                    results = analyze_irregular_section_from_config(config_file)
                # 发送分析结果
                self.analysis_done.emit(results)
                return
            
            # 矩形截面分析
            # 设置材料参数
            self.analyzer.set_materials(
                self.params["concrete"],
                self.params["steel"]
            )
            
            # 设置截面参数
            self.analyzer.set_section(
                [self.params["width"], self.params["height"]],
                {
                    "top": {
                        "area": self.params["top_area"],
                        "depth": self.params["top_cover"]
                    },
                    "bottom": {
                        "area": self.params["bottom_area"],
                        "depth": self.params["bottom_cover"]
                    }
                }
            )
            
            # 执行分析
            results = self.analyzer.analyze_full_range(
                N_target=self.params["N_target"] * 1000,  # 转换为N
                kappa_start=0,
                kappa_end=0.0015,
                n_steps=self.params["n_steps"]
            )
            
            # 发送分析结果
            self.analysis_done.emit(results)
            
        except Exception as e:
            # 发送错误信息
            self.analysis_done.emit({"error": str(e)})


class MplCanvas(FigureCanvas):
    """Matplotlib画布封装类"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)
        self.setParent(parent)
        self.fig.tight_layout()


class RCSectionAnalysisGUI(QMainWindow):
    """钢筋混凝土截面分析界面"""
    def __init__(self):
        super().__init__()
        self.analyzer = RCSectionAnalyzer()
        self.analysis_thread = None  # 分析线程对象
        self.initUI()
        
    def initUI(self):
        """初始化界面"""
        # 设置窗口基本属性
        self.setWindowTitle('钢筋混凝土截面全过程分析 (GB 50010-2010)')
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建主部件和布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 创建左侧参数设置面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 材料选择组
        material_group = QGroupBox("材料选择")
        material_layout = QGridLayout()
        material_group.setLayout(material_layout)
        
        # 混凝土类型选择
        material_layout.addWidget(QLabel("混凝土强度等级:"), 0, 0)
        self.concrete_combo = QComboBox()
        for concrete in self.analyzer.CONCRETE_TYPES.keys():
            self.concrete_combo.addItem(concrete)
        self.concrete_combo.setCurrentText("C30")
        material_layout.addWidget(self.concrete_combo, 0, 1)
        
        # 钢筋类型选择
        material_layout.addWidget(QLabel("钢筋类型:"), 1, 0)
        self.steel_combo = QComboBox()
        for steel in self.analyzer.STEEL_TYPES.keys():
            self.steel_combo.addItem(steel)
        self.steel_combo.setCurrentText("HRB400")
        material_layout.addWidget(self.steel_combo, 1, 1)
        
        # 材料参数显示
        self.material_params = QLabel()
        material_layout.addWidget(self.material_params, 2, 0, 1, 2)
        self.update_material_params()
        
        # 连接材料选择变化事件
        self.concrete_combo.currentTextChanged.connect(self.update_material_params)
        self.steel_combo.currentTextChanged.connect(self.update_material_params)
        
        # 截面参数组
        section_group = QGroupBox("截面参数")
        section_layout = QGridLayout()
        section_group.setLayout(section_layout)
        
        # 截面类型选择
        section_layout.addWidget(QLabel("截面类型:"), 0, 0)
        self.section_type_combo = QComboBox()
        self.section_type_combo.addItem("矩形截面", "rectangular")
        self.section_type_combo.addItem("不规则对称截面", "irregular")
        self.section_type_combo.setCurrentText("矩形截面")
        section_layout.addWidget(self.section_type_combo, 0, 1)
        
        # 连接截面类型变化事件
        self.section_type_combo.currentTextChanged.connect(self.on_section_type_changed)
        
        # JSON配置文件选择（仅不规则截面显示）
        self.config_file_label = QLabel("JSON配置文件:")
        section_layout.addWidget(self.config_file_label, 1, 0)
        self.config_file_layout = QHBoxLayout()
        self.config_file_edit = QLineEdit()
        self.config_file_edit.setPlaceholderText("选择不规则截面配置文件...")
        self.config_file_edit.setEnabled(False)
        self.config_file_button = QPushButton("浏览...")
        self.config_file_button.setEnabled(False)
        self.config_file_button.clicked.connect(self.select_config_file)
        self.config_file_layout.addWidget(self.config_file_edit)
        self.config_file_layout.addWidget(self.config_file_button)
        section_layout.addLayout(self.config_file_layout, 1, 1)
        
        # 矩形截面参数标签
        self.width_label = QLabel("截面宽度 (mm):")
        section_layout.addWidget(self.width_label, 2, 0)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(100, 2000)
        self.width_spin.setValue(300)
        section_layout.addWidget(self.width_spin, 2, 1)
        
        self.height_label = QLabel("截面高度 (mm):")
        section_layout.addWidget(self.height_label, 3, 0)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(100, 3000)
        self.height_spin.setValue(500)
        section_layout.addWidget(self.height_spin, 3, 1)
        
        # 顶部钢筋
        self.top_count_label = QLabel("顶部钢筋数量:")
        section_layout.addWidget(self.top_count_label, 4, 0)
        self.top_count_spin = QSpinBox()
        self.top_count_spin.setRange(1, 20)
        self.top_count_spin.setValue(3)
        section_layout.addWidget(self.top_count_spin, 4, 1)
        
        self.top_dia_label = QLabel("顶部钢筋直径 (mm):")
        section_layout.addWidget(self.top_dia_label, 5, 0)
        self.top_dia_spin = QSpinBox()
        self.top_dia_spin.setRange(8, 40)
        self.top_dia_spin.setValue(20)
        section_layout.addWidget(self.top_dia_spin, 5, 1)
        
        self.top_cover_label = QLabel("顶部保护层厚度 (mm):")
        section_layout.addWidget(self.top_cover_label, 6, 0)
        self.top_cover_spin = QSpinBox()
        self.top_cover_spin.setRange(15, 100)
        self.top_cover_spin.setValue(50)
        section_layout.addWidget(self.top_cover_spin, 6, 1)
        
        # 底部钢筋
        self.bottom_count_label = QLabel("底部钢筋数量:")
        section_layout.addWidget(self.bottom_count_label, 7, 0)
        self.bottom_count_spin = QSpinBox()
        self.bottom_count_spin.setRange(1, 20)
        self.bottom_count_spin.setValue(3)
        section_layout.addWidget(self.bottom_count_spin, 7, 1)
        
        self.bottom_dia_label = QLabel("底部钢筋直径 (mm):")
        section_layout.addWidget(self.bottom_dia_label, 8, 0)
        self.bottom_dia_spin = QSpinBox()
        self.bottom_dia_spin.setRange(8, 40)
        self.bottom_dia_spin.setValue(25)
        section_layout.addWidget(self.bottom_dia_spin, 8, 1)
        
        self.bottom_cover_label = QLabel("底部保护层厚度 (mm):")
        section_layout.addWidget(self.bottom_cover_label, 9, 0)
        self.bottom_cover_spin = QSpinBox()
        self.bottom_cover_spin.setRange(15, 100)
        self.bottom_cover_spin.setValue(50)
        section_layout.addWidget(self.bottom_cover_spin, 9, 1)
        
        # 钢筋面积显示
        self.steel_area_label = QLabel()
        section_layout.addWidget(self.steel_area_label, 10, 0, 1, 2)
        self.update_steel_area()
        
        # 连接钢筋参数变化事件
        self.top_count_spin.valueChanged.connect(self.update_steel_area)
        self.top_dia_spin.valueChanged.connect(self.update_steel_area)
        self.bottom_count_spin.valueChanged.connect(self.update_steel_area)
        self.bottom_dia_spin.valueChanged.connect(self.update_steel_area)
        
        # 分析参数组
        analysis_group = QGroupBox("分析参数")
        analysis_layout = QGridLayout()
        analysis_group.setLayout(analysis_layout)
        
        # 目标轴力
        analysis_layout.addWidget(QLabel("目标轴力 (kN):"), 0, 0)
        self.N_spin = QDoubleSpinBox()
        self.N_spin.setRange(-10000, 10000)
        self.N_spin.setValue(0)
        self.N_spin.setSingleStep(10)
        analysis_layout.addWidget(self.N_spin, 0, 1)
        
        # 分析步数
        analysis_layout.addWidget(QLabel("分析步数:"), 1, 0)
        self.step_spin = QSpinBox()
        self.step_spin.setRange(50, 1000)
        self.step_spin.setValue(200)
        analysis_layout.addWidget(self.step_spin, 1, 1)
        
        # 分析按钮
        self.analyze_btn = QPushButton("开始分析")
        self.analyze_btn.clicked.connect(self.perform_analysis)
        analysis_layout.addWidget(self.analyze_btn, 2, 0, 1, 2)
        
        # 添加各组到左侧布局
        left_layout.addWidget(material_group)
        left_layout.addWidget(section_group)
        left_layout.addWidget(analysis_group)
        left_layout.addStretch()
        
        # 创建右侧结果展示面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 创建结果标签页
        self.tabs = QTabWidget()
        
        # 结果摘要标签页
        summary_tab = QWidget()
        summary_layout = QVBoxLayout(summary_tab)
        
        # 结果摘要
        self.result_summary = QLabel("请点击开始分析按钮进行截面分析")
        # 使用系统默认字体，避免字体不存在的问题
        font = self.result_summary.font()
        font.setPointSize(16)
        self.result_summary.setFont(font)
        summary_layout.addWidget(self.result_summary)
        
        self.tabs.addTab(summary_tab, "结果摘要")
        
        # 弯矩-曲率曲线标签页
        self.moment_curvature_canvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.tabs.addTab(self.moment_curvature_canvas, "弯矩-曲率曲线")
        
        # 应变发展曲线标签页
        self.strain_canvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.tabs.addTab(self.strain_canvas, "应变发展曲线")
        
        # 中和轴应变曲线标签页
        self.neutral_axis_canvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.tabs.addTab(self.neutral_axis_canvas, "中和轴应变")
        
        # 添加标签页到右侧布局
        right_layout.addWidget(self.tabs)
        
        # 添加面板到分割器
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 800])  # 设置初始大小比例
        
        # 添加分割器到主布局
        main_layout.addWidget(splitter)
        
        # 显示窗口
        self.show()
        
        # 初始化截面类型状态
        self.on_section_type_changed()
    
    def update_material_params(self):
        """更新材料参数显示"""
        concrete_type = self.concrete_combo.currentText()
        steel_type = self.steel_combo.currentText()
        
        # 更新分析器材料参数
        try:
            self.analyzer.set_materials(concrete_type, steel_type)
        except ValueError as e:
            QMessageBox.warning(self, "参数错误", str(e))
            return
        
        # 构建参数文本，保护性格式化以避免 None 值导致的运算错误
        if self.analyzer.f_cd is None:
            params_text = "<b>材料参数:</b><br>请先设置材料参数"
        else:
            f_cd_text = f"{self.analyzer.f_cd:.2f} MPa" if self.analyzer.f_cd is not None else "N/A"
            f_td_text = f"{self.analyzer.f_td:.2f} MPa" if self.analyzer.f_td is not None else "N/A"
            E_c_text = f"{self.analyzer.E_c/1e3:.2f} GPa" if self.analyzer.E_c is not None else "N/A"
            epsu_text = f"{self.analyzer.epsu:.6f}" if self.analyzer.epsu is not None else "N/A"
            f_yd_text = f"{self.analyzer.f_yd:.2f} MPa" if self.analyzer.f_yd is not None else "N/A"
            E_s_text = f"{self.analyzer.E_s/1e3:.2f} GPa" if self.analyzer.E_s is not None else "N/A"

            params_text = (
                f"<b>材料参数:</b><br>\n"
                f"混凝土抗压强度设计值: {f_cd_text}<br>\n"
                f"混凝土抗拉强度设计值: {f_td_text}<br>\n"
                f"混凝土弹性模量: {E_c_text}<br>\n"
                f"混凝土极限压应变: {epsu_text}<br>\n"
                f"钢筋屈服强度设计值: {f_yd_text}<br>\n"
                f"钢筋弹性模量: {E_s_text}"
            )
        
        self.material_params.setText(params_text)
    
    def calculate_steel_area(self, count, diameter):
        """计算钢筋面积"""
        radius = diameter / 2
        return count * 3.1416 * radius * radius
    
    def update_steel_area(self):
        """更新钢筋面积显示"""
        # 只有在矩形截面模式下才更新钢筋面积
        if not self.width_label.isVisible():
            self.steel_area_label.setText("")
            return
            
        top_area = self.calculate_steel_area(
            self.top_count_spin.value(), 
            self.top_dia_spin.value()
        )
        
        bottom_area = self.calculate_steel_area(
            self.bottom_count_spin.value(), 
            self.bottom_dia_spin.value()
        )
        
        self.steel_area_label.setText(
            f"顶部钢筋面积: {top_area:.1f} mm² | 底部钢筋面积: {bottom_area:.1f} mm²"
        )
    
    def perform_analysis(self):
        """执行截面分析 - 启动子线程处理"""
        # 如果已有线程在运行，先终止
        if self.analysis_thread and self.analysis_thread.isRunning():
            self.analysis_thread.terminate()
        
        # 更新UI状态
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("分析中...")
        self.result_summary.setText("正在进行截面分析，请稍候...")
        
        # 收集所有分析参数
        params = {
            "section_type": self.section_type_combo.currentData(),
            "concrete": self.concrete_combo.currentText(),
            "steel": self.steel_combo.currentText(),
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "top_area": self.calculate_steel_area(
                self.top_count_spin.value(), 
                self.top_dia_spin.value()
            ),
            "top_cover": self.top_cover_spin.value(),
            "bottom_area": self.calculate_steel_area(
                self.bottom_count_spin.value(), 
                self.bottom_dia_spin.value()
            ),
            "bottom_cover": self.bottom_cover_spin.value(),
            "N_target": self.N_spin.value(),
            "n_steps": self.step_spin.value(),
        }
        
        # 如果是不规则截面，添加配置文件路径
        if params["section_type"] == "irregular":
            config_file = self.config_file_edit.text().strip()
            if not config_file:
                QMessageBox.warning(self, "参数错误", "请选择不规则截面配置文件")
                return
            params["config_file"] = config_file
        
        # 创建并启动分析线程
        self.analysis_thread = AnalysisThread(self.analyzer, params)
        self.analysis_thread.analysis_done.connect(self.on_analysis_finished)
        self.analysis_thread.finished.connect(self.on_thread_finished)  # 线程结束信号
        self.analysis_thread.start()
    
    def on_analysis_finished(self, results):
        """分析完成回调函数，在主线程中执行"""
        # 检查是否有错误
        if "error" in results:
            QMessageBox.critical(self, "分析错误", f"分析过程中发生错误: {results['error']}")
            return
        
        # 检查结果格式（不规则截面 vs 矩形截面）
        if "full_analysis" in results:
            # 不规则截面结果
            analysis_results = results["full_analysis"]
            section_info = results["section_info"]
            materials = results["materials"]
            
            # 计算最大弯矩及对应曲率
            max_moment = analysis_results["max_moment"]
            max_idx = analysis_results["moments"].index(max_moment)
            max_curvature = analysis_results["kappas"][max_idx]
            
            # 更新结果摘要
            summary_text = f"""<h3>不规则对称截面分析结果摘要</h3>
            <p></p>
            <b>极限弯矩:</b> {max_moment:.2f} kN·m<br>
            <b>对应曲率:</b> {max_curvature:.6f} 1/m<br>
            <b>破坏模式:</b> {analysis_results['failure_mode']}<br>
            <b>材料组合:</b> 混凝土 {materials['concrete']}, 钢筋 {materials['steel']}<br>
            <b>截面类型:</b> {section_info['type']}<br>
            <b>截面高度:</b> {section_info['height']} mm"""
        else:
            # 矩形截面结果
            if not results["moments"]:
                QMessageBox.warning(self, "分析结果", "未能获得有效的分析结果")
                return
            
            # 计算最大弯矩及对应曲率
            max_moment = max(results["moments"])
            max_idx = results["moments"].index(max_moment)
            max_curvature = results["kappas"][max_idx]
            
            # 更新结果摘要
            summary_text = f"""<h3>分析结果摘要</h3>
            <p></p>
            <b>极限弯矩:</b> {max_moment/1e6:.2f} kN·m<br>
            <b>对应曲率:</b> {max_curvature:.6f} 1/m<br>
            <b>破坏模式:</b> {results["failure_mode"]}<br>
            <b>材料组合:</b> 混凝土 {self.concrete_combo.currentText()}, 钢筋 {self.steel_combo.currentText()}<br>
            <b>截面尺寸:</b> {self.width_spin.value()} × {self.height_spin.value()} mm"""
        
        self.result_summary.setText(summary_text)
        
        # 确定要绘制的数据
        if "full_analysis" in results:
            plot_data = results["full_analysis"]
            moment_scale = 1.0  # 已经是 kN·m
        else:
            plot_data = results
            moment_scale = 1e6  # 转换为 kN·m
        
        # 绘制弯矩-曲率曲线
        self.moment_curvature_canvas.axes.clear()
        self.moment_curvature_canvas.axes.plot(
            plot_data["kappas"], 
            [m/moment_scale for m in plot_data["moments"]], 
            'b-'
        )
        self.moment_curvature_canvas.axes.set_title('Moment-Curvature Curve')
        self.moment_curvature_canvas.axes.set_xlabel('Curvature (1/m)')
        self.moment_curvature_canvas.axes.set_ylabel('Moment (kN·m)')
        self.moment_curvature_canvas.axes.grid(True)
        self.moment_curvature_canvas.fig.tight_layout()
        self.moment_curvature_canvas.draw()
        
        # 绘制应变发展曲线
        self.strain_canvas.axes.clear()
        self.strain_canvas.axes.plot(
            plot_data["kappas"], 
            plot_data["max_eps_concrete"], 
            'r-', 
            label='Max Strain (Tension)'
        )
        self.strain_canvas.axes.plot(
            plot_data["kappas"], 
            plot_data["min_eps_concrete"], 
            'g-', 
            label='Min Strain (Compression)'
        )
        if self.analyzer.eps_tu is not None:
            self.strain_canvas.axes.axhline(
                y=self.analyzer.eps_tu, 
                color='r', 
                linestyle='--', 
                label='Concrete Ultimate Tension Strain'
            )
        if self.analyzer.epsu is not None:
            self.strain_canvas.axes.axhline(
                y=-self.analyzer.epsu, 
                color='g', 
                linestyle='--', 
                label='Concrete Ultimate Compression Strain'
            )
        self.strain_canvas.axes.set_title('Concrete Strain Development')
        self.strain_canvas.axes.set_xlabel('Curvature (1/m)')
        self.strain_canvas.axes.set_ylabel('Strain')
        self.strain_canvas.axes.legend()
        self.strain_canvas.axes.grid(True)
        self.strain_canvas.fig.tight_layout()
        self.strain_canvas.draw()
        
        # 绘制中和轴应变曲线
        self.neutral_axis_canvas.axes.clear()
        self.neutral_axis_canvas.axes.plot(
            plot_data["kappas"], 
            plot_data["epsilons0"], 
            'k-'
        )
        self.neutral_axis_canvas.axes.set_title('Neutral Axis Strain Development')
        self.neutral_axis_canvas.axes.set_xlabel('Curvature (1/m)')
        self.neutral_axis_canvas.axes.set_ylabel('Strain')
        self.neutral_axis_canvas.axes.grid(True)
        self.neutral_axis_canvas.fig.tight_layout()
        self.neutral_axis_canvas.draw()
    
    def on_thread_finished(self):
        """线程结束回调函数，恢复UI状态"""
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("开始分析")
    
    def select_config_file(self):
        """选择JSON配置文件"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, 
            "选择不规则截面配置文件", 
            "", 
            "JSON文件 (*.json);;所有文件 (*)"
        )
        if file_path:
            self.config_file_edit.setText(file_path)
    
    def on_section_type_changed(self):
        """截面类型变化处理"""
        section_type = self.section_type_combo.currentData()
        
        if section_type == "irregular":
            # 显示不规则截面控件
            self.config_file_label.setVisible(True)
            self.config_file_edit.setVisible(True)
            # 启用编辑框和浏览按钮，允许用户选择文件
            self.config_file_edit.setEnabled(True)
            self.config_file_button.setVisible(True)
            self.config_file_button.setEnabled(True)
            # 隐藏矩形截面控件
            self.width_label.setVisible(False)
            self.width_spin.setVisible(False)
            self.height_label.setVisible(False)
            self.height_spin.setVisible(False)
            self.top_count_label.setVisible(False)
            self.top_count_spin.setVisible(False)
            self.top_dia_label.setVisible(False)
            self.top_dia_spin.setVisible(False)
            self.top_cover_label.setVisible(False)
            self.top_cover_spin.setVisible(False)
            self.bottom_count_label.setVisible(False)
            self.bottom_count_spin.setVisible(False)
            self.bottom_dia_label.setVisible(False)
            self.bottom_dia_spin.setVisible(False)
            self.bottom_cover_label.setVisible(False)
            self.bottom_cover_spin.setVisible(False)
        else:
            # 隐藏不规则截面控件
            self.config_file_label.setVisible(False)
            self.config_file_edit.setVisible(False)
            # 禁用编辑框和浏览按钮，避免误操作
            self.config_file_edit.setEnabled(False)
            self.config_file_button.setVisible(False)
            self.config_file_button.setEnabled(False)
            # 显示矩形截面控件
            self.width_label.setVisible(True)
            self.width_spin.setVisible(True)
            self.height_label.setVisible(True)
            self.height_spin.setVisible(True)
            self.top_count_label.setVisible(True)
            self.top_count_spin.setVisible(True)
            self.top_dia_label.setVisible(True)
            self.top_dia_spin.setVisible(True)
            self.top_cover_label.setVisible(True)
            self.top_cover_spin.setVisible(True)
            self.bottom_count_label.setVisible(True)
            self.bottom_count_spin.setVisible(True)
            self.bottom_dia_label.setVisible(True)
            self.bottom_dia_spin.setVisible(True)
            self.bottom_cover_label.setVisible(True)
            self.bottom_cover_spin.setVisible(True)
        
        self.update_steel_area()