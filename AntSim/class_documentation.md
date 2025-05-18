# 类文档

## main.py

### MainWindow
- **描述**：主窗口类，继承自 `QtWidgets.QMainWindow`，负责初始化界面和各个组件，并处理用户交互。
- **关键函数**：
  - `__init__()`: 初始化主窗口，加载 UI 文件，初始化各种控件和实例，连接信号和槽。

### 类相互关系
- `MainWindow` 实例化了 `Antenna`、`AntSimData`、`AntSimCalculator`、`SimulationButton` 等类。
- `AntSimCalculator` 的信号连接到 `SimulationButton` 实例的方法，用于更新按钮状态。

## circuit.py

### SeriesCircuit
- **描述**：串联电路类，用于计算串联电路的 ABCD 矩阵。
- **关键函数**：
  - `__init__(self, circuit_str: str, frequency_ghz: Union[float, List[float]] = 1.0)`: 初始化串联电路，解析电路字符串并计算阻抗。
  - `_calculate_abcd(self)`: 计算串联电路的 ABCD 矩阵。
  - `get_abcd(self) -> Union[np.ndarray, List[np.ndarray]]`: 获取 ABCD 矩阵。

### 辅助函数
- `parse_circuit_string(circuit_str: str, frequency_ghz: Union[float, List[float]] = 1.0) -> Union[complex, List[complex]]`: 解析表示元件关系的字符串，返回电路阻抗。