import numpy as np
import matplotlib.pyplot as plt
from PyQt5 import QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


class ResultPlot:
    def __init__(self, calculator: 'AntSimCalculator', result_ui):
        self.calculator = calculator  # 存储AntSimCalculator实例
        self.result_ui = result_ui    # 存储绑定的结果UI对象
        self.current_widget = self.result_ui.findChild(QtWidgets.QFrame, 'Current')
        if not self.current_widget:
            raise ValueError("未找到名为'Current'的QFrame子控件")

    def plot_results(self):
        # 获取计算结果（示例：单频点电流矩阵）
        current_matrix = self.calculator.get_single_freq_current_matrix()
        if current_matrix is None:
            print("没有可用的电流数据，无法绘图。")
            return

        # 获取网格数据
        grid_array = self.calculator.data_source.get_grid_array()
        if grid_array.size == 0:
            print("网格数据为空，无法绘图。")
            return

        # 提取第一个馈电点的电流数据（示例逻辑）
        current_array_complex = current_matrix[:, 0] if current_matrix.shape[1] > 0 else None
        if current_array_complex is None:
            print("馈电点电流数据缺失，无法绘图。")
            return

        # 计算带相位符号的电流幅度（参考现有plot_current_curve逻辑）
        current_amplitudes = np.abs(current_array_complex)
        current_phases = np.angle(current_array_complex)
        signed_current = current_amplitudes * np.sign(current_phases)
        # 归一化到(-1, 1)区间
        max_abs = np.max(np.abs(signed_current)) if signed_current.size > 0 else 1.0
        if max_abs != 0:
            signed_current = signed_current / max_abs

        # 创建/更新绘图组件（参考现有plot_current_curve逻辑）
        plt.rcParams['font.family'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False

        # 若Current子控件已有画布则清空，否则新建
        if hasattr(self.current_widget, 'current_plot_canvas'):
            self.current_widget.current_plot_canvas.deleteLater()
            self.current_widget.current_plot_ax = None

        figure = plt.Figure()
        canvas = FigureCanvas(figure)
        ax = figure.add_subplot(111)
        ax.plot(grid_array, signed_current)
        ax.set_title('结果电流分布（考虑相位）')
        ax.set_xlabel('Mesh 网格', fontsize=24)
        ax.set_ylabel('带相位符号的电流幅度', fontsize=24)


        # 添加导航工具栏
        toolbar = NavigationToolbar(canvas, self.current_widget)

        # 设置布局（若Current子控件无布局则新建）
        layout = self.current_widget.layout()
        if not layout:
            layout = QtWidgets.QVBoxLayout(self.current_widget)
        layout.addWidget(toolbar)
        layout.addWidget(canvas)

        # 存储画布引用以便后续更新
        self.current_widget.current_plot_canvas = canvas
        self.current_widget.current_plot_ax = ax

        # 初始化标记点列表
        self.markers = []
        # 连接鼠标移动事件
        self.motion_cid = canvas.mpl_connect('motion_notify_event', self.on_mouse_move)

    def update_single_freq_curve(self):
        # 获取最新的单频点电流数据
        current_matrix = self.calculator.get_single_freq_current_matrix()
        if current_matrix is None:
            print("没有可用的电流数据，无法更新曲线。")
            return

        # 获取网格数据
        grid_array = self.calculator.data_source.get_grid_array()
        if grid_array.size == 0:
            print("网格数据为空，无法更新曲线。")
            return

        # 提取第一个馈电点的电流数据
        current_array_complex = current_matrix[:, 0] if current_matrix.shape[1] > 0 else None
        if current_array_complex is None:
            print("馈电点电流数据缺失，无法更新曲线。")
            return

        # 计算带相位符号的电流幅度
        current_amplitudes = np.abs(current_array_complex)
        current_phases = np.angle(current_array_complex)
        signed_current = current_amplitudes 
        #* np.sign(current_phases)
        # 归一化到(-1, 1)区间
        max_abs = np.max(np.abs(signed_current)) if signed_current.size > 0 else 1.0
        if max_abs != 0:
            signed_current = signed_current / max_abs

        # 检查是否已有画布和坐标轴
        if not hasattr(self.current_widget, 'current_plot_ax') or not hasattr(self.current_widget, 'current_plot_canvas'):
            print("未找到现有图表，将调用plot_results创建。")
            self.plot_results()
            return

        # 更新曲线数据
        ax = self.current_widget.current_plot_ax
        # 假设原曲线是第一条（索引0）
        if len(ax.lines) > 0:
            ax.lines[0].set_ydata(signed_current)
            ax.relim()  # 重新计算数据范围
            ax.autoscale_view()  # 自动调整坐标轴范围
            # 更新标题（可选）
            ax.set_title('更新后的单频点电流分布（考虑相位）')
            # 重绘画布
            self.current_widget.current_plot_canvas.draw()
        else:
            print("现有图表中没有曲线，将调用plot_results创建。")
            self.plot_results()

    def on_mouse_move(self, event):
        # 仅处理有效坐标
        if event.xdata is not None and event.ydata is not None:
            ax = self.current_widget.current_plot_ax
            grid_array = self.calculator.data_source.get_grid_array()
            current_array_complex = self.calculator.get_single_freq_current_matrix()[:, 0]
            current_amplitudes = np.abs(current_array_complex)
            max_abs = np.max(np.abs(current_amplitudes)) if current_amplitudes.size > 0 else 1.0
            signed_current = current_amplitudes / max_abs if max_abs != 0 else current_amplitudes
            
            # 插值获取对应y值
            y_val = np.interp(event.xdata, grid_array, signed_current)
            
            # 更新右上角文本
            if not hasattr(self, 'current_text'):
                self.current_text = ax.text(0.95, 0.95, '', transform=ax.transAxes, ha='right', va='top')
            self.current_text.set_text(f'x: {event.xdata:.2f}, y: {y_val:.2f}')
            self.current_widget.current_plot_canvas.draw()