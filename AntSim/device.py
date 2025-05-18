from PyQt5.QtWidgets import (QTreeWidget, QTreeWidgetItem, QComboBox,
                            QSpinBox, QSlider, QLineEdit, QMenu, QWidget)
from PyQt5.QtCore import Qt, pyqtSignal

class Antenna(QTreeWidget):
    data_changed = pyqtSignal() # 添加信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(5)
        # 列名保持不变，但类型下拉框内容会变
        self.setHeaderLabels(["类型", "实际位置", "索引", "滑块", "值"])

        # 保存网格步进值和网格数
        self.grid_step = 0.001
        self.grid_count = 2001

        # 初始化第一行
        self.add_row()

        # 启用右键菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def add_row(self, index_val=0, type_val="馈电", value_val=""): # 允许设置初始值
        item = QTreeWidgetItem(self)

        # 类型列 - 下拉框
        combo = QComboBox()
        # --- 修改：简化类型选项 ---
        combo.addItems(["馈电", "元件"])
        # --- 修改结束 ---
        if type_val in [combo.itemText(i) for i in range(combo.count())]:
            combo.setCurrentText(type_val)
        self.setItemWidget(item, 0, combo)

        # 实际位置列 - 文本 (由 update_position 更新)
        item.setText(1, "0")

        # 索引列 - SpinBox
        spin = QSpinBox()
        spin.setRange(0, self.grid_count - 1)
        spin.setValue(index_val) # 设置初始值
        self.setItemWidget(item, 2, spin)

        # 滑块列 - QSlider
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, self.grid_count - 1)
        slider.setValue(index_val) # 设置初始值
        self.setItemWidget(item, 3, slider)

        # 值列 - QLineEdit (始终可编辑)
        line_edit = QLineEdit(value_val) # 使用初始值
        self.setItemWidget(item, 4, line_edit)
        # --- 移除或注释掉根据类型设置编辑状态的逻辑 ---
        # self._update_value_editability(item) # 不再需要根据类型改变编辑状态

        # 绑定spinbox和slider的值
        spin.valueChanged.connect(lambda value, it=item: self.update_position(it, value)) # 传递 item
        slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)

        # --- 连接信号以触发 data_changed ---
        # --- 修改：类型改变不再需要调用 _on_type_changed 来控制编辑状态 ---
        combo.currentIndexChanged.connect(self.data_changed.emit) # 类型改变时直接发射信号
        # --- 修改结束 ---
        line_edit.editingFinished.connect(self.data_changed.emit) # 值编辑完成时

        # 触发一次初始位置更新
        self.update_position(item, index_val)

        # self.data_changed.emit() # 添加行后发射信号 (update_position 也会发)
        return item # 返回创建的 item

    # --- 移除或注释掉不再需要的方法 ---
    # def _on_type_changed(self, item):
    #     """当类型下拉框改变时调用 (不再需要)"""
    #     # self._update_value_editability(item) # 移除
    #     self.data_changed.emit() # 类型改变也发射信号 (已移至 add_row 中的 connect)

    # def _update_value_editability(self, item):
    #     """根据类型更新值列的可编辑状态 (不再需要)"""
    #     pass # 或者直接删除此方法
    # --- 移除结束 ---


    def update_position(self, item, index):
        # 计算实际位置并更新第1列
        actual_pos = index * self.grid_step
        item.setText(1, f"{actual_pos:.3f}")
        # 在更新位置后发射信号
        self.data_changed.emit()

    def update_grid_params(self, grid_step, grid_count):
        # 更新网格参数
        old_grid_count = self.grid_count
        self.grid_step = grid_step
        self.grid_count = grid_count

        needs_update = False # 标记是否有数据因范围变化而改变
        # 更新所有行的最大值和实际位置
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            spin = self.itemWidget(item, 2)
            slider = self.itemWidget(item, 3)

            if not spin or not slider: continue # 跳过无效行

            current_value = spin.value()
            new_max = self.grid_count - 1 if self.grid_count > 0 else 0

            # 更新范围
            spin.setRange(0, new_max)
            slider.setRange(0, new_max)

            # 如果当前值超出新范围，调整为最大值
            if current_value > new_max:
                spin.setValue(new_max) # setValue 会触发 valueChanged -> update_position -> data_changed
                needs_update = True # 标记需要发射信号（虽然setValue内部会触发）
            elif old_grid_count != self.grid_count: # 即使值没超范围，如果步长变了，位置也需要更新
                # 重新触发位置更新以使用新的 grid_step
                self.update_position(item, current_value) # update_position 会发射 data_changed
                needs_update = True # 标记需要发射信号（虽然update_position内部会触发）

        # if needs_update: # 由于 update_position 和 setValue 内部会触发，这里可能不再需要显式发射
        #      self.data_changed.emit()

    def show_context_menu(self, position):
        menu = QMenu()

        add_action = menu.addAction("新建行")
        add_action.triggered.connect(self.add_row_interactive) # 使用新方法

        delete_action = menu.addAction("删除选中行")
        delete_action.triggered.connect(self.delete_selected)

        menu.exec_(self.viewport().mapToGlobal(position))

    def add_row_interactive(self):
        """通过菜单添加新行"""
        self.add_row() # 使用默认值添加

    def delete_selected(self):
        items_to_delete = self.selectedItems()
        if not items_to_delete: return

        for item in items_to_delete:
            # 在移除 widget 之前断开连接，避免潜在问题
            combo = self.itemWidget(item, 0)
            spin = self.itemWidget(item, 2)
            slider = self.itemWidget(item, 3)
            line_edit = self.itemWidget(item, 4)
            try:
                if combo: combo.currentIndexChanged.disconnect() # 断开 combo 的连接
                if spin: spin.valueChanged.disconnect() # 断开 spin 的连接
                if slider: slider.valueChanged.disconnect()
                if line_edit: line_edit.editingFinished.disconnect()
            except TypeError:
                pass # Ignore if signals were not connected or already disconnected

            self.takeTopLevelItem(self.indexOfTopLevelItem(item))

        self.data_changed.emit() # 删除行后发射信号

    # --- 添加方法以方便外部设置/获取数据 ---
    def get_all_data(self):
        """获取控件中所有行的数据"""
        data = []
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if not item: continue
            combo = self.itemWidget(item, 0)
            spin = self.itemWidget(item, 2)
            line_edit = self.itemWidget(item, 4)

            type_val = combo.currentText() if combo else "N/A"
            index_val = spin.value() if spin else 0
            value_val = line_edit.text() if line_edit else ""
            actual_pos = item.text(1) # 读取实际位置文本

            data.append({
                '类型': type_val,
                '索引': index_val,
                '值': value_val,
                '实际位置': actual_pos # 也可包含位置信息
            })
        return data

    def set_all_data(self, data_list):
        """用提供的数据列表完全替换控件内容"""
        self.clear() # 清除现有所有行
        for data_item in data_list:
            self.add_row(
                index_val=data_item.get('索引', 0),
                type_val=data_item.get('类型', "馈电"),
                value_val=data_item.get('值', "0")
            )
        # set_all_data 完成后不需要单独发射信号，因为 add_row 内部会发射