from PyQt5 import QtWidgets, QtCore, QtGui
import copy # 导入 copy 模块

class SimulationState:
    """定义仿真状态常量"""
    IDLE = 0      # 待仿真
    RUNNING = 1   # 仿真中
    COMPLETE = 2  # 仿真完成

class SimulationButton(QtCore.QObject):
    """
    管理单个仿真按钮的外观和状态。
    根据仿真状态更改按钮的背景色和文本。
    """
    # 定义默认的状态配置
    DEFAULT_STATE_CONFIG = {
        SimulationState.IDLE: {
            "text": "待计算", # 改为更通用的“待计算”
            "color": "yellow",
            "tooltip": "点击开始计算"
        },
        SimulationState.RUNNING: {
            "text": "计算中", # 改为更通用的“计算中”
            "color": "red",
            "tooltip": "计算正在进行..."
        },
        SimulationState.COMPLETE: {
            "text": "计算完成", # 改为更通用的“计算完成”
            "color": "lightgreen",
            "tooltip": "计算已完成"
        }
    }

    def __init__(self, button: QtWidgets.QPushButton, state_config_override: dict = None, parent=None):
        """
        初始化 SimulationButton。

        Args:
            button (QtWidgets.QPushButton): 需要管理的 QPushButton 实例。
            state_config_override (dict, optional): 用于覆盖默认状态文本和提示的字典。
                                                    结构应与 DEFAULT_STATE_CONFIG 类似，
                                                    例如 {SimulationState.IDLE: {"text": "计算频率点"}, ...}。
                                                    Defaults to None.
            parent (QObject, optional): 父对象. Defaults to None.
        """
        super().__init__(parent)
        if not isinstance(button, QtWidgets.QPushButton):
            raise TypeError("传入的 button 必须是 QPushButton 实例")
        self.button = button
        self._state = SimulationState.IDLE # 初始状态

        # --- 修改：合并默认配置和覆盖配置 ---
        self.state_config = copy.deepcopy(self.DEFAULT_STATE_CONFIG) # 深拷贝默认配置
        if state_config_override:
            for state, overrides in state_config_override.items():
                if state in self.state_config:
                    # 只更新 state_config_override 中提供的键
                    for key, value in overrides.items():
                         if key in self.state_config[state]:
                              self.state_config[state][key] = value
        # --- 修改结束 ---

        self.set_state(self._state) # 应用初始状态

    def set_state(self, state):
        """
        设置按钮的状态并更新外观。

        Args:
            state (int): SimulationState 中的状态常量 (IDLE, RUNNING, COMPLETE)。
        """
        # --- 修改：使用 self.state_config ---
        if state not in self.state_config:
            print(f"警告：未知的仿真状态 {state}")
            return

        self._state = state
        config = self.state_config[state]
        # --- 修改结束 ---

        # 更新按钮文本
        self.button.setText(config["text"])

        # 更新按钮背景色 (使用样式表)
        style = f"QPushButton {{ background-color: {config['color']}; }}"
        self.button.setStyleSheet(style)

        # 更新工具提示
        self.button.setToolTip(config["tooltip"])

        # 根据状态启用/禁用按钮 (例如，仿真中时禁用)
        # 注意：如果两个按钮可能同时运行不同的计算，这里的禁用逻辑可能需要调整
        # 目前假设同一时间只有一个计算在运行
        self.button.setEnabled(state != SimulationState.RUNNING)

    def get_state(self):
        """获取当前按钮状态"""
        return self._state

    # --- 槽函数保持不变，但需要连接到 Calculator 中更具体的信号 ---
    # --- 例如，Calculator 可能需要发出 sweep_started, sweep_complete, single_freq_started 等信号 ---

    @QtCore.pyqtSlot()
    def on_calculation_started(self):
        """响应计算开始的槽函数 (通用)"""
        self.set_state(SimulationState.RUNNING)

    # 这个槽可能需要区分是哪个计算完成的，或者 Calculator 发出更具体的信号
    @QtCore.pyqtSlot() # 假设 Calculator 发出不带参数的完成信号
    def on_calculation_complete(self):
        """响应计算完成的槽函数 (通用)"""
        self.set_state(SimulationState.COMPLETE)

    # 这个槽也可能需要区分错误来源
    @QtCore.pyqtSlot(str) # 参数类型匹配 Calculator 的 error 信号
    def on_calculation_error(self, error_message):
        """响应计算错误的槽函数 (通用)"""
        self.set_state(SimulationState.IDLE)
        # 使用配置中的 IDLE tooltip 作为基础
        base_tooltip = self.state_config[SimulationState.IDLE].get("tooltip", "点击开始计算")
        error_tooltip = f"计算出错: {error_message}\n{base_tooltip}"
        self.button.setToolTip(error_tooltip)

    def reset(self):
        """将按钮重置回初始待计算状态"""
        self.set_state(SimulationState.IDLE)