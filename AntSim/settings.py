# Setting控件默认值配置
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt, QObject, pyqtSignal

# 将 Delegate 类定义移到 Settings 类外部或保持在 init_settings 内部，但确保只定义一次
class CustomItemDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 如果需要，可以在这里存储对树的引用
        # self.setting_tree = parent

    def createEditor(self, parent, option, index):
        if index.column() == 1:
            # 尝试通过 model() 获取 QTreeWidget
            model = index.model()
            # QStandardItemModel 没有 parent() 方法，需要找到 TreeWidget
            # 一个常见的方法是假设 delegate 的 parent 就是 TreeWidget
            tree_widget = self.parent()
            if isinstance(tree_widget, QtWidgets.QTreeWidget):
                item = tree_widget.itemFromIndex(index)
                if item:
                    item_text = item.text(0)
                    if item_text in ['频点数', '网格数']: # 只读字段
                        return None
                    if item_text == '自动触发':
                        editor = QtWidgets.QCheckBox(parent)
                        # 从 item 获取状态，而不是未定义的 child
                        editor.setChecked(item.checkState(1) == QtCore.Qt.Checked)
                        return editor
                    # 其他可编辑字段的默认编辑器
                    editor = QtWidgets.QLineEdit(parent)
                    editor.setValidator(QtGui.QDoubleValidator()) # 添加数字验证
                    return editor
        # 对于第0列或不满足条件的情况，不创建编辑器
        return super().createEditor(parent, option, index) # 或者显式返回 None

