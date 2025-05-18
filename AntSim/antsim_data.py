import numpy as np
from PyQt5 import QtCore
from settings import Settings # 假设 Settings 在同一目录下或可访问
from device import Antenna # 假设 Antenna 在 device.py 中

class AntSimData(QtCore.QObject): # 继承 QObject 以使用信号
    """
    管理基础数据，与 UI 设置绑定。
    包括频率数组、网格数组、单位 RLGC 参数和天线数据。
    """
    # 定义信号，当数据更新时发射
    data_updated = QtCore.pyqtSignal()

    def __init__(self, settings_instance, device, parent=None):
        super().__init__(parent) # 调用父类构造函数
        self.settings_instance = settings_instance
        self.device = device # 存储传入的 Antenna 控件实例

        # 初始化核心数据结构
        self.freq_array = np.array([]) # 频率数组 (Hz)
        self.grid_array = np.array([]) # 网格位置数组 (m)
        self.grid_step = 0.0           # 网格步长 (m)
        self.antenna_elements_data = [] # 存储提取的 Antenna 数据
        self.current_line_settings = self.settings_instance.line_settings.copy()
        self.unit_R = 0.0 # Ohm/m
        self.unit_L = 0.0 # H/m
        self.unit_G = 0.0 # S/m
        self.unit_C = 0.0 # F/m
        self.R_per_step = 0.0 # Ohm
        self.L_per_step = 0.0 # H
        self.G_per_step = 0.0 # S
        self.C_per_step = 0.0 # F

        # 连接 Settings 信号
        self.settings_instance.line_changed.connect(self._on_line_settings_changed)
        self.settings_instance.grid_changed.connect(self._on_grid_settings_changed) # 分开处理 grid 变化
        self.settings_instance.frequency_changed.connect(self._on_freq_settings_changed) # 分开处理 freq 变化

        # --- 添加连接 Antenna 控件的信号 ---
        if isinstance(self.device, Antenna):
            self.device.data_changed.connect(self._update_antenna_data) # 连接信号到槽
        # --- 连接结束 ---

        # 初始更新
        self.update_all_data()

    @QtCore.pyqtSlot(dict)
    def _on_line_settings_changed(self, line_settings_dict):
        """处理传输线设置更改信号"""
        print("检测到传输线设置更改，更新内部存储...")
        self.current_line_settings = line_settings_dict
        # 仅更新依赖传输线设置的数据
        self._update_unit_rlgc_params()
        print("基础数据更新完成 (line settings)。")
        self.data_updated.emit() # 发射信号

    @QtCore.pyqtSlot(dict) # 修改为接收 dict
    def _on_grid_settings_changed(self, grid_settings_dict): # 修改为接收 dict
        """处理网格设置更改信号"""
        print("检测到网格设置更改，正在更新网格和相关数据...")
        # 更新网格数组和步长，这会触发 RLGC per step 更新
        self.update_grid_array()
        # 通知 Antenna 控件更新其内部参数 (如 spinbox/slider 范围)
        if isinstance(self.device, Antenna):
             try:
                 grid_step = float(grid_settings_dict.get('grid_step', self.grid_step)) # 使用新值或当前值
                 grid_count = int(grid_settings_dict.get('grid_count', len(self.grid_array))) # 使用新值或当前值
                 self.device.update_grid_params(grid_step, grid_count)
             except (ValueError, TypeError) as e:
                 print(f"更新 Antenna 控件网格参数时出错: {e}")
        print("基础数据更新完成 (grid settings)。")
        self.data_updated.emit() # 发射信号

    @QtCore.pyqtSlot(dict) # 修改为接收 dict
    def _on_freq_settings_changed(self, freq_settings_dict): # 修改为接收 dict
        """处理频率设置更改信号"""
        print("检测到频率设置更改，正在更新频率数据...")
        self.update_freq_array()
        print("基础数据更新完成 (frequency settings)。")
        self.data_updated.emit() # 发射信号


    def update_all_data(self):
        """更新所有基础数据并发出信号 (通常在初始化时调用)"""
        self.update_freq_array()
        self.update_grid_array() # 会触发 _update_unit_rlgc_params
        self._update_antenna_data() # 读取 Antenna 控件数据
        # 初始时也需要更新 Antenna 控件的网格参数
        if isinstance(self.device, Antenna):
             grid_settings = self.settings_instance._read_settings_from_tree("网格设置")
             try:
                 grid_step = float(grid_settings.get('grid_step', self.grid_step))
                 grid_count = int(grid_settings.get('grid_count', len(self.grid_array)))
                 self.device.update_grid_params(grid_step, grid_count)
             except (ValueError, TypeError) as e:
                 print(f"初始化时更新 Antenna 控件网格参数出错: {e}")

        print("所有基础数据初始更新完成。")
        self.data_updated.emit() # 发射信号

    def update_freq_array(self):
        """根据频率设置更新频率数组"""
        try:
            freq_settings = self.settings_instance._read_settings_from_tree("频率设置")
            start_freq = float(freq_settings.get('start_freq', 0)) * 1e6 # 转 Hz
            end_freq = float(freq_settings.get('end_freq', 0)) * 1e6 # 转 Hz
            freq_count = int(freq_settings.get('freq_count', 0))
            # print(f"更新频率数组：起始={start_freq} Hz, 终止={end_freq} Hz, 点数={freq_count}")
            if freq_count > 1:
                self.freq_array = np.linspace(start_freq, end_freq, freq_count)
            elif freq_count == 1:
                self.freq_array = np.array([start_freq])
            else:
                self.freq_array = np.array([])
        except (ValueError, KeyError, TypeError) as e:
                print(f"更新频率数组错误: {e}")
                self.freq_array = np.array([])

    def update_grid_array(self):
        """根据网格设置更新网格数组和网格步长，并触发 RLGC 更新"""
        try:
            grid_settings = self.settings_instance._read_settings_from_tree("网格设置")
            # 将 antenna_length 从 mm 转换为 m
            antenna_length = float(grid_settings.get('antenna_length', 0)) / 1000
            grid_count = int(grid_settings.get('grid_count', 0))
            if grid_count > 1:
                self.grid_array = np.linspace(0, antenna_length, grid_count)
                self.grid_step = antenna_length / (grid_count - 1) if grid_count > 1 else 0
            elif grid_count == 1:
                 self.grid_array = np.array([0])
                 self.grid_step = 0 # 单点网格步长为 0
            else:
                 self.grid_array = np.array([])
                 self.grid_step = 0
            # print(f"网格步长更新为: {self.grid_step}")

            self._update_unit_rlgc_params() # 更新依赖 grid_step 的参数

        except (ValueError, KeyError, TypeError, ZeroDivisionError) as e: # 添加 ZeroDivisionError
            print(f"更新网格数组错误: {e}")
            self.grid_array = np.array([])
            self.grid_step = 0
            self._update_unit_rlgc_params() # 即使出错也要尝试更新 RLGC (可能为 0)

    def _update_unit_rlgc_params(self):
        """根据传输线设置更新单位长度 RLGC，然后计算单位网格 RLGC"""
        # print("正在更新单位长度和单位网格 RLGC 参数...")
        line_settings = self.current_line_settings
        try:
            # 将 unit_R 和 unit_G 从 mm 转换为 m
            self.unit_R = float(line_settings.get('unit_R', 0)) * 1000  # Ohm/m
            self.unit_G = float(line_settings.get('unit_G', 0)) * 1000# S/m
            # 修改 ref_freq 为 GHz 单位
            ref_freq_GHz = float(line_settings.get('ref_freq', 100)) # GHz
            # 将 ref_wavelength 从 mm 转换为 m
            ref_wavelength_quarter = float(line_settings.get('ref_wavelength', 0.75)) / 1000 # m

            f_ref = ref_freq_GHz * 1e9 # Hz，直接乘以 1e9 转换为 Hz
            lambda_full = 4 * ref_wavelength_quarter # m
            v = 3e8 # Default speed of light (m/s)
            if f_ref != 0 and lambda_full != 0:
                 v = f_ref * lambda_full
            if v == 0: v = 3e8 # Fallback

            self.unit_L = 0.0
            self.unit_C = 0.0
            Z0 = float(line_settings.get('characteristic_impedance', 50)) # Ohm 补充 Z0 的获取
            if v != 0 and Z0 != 0:
                self.unit_L = Z0 / v       # H/m
                self.unit_C = 1 / (v * Z0) # F/m

            self.R_per_step = self.unit_R * self.grid_step # Ohm
            self.G_per_step = self.unit_G * self.grid_step # S
            self.L_per_step = self.unit_L * self.grid_step # H
            self.C_per_step = self.unit_C * self.grid_step # F

            # 将电感转换为纳亨，电容转换为皮法
            L_per_step_nh = self.L_per_step * 1e9
            C_per_step_pf = self.C_per_step * 1e12

            print(f"单位网格 RLGC: R={self.R_per_step}, L={L_per_step_nh} nH, G={self.G_per_step}, C={C_per_step_pf} pF")

        except (ValueError, ZeroDivisionError, TypeError, KeyError) as e:
            print(f"计算单位 RLGC 时出错: {e}")
            self.unit_R = self.unit_L = self.unit_G = self.unit_C = 0.0
            self.R_per_step = self.L_per_step = self.G_per_step = self.C_per_step = 0.0

    # --- 修改 _update_antenna_data 为槽函数 ---
    @QtCore.pyqtSlot() # 标记为槽
    def _update_antenna_data(self):
        """更新内部存储的 Antenna 元件数据 (现在是槽函数)"""
        print("正在更新 Antenna 数据 (槽函数)...")
        # 使用 Antenna 控件提供的方法获取数据
        if isinstance(self.device, Antenna):
             self.antenna_elements_data = self.device.get_all_data() # 使用新方法
        else:
             self.antenna_elements_data = self.get_antenna_data_fallback() # 保留旧逻辑作为后备

        print(f"Antenna 数据已更新: {self.antenna_elements_data}")
        self.data_updated.emit() # 发射信号表明数据已更新

    def get_antenna_data_fallback(self):
        """从绑定的 device (Antenna QTreeWidget) 提取数据 (旧逻辑，作为后备)"""
        data = []
        if not isinstance(self.device, Antenna): # 检查类型
            print("错误：AntSimData 未正确绑定 Antenna 控件。")
            return data
        try:
            for i in range(self.device.topLevelItemCount()):
                item = self.device.topLevelItem(i)
                if not item: continue

                combo_widget = self.device.itemWidget(item, 0) # 类型列
                type_val = combo_widget.currentText() if combo_widget else "N/A"

                spin_widget = self.device.itemWidget(item, 2) # 索引列
                index_val = spin_widget.value() if spin_widget else None

                line_edit_widget = self.device.itemWidget(item, 4) # 值列
                value_val = line_edit_widget.text() if line_edit_widget else ""

                data.append({'类型': type_val, '索引': index_val, '值': value_val})
        except Exception as e:
            print(f"从 Antenna 控件提取数据时出错 (fallback): {e}")
        return data

    # --- Getter 方法 ---
    def get_freq_array(self):
        return self.freq_array

    def get_grid_array(self):
        return self.grid_array

    def get_grid_step(self):
        return self.grid_step

    def get_unit_rlgc_per_step(self):
        return self.R_per_step, self.L_per_step, self.G_per_step, self.C_per_step

    def get_antenna_elements_data(self):
        # 返回内部存储的数据，而不是每次都重新读取
        return self.antenna_elements_data