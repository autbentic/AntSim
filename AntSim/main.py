from PyQt5 import QtWidgets, uic
import sys
import settings
from antsim_data import AntSimData
from antsim_calculator import AntSimCalculator # <--- 导入 Calculator
from result_plot import ResultPlot
from device import Antenna
from simulation_button import SimulationButton, SimulationState # <--- 导入 SimulationButton
import numpy as np

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi('AntSim.ui', self)

        # 初始化Setting控件的默认值
        setting_tree = self.findChild(QtWidgets.QTreeWidget, 'Setting')
        settings_instance = settings.Settings.init_settings(setting_tree)
        self.antenna_widget = Antenna(self)
        antenna_layout = self.findChild(QtWidgets.QVBoxLayout, 'verticalLayout_2')
        old_antenna = self.findChild(QtWidgets.QTableWidget, 'Antenna')
        if old_antenna:
            antenna_layout.replaceWidget(old_antenna, self.antenna_widget)
            old_antenna.deleteLater()
        else:
             antenna_layout.addWidget(self.antenna_widget)
        # 确保 settings_instance 中的参数单位是 GHz、mm、欧姆/mm、S/mm 等
        self.ant_sim_data = AntSimData(settings_instance, self.antenna_widget)


        # --- 实例化 Calculator ---
        # 删除实例化 Presenter 的代码
        # 查找 Result 控件
        self.result_widget = self.findChild(QtWidgets.QTabWidget, 'Result')
        # 查找 Current 控件
        self.current_widget = self.findChild(QtWidgets.QFrame, 'Current')

        # 实例化 Calculator 时传入 Result 控件
        self.calculator = AntSimCalculator(self.ant_sim_data, self.result_widget)
        self.result_plot = ResultPlot(self.calculator, self.result_widget)
        # 初始化 Presenter 时传入 Current 控件相关信息
        # --- 查找 UI 控件 ---

        # --- 修改：查找两个按钮 ---
        sim_fre_button_widget = self.findChild(QtWidgets.QPushButton, 'SimFre') # 查找 SimFre 按钮
        sim_sweep_button_widget = self.findChild(QtWidgets.QPushButton, 'SimFreSweep') # 查找 SimSweep 按钮
        # 检查按钮是否成功找到
        if not sim_fre_button_widget or not sim_sweep_button_widget:
            error_msg = "未能找到所有必要的按钮，请检查 UI 文件中的 objectName。"
            if not sim_fre_button_widget:
                error_msg += " 未找到 'SimFre' 按钮。"
            if not sim_sweep_button_widget:
                error_msg += " 未找到 'SimFreSweep' 按钮。"
            QtWidgets.QMessageBox.critical(self, "错误", error_msg)
            return
        # --- 修改结束 ---

        # 检查是否所有必要的 UI 控件都找到了
        # --- 修改：检查两个按钮 ---
        # if not all([impedance_chart_widget, vswr_chart_widget, distribution_chart_widget,
        #             status_label_widget, progress_bar_widget, result_summary_label_widget,
        #             sim_fre_button_widget, sim_sweep_button_widget]): # 检查两个按钮
        #     QtWidgets.QMessageBox.critical(self, "错误", "未能找到所有必要的 UI 控件，请检查 UI 文件中的 objectName。")
            # 可以选择退出或禁用功能
            # sys.exit(1) # 或者 return
        # --- 修改结束 ---

        # --- 注释掉结果显示相关代码 ---
        # ui_elements = {
        #     'impedance_chart': impedance_chart_widget,
        #     'vswr_chart': vswr_chart_widget,
        #     'distribution_chart': distribution_chart_widget,
        #     'status_label': status_label_widget,
        #     'progress_bar': progress_bar_widget,
        #     'result_summary_label': result_summary_label_widget
        # }
        # self.presenter = AntSimResultPresenter(self.calculator, ui_elements) # 取消注释
        # --- 注释结束 ---
        # --- 实例化结束 ---

        # --- 实例化并设置 SimulationButton ---
        # --- 添加：实例化两个按钮管理器 ---
        # SimFre 按钮的配置
        fre_config = {
            SimulationState.IDLE: {"text": "计算频率点", "tooltip": "计算当前设置的频率"},
            SimulationState.RUNNING: {"text": "计算中...", "tooltip": "正在计算当前频率..."},
            SimulationState.COMPLETE: {"text": "频率点完成", "tooltip": "当前频率计算完成"}
        }
        self.sim_fre_button_manager = SimulationButton(sim_fre_button_widget, fre_config)

        # SimSweep 按钮的配置
        sweep_config = {
            SimulationState.IDLE: {"text": "扫描频率", "tooltip": "开始频率扫描"},
            SimulationState.RUNNING: {"text": "扫描中...", "tooltip": "频率扫描正在进行..."},
            SimulationState.COMPLETE: {"text": "扫描完成", "tooltip": "频率扫描已完成"}
        }
        self.sim_sweep_button_manager = SimulationButton(sim_sweep_button_widget, sweep_config)
        # --- 添加结束 ---
        # self.sim_button_manager = SimulationButton(simulation_button_widget) # 移除旧的单按钮管理器实例化


        # --- 连接计算器信号到 SimulationButton ---
        # --- 修改：连接到两个管理器，并假设 Calculator 有更具体的信号 ---
        # 连接 Calculator 信号到 SimFre 按钮管理器 (需要 Calculator 实现这些信号)
        # self.calculator.single_freq_started.connect(self.sim_fre_button_manager.on_calculation_started)
        # self.calculator.single_freq_complete.connect(self.sim_fre_button_manager.on_calculation_complete)
        # self.calculator.single_freq_error.connect(self.sim_fre_button_manager.on_calculation_error)

        # 连接 Calculator 信号到 SimSweep 按钮管理器 (需要 Calculator 实现这些信号)
        # self.calculator.sweep_started.connect(self.sim_sweep_button_manager.on_calculation_started)
        # self.calculator.sweep_complete.connect(self.sim_sweep_button_manager.on_calculation_complete)
        # self.calculator.sweep_error.connect(self.sim_sweep_button_manager.on_calculation_error)

        # 暂时使用通用信号连接，后续需要 Calculator 提供更具体的信号
        self.calculator.calculation_started.connect(self.sim_fre_button_manager.on_calculation_started) # 示例：连接到 fre
        self.calculator.calculation_complete.connect(self.sim_fre_button_manager.on_calculation_complete) # 示例：连接到 fre
        self.calculator.error_occurred.connect(self.sim_fre_button_manager.on_calculation_error) # 示例：连接到 fre
        # 你需要决定通用信号应该控制哪个按钮，或者修改 Calculator

        # 当数据更新时，重置两个按钮的状态
        self.ant_sim_data.data_updated.connect(self.sim_fre_button_manager.reset)
        self.ant_sim_data.data_updated.connect(self.sim_sweep_button_manager.reset)
        # --- 修改结束 ---


        # --- 连接仿真按钮点击事件 ---
        # --- 修改：连接两个按钮到 Calculator 的不同方法 ---
        # 点击 SimFre 按钮时，触发单频计算 (假设方法名为 run_single_frequency)
        sim_fre_button_widget.clicked.connect(lambda: (
            print(f"当前单频计算频率: {settings_instance.get_current_freq() * 1000:.2f} MHz"),
            self.calculator.calculate_single_frequency(settings_instance.get_current_freq()),
            self.result_plot.update_single_freq_curve()
        ))

        # 点击 SimSweep 按钮时，触发频率扫描
        sim_sweep_button_widget.clicked.connect(lambda: (
            print(f"当前频率扫描起始频率: {self.data_source.get_freq_array()[0] / 1e6:.2f} MHz"),
            print(f"当前频率扫描结束频率: {self.data_source.get_freq_array()[-1] / 1e6:.2f} MHz"),
            self.calculator.run_frequency_sweep()
        ))
        # --- 修改结束 ---
        # simulation_button_widget.clicked.connect(self.calculator.run_frequency_sweep) # 移除旧的连接


        self.show()



if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    # 尝试导入 pyqtgraph，如果失败则提示
    #try:
    #    import pyqtgraph as pg
        # 可以设置一些全局选项
        # pg.setConfigOption('background', 'w')
        # pg.setConfigOption('foreground', 'k')
    #except ImportError:
    #    QtWidgets.QMessageBox.warning(None, "缺少库", "需要安装 pyqtgraph 库才能显示图表。\n请运行: pip install pyqtgraph")
         # 可以选择退出
         # sys.exit(1)

    window = MainWindow()
    sys.exit(app.exec_())


if self.result_widget:
    current_widget = self.result_widget.findChild(QtWidgets.QFrame, 'Current')
    if current_widget:
        grid_array = self.data_source.get_grid_array()
        # 确保传入复数形式的电流数据
        current_array_complex = self.single_freq_current_matrix[:, 0]  
        self.plot_current_curve(current_widget, grid_array, current_array_complex)


    