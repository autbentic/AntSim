import numpy as np
import cmath
import math
from PyQt5 import QtCore, QtWidgets # 添加 QtWidgets 导入
from antsim_data import AntSimData # 导入基础数据类
# 修改相对导入为绝对导入
from calculation import ElementCalculation, FeedCalculation
from result_plot import ResultPlot

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

class AntSimCalculator(QtCore.QObject):
    """
    执行核心计算，使用来自 AntSimData 的数据。
    计算 ABCD 矩阵、电压/电流分布。
    """
    calculation_started = QtCore.pyqtSignal()
    calculation_progress = QtCore.pyqtSignal(int) # 报告进度 (0-100)
    calculation_complete = QtCore.pyqtSignal(object, object, object, object) # 发射结果 (V, I, Zin, Gamma)
    error_occurred = QtCore.pyqtSignal(str) # 报告错误信息

    def __init__(self, data_source: AntSimData, result_widget=None, parent=None):
        super().__init__(parent)
        self.data_source = data_source
        self.result_widget = result_widget
        self.current_plot_canvas = None
        self.current_plot_ax = None

        # 存储单频点计算结果
        self.single_freq_voltage_matrix = None
        self.single_freq_current_matrix = None
        # 存储频率扫描计算结果
        self.sweep_voltage_matrix = None
        self.sweep_current_matrix = None
        self.input_impedance_array = None # (频率数)
        self.reflection_coefficient_array = None # (频率数)
        self.load_impedance = 50 + 0j # 默认或从数据中设置

        # 内部状态
        self._antenna_abcd_matrices = {} # 存储当前频率的 Antenna ABCD
        self._abcd_matrix_complete = None # 存储当前频率的完整 ABCD

        # 连接数据源的更新信号，以便在数据变化时可以触发重新计算（如果需要自动）
        # self.data_source.data_updated.connect(self.run_frequency_sweep) # 例如：数据变了就自动重算

    def _calculate_unit_abcd_matrix(self, current_frequency):
        """根据存储的单位网格 RLGC 和当前频率计算单位网格的 ABCD 矩阵"""
        R, L, G, C = self.data_source.get_unit_rlgc_per_step()
        try:
            # 假设 current_frequency 单位是 GHz，需要转换为 Hz
            current_frequency_hz = current_frequency * 1e9  
            omega = 2 * math.pi * current_frequency_hz
            Z = R + 1j * omega * L
            Y = G + 1j * omega * C
            gamma = cmath.sqrt(Z * Y)
            Zc = float('inf') + 0j
            if Y != 0:
                try: Zc = cmath.sqrt(Z / Y)
                except ZeroDivisionError: pass
    
            cosh_gamma = cmath.cosh(gamma)
            sinh_gamma = cmath.sinh(gamma)
            A = D = cosh_gamma
            C_abcd = 0 + 0j
            if Zc != 0 and not cmath.isinf(Zc): C_abcd = (1 / Zc) * sinh_gamma
            B = Zc * sinh_gamma
            abcd_matrix = np.array([[A, B], [C_abcd, D]], dtype=complex)
            
            # 新增打印语句
            print(f"频率 {current_frequency} GHz 的单位 ABCD 矩阵值为:\n{abcd_matrix}")
            
            return abcd_matrix
        except (ValueError, ZeroDivisionError, TypeError) as e:
            msg = f"计算频率 {current_frequency} GHz 的单位 ABCD 矩阵时出错: {e}"
            print(msg)
            self.error_occurred.emit(msg)
            return np.identity(2, dtype=complex)

    def _update_antenna_abcd(self, freq):
        # 假设 freq 单位是 GHz，已经正确传递给 ElementCalculation 和 FeedCalculation
        antenna_elements = self.data_source.antenna_elements_data
        self._antenna_abcd_matrices = {}
    
        if self._abcd_matrix_complete is None:
            print("错误: _abcd_matrix_complete 为 None，无法更新天线 ABCD 矩阵。")
            self.error_occurred.emit("错误: _abcd_matrix_complete 为 None，无法更新天线 ABCD 矩阵。")
            return
    
        for index, element in enumerate(antenna_elements):
            element_type = element['类型']
            element_str = element['值']
    
            try:
                if element_type == '元件':
                    abcd_matrix_4x1 = ElementCalculation(element_str, freq)  # 假设 freq 单位是 GHz
                elif element_type == '馈电':
                    abcd_matrix_4x1 = FeedCalculation(element_str, freq)  # 假设 freq 单位是 GHz
                else:
                    print(f"未知的元件类型: {element_type}")
                    self.error_occurred.emit(f"未知的元件类型: {element_type}")
                    continue
    
                # 将 4x1 矩阵转换为 2x2 矩阵
                if isinstance(abcd_matrix_4x1, np.ndarray) and abcd_matrix_4x1.shape == (4, 1):
                    abcd_matrix_2x2 = np.array([[abcd_matrix_4x1[0, 0], abcd_matrix_4x1[1, 0]], [abcd_matrix_4x1[2, 0], abcd_matrix_4x1[3, 0]]], dtype=complex)
                else:
                    abcd_matrix_2x2 = abcd_matrix_4x1
    
                if 0 <= index < len(self._abcd_matrix_complete):
                    self._abcd_matrix_complete[index] = abcd_matrix_2x2
                else:
                    print(f"索引 {index} 超出 _abcd_matrix_complete 的范围，跳过此赋值。")
                    self.error_occurred.emit(f"索引 {index} 超出 _abcd_matrix_complete 的范围，跳过此赋值。")
    
            except Exception as e:
                print(f"计算 {element_type} {index} 的 ABCD 矩阵时出错: {e}")
                self.error_occurred.emit(f"计算 {element_type} {index} 的 ABCD 矩阵时出错: {e}")

    def _update_complete_abcd(self, freq):
        # 获取网格数组
        grid_array = self.data_source.get_grid_array()
        num_grids = len(grid_array)
        
        # 先调用 _calculate_unit_abcd_matrix 计算传输线的 abcd 矩阵
        unit_abcd_matrix = self._calculate_unit_abcd_matrix(freq)
        
        # 用这个矩阵给完成 abcd 矩阵的所有节点都附上这个值
        # 初始化一个长度为网格点数的列表，每个元素是单位 ABCD 矩阵
        self._abcd_matrix_complete = [unit_abcd_matrix] * num_grids
        
        # 再调用 _update_antenna_abcd 函数，给 antenna 节点附上相应的 abcd 矩阵值
        self._update_antenna_abcd(freq)

    def _calculate_voltage_current_distribution(self, freq_index, current_frequency, is_single_freq=False):
        self._update_complete_abcd(current_frequency)
        # 1. 先检查 antenna 数据，看有几个类型为馈电的
        antenna_elements = self.data_source.antenna_elements_data
        feed_points = [element for element in antenna_elements if element['类型'] == '馈电']
        num_feeds = len(feed_points)
        grid_array = self.data_source.get_grid_array()
        num_grids = len(grid_array)
    
        if num_grids < 1:
            return  # 至少需要一个点
    
        all_voltages = []
        all_currents = []
    
        # 3. 遍历 antenna 中为馈电类型的节点
        for feed_point in feed_points:
            feed_index = feed_point.get('索引')
            if feed_index is None or feed_index < 0 or feed_index >= num_grids:
                print(f"馈电节点索引 {feed_index} 无效，跳过此馈电点。")
                continue
    
            # 初始化边界条件矩阵
            voltage_boundary = np.zeros((num_grids + 2), dtype=complex)
            current_boundary = np.ones((num_grids + 2), dtype=complex)
    
            # 从左边界向馈电点计算
            for i in range(1, feed_index + 2):
                if i > 1:
                    abcd_matrix = self._abcd_matrix_complete[i - 2]
                    # 检查 abcd_matrix 的形状
                    if abcd_matrix.shape[0] >= 1 and abcd_matrix.shape[1] >= 2:
                        V_prev = voltage_boundary[i - 1]
                        I_prev = current_boundary[i - 1]
                        V = abcd_matrix[0, 0] * V_prev + abcd_matrix[0, 1] * I_prev
                        I = abcd_matrix[1, 0] * V_prev + abcd_matrix[1, 1] * I_prev
                        voltage_boundary[i] = V
                        current_boundary[i] = I
                    else:
                        print(f"abcd_matrix 形状不符合预期: {abcd_matrix.shape}，跳过此计算步骤。")
    
            # 从右边界向馈电点计算
            for i in range(num_grids + 1, feed_index + 1, -1):
                if i < num_grids + 1:
                    abcd_matrix = self._abcd_matrix_complete[i - 1]
                    # 检查 abcd_matrix 的形状
                    if abcd_matrix.shape[0] >= 1 and abcd_matrix.shape[1] >= 2:
                        V_next = voltage_boundary[i + 1]
                        I_next = current_boundary[i + 1]
                        inv_abcd = np.linalg.inv(abcd_matrix)
                        V = inv_abcd[0, 0] * V_next + inv_abcd[0, 1] * I_next
                        I = inv_abcd[1, 0] * V_next + inv_abcd[1, 1] * I_next
                        voltage_boundary[i] = V
                        current_boundary[i] = I
                    else:
                        print(f"abcd_matrix 形状不符合预期: {abcd_matrix.shape}，跳过此计算步骤。")
    
            left_voltage = voltage_boundary[feed_index + 1]
            right_voltage = voltage_boundary[feed_index + 2]
            if right_voltage != 0:
                factor = left_voltage / right_voltage
                voltage_boundary[feed_index + 2:] *= factor
                current_boundary[feed_index + 2:] *= factor
    
            current_boundary[feed_index + 1] = (
                current_boundary[feed_index] + current_boundary[feed_index + 2]
            )
    
            all_voltages.append(voltage_boundary[1:-1])
            all_currents.append(current_boundary[1:-1])
    
        if all_voltages and all_currents:
            if is_single_freq:
                self.single_freq_voltage_matrix = np.array(all_voltages).T
            self.single_freq_current_matrix = np.array(all_currents).T
            print(f"单频点电流矩阵（频率{current_frequency} GHz）: {self.single_freq_current_matrix}")
            if is_single_freq is False:  # 检查是否不是单频点计算
                self.sweep_voltage_matrix[freq_index, :, :len(all_voltages)] = np.array(all_voltages).T
                self.sweep_current_matrix[freq_index, :, :len(all_currents)] = np.array(all_currents).T
                print(f"频率扫描点{freq_index}（频率{current_frequency} GHz）电流矩阵: {self.sweep_current_matrix[freq_index, :, :len(all_currents)]}")

    def run_frequency_sweep(self):
        """执行整个频率扫描计算"""
        self.calculation_started.emit()
        print("开始频率扫描计算...")

        freq_array = self.data_source.get_freq_array()
        grid_array = self.data_source.get_grid_array()
        num_freqs = len(freq_array)
        num_grids = len(grid_array)
        antenna_elements = self.data_source.antenna_elements_data
        feed_points = [element for element in antenna_elements if element['类型'] == '馈电']
        num_feeds = len(feed_points)

        if num_freqs == 0 or num_grids == 0:
            msg = "频率点或网格点数量为零，无法计算。"
            print(msg)
            self.error_occurred.emit(msg)
            self.calculation_complete.emit(None, None, None, None) # 发射空结果
            return

        # 初始化频率扫描结果矩阵
        self.sweep_voltage_matrix = np.zeros((num_freqs, num_grids, num_feeds), dtype=complex)
        self.sweep_current_matrix = np.zeros((num_freqs, num_grids, num_feeds), dtype=complex)

        total_calculations = num_freqs
        for i, freq in enumerate(freq_array):
            print(f"\n--- 计算频率: {freq * 1000:.2f} MHz ({i+1}/{num_freqs}) ---")
            self._update_complete_abcd(freq)
            self._calculate_voltage_current_distribution(i, freq)

            # 报告进度
            progress = int(((i + 1) / total_calculations) * 100)
            self.calculation_progress.emit(progress)

        print("\n频率扫描计算完成。")
        self.calculation_complete.emit(
            self.sweep_voltage_matrix,
            self.sweep_current_matrix,
            self.input_impedance_array,
            self.reflection_coefficient_array
        )

    def calculate_single_frequency(self, freq):
        """执行单频点计算"""
        grid_array = self.data_source.get_grid_array()
        num_grids = len(grid_array)
        antenna_elements = self.data_source.antenna_elements_data
        feed_points = [element for element in antenna_elements if element['类型'] == '馈电']
        num_feeds = len(feed_points)

        if num_grids < 1:
            msg = "网格点数量为零，无法计算。"
            print(msg)
            self.error_occurred.emit(msg)
            return

        # 初始化单频点结果矩阵
        self.single_freq_voltage_matrix = np.zeros((num_grids, num_feeds), dtype=complex)
        self.single_freq_current_matrix = np.zeros((num_grids, num_feeds), dtype=complex)

        print(f"\n--- 计算频率: {freq * 1000:.2f} MHz ---")
        self._calculate_voltage_current_distribution(0, freq, is_single_freq=True)

        print("\n单频点计算完成。")
        self.calculation_complete.emit(
            self.single_freq_voltage_matrix,
            self.single_freq_current_matrix,
            None,
            None
        )

        
   

    # --- Getter 方法，用于获取计算结果 ---
    def get_single_freq_voltage_matrix(self):
        return self.single_freq_voltage_matrix

    def get_single_freq_current_matrix(self):
        return self.single_freq_current_matrix

    def get_sweep_voltage_matrix(self):
        return self.sweep_voltage_matrix

    def get_sweep_current_matrix(self):
        return self.sweep_current_matrix

    def get_input_impedance_array(self):
        return self.input_impedance_array

    def get_reflection_coefficient_array(self):
        return self.reflection_coefficient_array
