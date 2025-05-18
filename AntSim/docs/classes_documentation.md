# AntSim 类文档

## 1. Antenna 类（device.py）
- **继承关系**：继承自 PyQt5 的 QTreeWidget
- **信号**：`data_changed = pyqtSignal()`（数据变更时触发）
- **关键方法**：
  - `__init__`：初始化树状控件，设置列头、右键菜单等
  - `add_row`：添加新行（包含类型下拉框、索引SpinBox、滑块等控件）
  - `update_position`：根据索引计算实际位置并更新显示
  - `update_grid_params`：更新网格参数（步长和数量），调整控件范围
  - `get_all_data`：获取所有行数据（类型、索引、值、实际位置）
  - `set_all_data`：用数据列表重置控件内容
- **类间交互**：通过 `data_changed` 信号与 `AntSimData` 类的 `_update_antenna_data` 槽函数连接，同步数据。

## 2. AntSimCalculator 类（antsim_calculator.py）
- **继承关系**：继承自 PyQt5 的 QObject
- **信号**：`calculation_started`、`calculation_progress`、`calculation_complete`、`error_occurred`
- **关键方法**：
  - `__init__`：初始化计算模块，绑定数据源和结果控件
  - `_calculate_unit_abcd_matrix`：计算单位网格的ABCD矩阵
  - `_update_antenna_abcd`：根据天线元件类型（馈电/元件）更新ABCD矩阵
  - `_calculate_voltage_current_distribution`：计算电压电流分布
- **类间交互**：依赖 `AntSimData` 类提供的 `antenna_elements_data`（天线元件数据）和 `grid_array`（网格数组）进行计算。

## 3. AntSimData 类（antsim_data.py）
- **继承关系**：继承自 PyQt5 的 QObject
- **信号**：`data_updated = pyqtSignal()`（数据更新时触发）
- **关键方法**：
  - `__init__`：初始化基础数据（频率、网格、RLGC参数），绑定设置和设备控件
  - `update_freq_array`：根据频率设置更新频率数组
  - `update_grid_array`：根据网格设置更新网格数组和步长
  - `_update_unit_rlgc_params`：计算单位长度和单位网格的RLGC参数
  - `_update_antenna_data`（槽函数）：通过 `Antenna` 控件的 `get_all_data` 方法同步天线数据
- **类间交互**：
  - 从 `Settings` 类获取设置参数（频率、网格、传输线）
  - 向 `Antenna` 控件同步网格参数（`update_grid_params`）
  - 为 `AntSimCalculator` 提供 `antenna_elements_data` 和 `grid_array` 等计算所需数据