class Settings(QObject):
    # 定义信号
    frequency_changed = pyqtSignal(dict)
    grid_changed = pyqtSignal(dict)
    line_changed = pyqtSignal(dict)

    # 类属性作为默认设置
    frequency_settings = {
        "start_freq": "1", "current_freq": "1", "end_freq": "7",
        "freq_step": "0.01", "freq_count": "601"
    }
    grid_settings = {
        "impedance_pos": "10", "antenna_length": "100",
        "grid_step": "0.05", "grid_count": "2001"
    }
    line_settings = {
        "unit_R": "0.2", "unit_G": "0", "ref_freq": "2.6",
        "ref_wavelength": "14", "characteristic_impedance": "200"
    }

    def __init__(self):
        super().__init__()
        self.setting_tree = None

    # --- 唯一的 init_settings 方法 ---
    @classmethod
    def init_settings(cls, setting_tree):
        if not setting_tree:
            return None # 如果 tree 无效则返回

        # 1. 首先创建实例
        instance = cls()
        instance.setting_tree = setting_tree

        # 2. 配置 Tree Widget
        setting_tree.setColumnCount(3) # 假设三列：名称、值、(可选单位/描述)
        setting_tree.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.EditKeyPressed)

        # 设置自定义 Delegate
        # 注意：将 CustomItemDelegate 定义移到类外部或确保它只在此处定义一次
        delegate = CustomItemDelegate(setting_tree)
        setting_tree.setItemDelegate(delegate)

        # 配置项标志 (可编辑性, 可选中状态等)
        for i in range(setting_tree.topLevelItemCount()):
            item = setting_tree.topLevelItem(i)
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable) # 顶层项不可编辑
            for j in range(item.childCount()):
                child = item.child(j)
                child_text = child.text(0)
                if child_text == '自动触发':
                    child.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
                    child.setCheckState(1, QtCore.Qt.Unchecked) # 默认不选中
                elif child_text in ['频点数', '网格数']: # 只读计算字段
                     child.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled) # 不可编辑
                else: # 其他字段可编辑
                    child.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)

        # 3. 使用类属性中的默认值填充树
        # 使用类属性中的默认值填充树，这里的 antenna_length 单位可能是 mm
        top_level_items_data = [
            ("频率设置", cls.frequency_settings),
            ("网格设置", cls.grid_settings),
            ("传输线设置", cls.line_settings)
        ]

        for index, (category_name, settings_dict) in enumerate(top_level_items_data):
             item = setting_tree.topLevelItem(index)
             if item and item.text(0) == category_name: # 确保顶层项匹配
                 keys = list(settings_dict.keys()) # 获取定义顺序的键
                 for i, key in enumerate(keys):
                     if i < item.childCount(): # 检查子项是否存在
                         item.child(i).setText(1, settings_dict[key])

        # 4. 在实例创建和填充后执行初始计算并发出信号
        #    这些方法现在属于实例并使用 'self' (在方法内部)
        instance._update_frequency_settings() # 调用实例方法
        instance._update_grid_settings()      # 调用实例方法
        instance._update_line_settings()      # 调用实例方法

        # 5. 将 itemChanged 信号连接到实例的方法
        setting_tree.itemChanged.connect(instance._on_item_changed)

        # 6. 最终 UI 调整
        setting_tree.expandAll()

        # 7. 返回完全初始化的实例
        return instance

    # --- 实例方法 ---

    def _read_settings_from_tree(self, category_name):
        """辅助方法：从树中读取指定类别的设置"""
        settings = {}
        if not self.setting_tree: return settings
        # 使用 findItems 查找顶层项
        items = self.setting_tree.findItems(category_name, Qt.MatchExactly | Qt.MatchRecursive, 0)
        if not items: return settings
        root = items[0]

        # 假定子项的键是其第一列的文本（需要标准化）
        key_map = {}
        if category_name == "频率设置": key_map = {child.text(0): key for key, child in zip(self.frequency_settings.keys(), [root.child(i) for i in range(root.childCount())])}
        elif category_name == "网格设置": key_map = {child.text(0): key for key, child in zip(self.grid_settings.keys(), [root.child(i) for i in range(root.childCount())])}
        elif category_name == "传输线设置": key_map = {child.text(0): key for key, child in zip(self.line_settings.keys(), [root.child(i) for i in range(root.childCount())])}

        for i in range(root.childCount()):
            child = root.child(i)
            # 使用映射或标准化后的文本作为键
            key_text = child.text(0)
            # 标准化键名以匹配字典键 (例如, "开始频点" -> "start_freq")
            # 这里简化处理，假设顺序一致或使用映射
            internal_key = key_map.get(key_text, key_text.lower().replace(" ", "_")) # Fallback if map fails
            settings[internal_key] = child.text(1)
        return settings

    def _update_tree_item(self, category_name, internal_key, value):
         """辅助方法：更新树中的特定项"""
         if not self.setting_tree: return
         items = self.setting_tree.findItems(category_name, Qt.MatchExactly | Qt.MatchRecursive, 0)
         if not items: return
         root = items[0]

         # 找到对应的子项来更新
         target_child = None
         # 需要一种方法将 internal_key (如 "start_freq") 映射回 UI 文本 ("开始频点")
         # 或者直接按索引查找（如果顺序固定）
         key_to_find = ""
         if category_name == "频率设置": key_to_find = list(self.frequency_settings.keys()).index(internal_key)
         elif category_name == "网格设置": key_to_find = list(self.grid_settings.keys()).index(internal_key)
         elif category_name == "传输线设置": key_to_find = list(self.line_settings.keys()).index(internal_key)
         else: key_to_find = -1 # 未知类别

         if key_to_find != -1 and key_to_find < root.childCount():
              target_child = root.child(key_to_find)

         if target_child:
              # 暂时阻止信号以避免递归（如果 _on_item_changed 直接触发更新）
              # self.setting_tree.blockSignals(True)
              current_value = target_child.text(1)
              new_value_str = str(value)
              if current_value != new_value_str: # 仅在值改变时更新
                  target_child.setText(1, new_value_str)
              # self.setting_tree.blockSignals(False)


    def _update_frequency_settings(self):
        """读取频率设置，计算派生值，更新树，并发出信号"""
        settings = self._read_settings_from_tree("频率设置")
        updated = False # 标记是否有值被重新计算并更新到UI

        try:
            start = float(settings.get("start_freq", 0))
            end = float(settings.get("end_freq", 0))
            step_str = settings.get("freq_step", "")
            count_str = settings.get("freq_count", "")

            # 优先用步进计算数量
            if step_str:
                step = float(step_str)
                if step > 0:
                    count_calc = max(1, int((end - start) / step) + 1)
                    if str(count_calc) != count_str:
                        settings["freq_count"] = str(count_calc)
                        self._update_tree_item("频率设置", "freq_count", count_calc)
                        updated = True
                # 如果步进为0或负数，可能需要处理或忽略
            # 否则用数量计算步进
            elif count_str:
                count = max(1, int(count_str))
                if str(count) != count_str: # 确保数量至少为1
                    settings["freq_count"] = str(count)
                    self._update_tree_item("频率设置", "freq_count", count)
                    updated = True

                if count > 1:
                    step_calc = (end - start) / (count - 1)
                    step_rounded = str(round(step_calc, 4)) # 保留4位小数
                    if step_rounded != step_str:
                        settings["freq_step"] = step_rounded
                        self._update_tree_item("频率设置", "freq_step", step_rounded)
                        updated = True
                else: # count is 1
                    if "0" != step_str:
                        settings["freq_step"] = "0"
                        self._update_tree_item("频率设置", "freq_step", "0")
                        updated = True

            # 如果UI被更新，重新读取以确保一致性
            if updated:
                 settings = self._read_settings_from_tree("频率设置")

        except (ValueError, ZeroDivisionError, TypeError) as e:
            print(f"计算频率设置时出错: {e}") # 添加日志或错误处理

        self.frequency_changed.emit(settings)

    def _update_grid_settings(self):
        """读取网格设置，计算 grid_count，更新树，并发出信号"""
        settings = self._read_settings_from_tree("网格设置")
        updated = False

        try:
            length_str = settings.get("antenna_length", "")
            step_str = settings.get("grid_step", "")
            count_str = settings.get("grid_count", "")

            # 检查是否有足够信息计算网格数
            if length_str and step_str:
                antenna_length = float(length_str)
                grid_step = float(step_str)
                if grid_step > 0:
                    grid_count_calc = int(antenna_length / grid_step) + 1
                    if str(grid_count_calc) != count_str:
                        settings['grid_count'] = str(grid_count_calc)
                        self._update_tree_item("网格设置", "grid_count", grid_count_calc)
                        updated = True
                # 如果 grid_step <= 0，可能需要错误处理

            # 如果UI更新，重新读取
            if updated:
                 settings = self._read_settings_from_tree("网格设置")

        except (ValueError, ZeroDivisionError, TypeError) as e:
            print(f"计算网格设置时出错: {e}") # 添加日志

        self.grid_changed.emit(settings)

    def _update_line_settings(self):
        """读取传输线设置并发出信号"""
        settings = self._read_settings_from_tree("传输线设置")
        self.line_changed.emit(settings)

    def _on_item_changed(self, item, column):
        """处理树中的更改，触发更新和信号发射"""
        # 确保更改在值列 (1) 且项目有父项 (不是顶层项)
        if column == 1 and item and item.parent():
            parent_text = item.parent().text(0)
            item_text = item.text(0)

            # 避免由计算字段的更改触发无限循环
            if item_text in ['频点数', '网格数']:
                 return # 不处理对计算字段的直接编辑（如果允许的话）或程序化更改

            # 根据更改项的类别触发相应的更新方法
            if parent_text == '频率设置':
                self._update_frequency_settings()
            elif parent_text == '网格设置':
                self._update_grid_settings()
            elif parent_text == '传输线设置':
                # 传输线设置通常不涉及内部计算，可以直接触发更新/信号
                self._update_line_settings()

    def get_current_freq(self):
        """返回当前频点的值"""
        settings = self._read_settings_from_tree("频率设置")
        try:
            return float(settings.get("current_freq", 0))
        except ValueError:
            print("无法将当前频点转换为浮点数")
            return 0

# --- 删除所有重复的方法定义 ---
# 确保只有一个 init_settings (@classmethod)
# 确保只有一个 _update_frequency_settings (实例方法)
# 确保只有一个 _update_grid_settings (实例方法)
# 确保只有一个 _update_line_settings (实例方法)
# 确保只有一个 _on_item_changed (实例方法)

