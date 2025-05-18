import re
import numpy as np
from typing import Union, List, Tuple
from PyQt5 import QtWidgets  # 新增导入 PyQt5 的 QtWidgets
# 修改相对导入为绝对导入
from circuit import SeriesCircuit
from circuit import ParallelCircuit

def ElementCalculation(element_str: str, frequency_ghz: Union[float, List[float]] = 1.0) -> Union[np.ndarray, List[np.ndarray]]:
    """计算复杂电路表达式的ABCD矩阵
    
    参数：
        element_str: str，复杂电路表达式，如S(2p+3n)+P((3p+1n+50o)/3p)
        frequency_ghz: float或float列表，工作频率（GHz），默认为1.0GHz
        
    返回：
        np.ndarray或np.ndarray列表：计算得到的ABCD矩阵
    """
    # 移除所有空白字符
    element_str = re.sub(r'\s+', '', element_str)
    
    def find_matching_parenthesis(s: str, start: int) -> int:
        """找到匹配的右括号位置"""
        count = 1
        for i in range(start + 1, len(s)):
            if s[i] == '(':
                count += 1
            elif s[i] == ')':
                count -= 1
                if count == 0:
                    return i
        raise ValueError("括号不匹配")
    
    def parse_circuit_expression(expr: str) -> Union[np.ndarray, List[np.ndarray]]:
        """解析电路表达式，返回ABCD矩阵"""
        try:
            # 如果表达式为空，返回单位矩阵
            if not expr:
                if isinstance(frequency_ghz, (list, tuple)):
                    return [np.array([[1], [0], [0], [1]], dtype=complex) for _ in range(len(frequency_ghz))]
                return np.array([[1], [0], [0], [1]], dtype=complex)
            
            # 查找最后一个+号，用于分割级联电路
            last_plus = -1
            i = 0
            while i < len(expr):
                if expr[i] == '(':
                    i = find_matching_parenthesis(expr, i)
                elif expr[i] == '+':
                    last_plus = i
                i += 1
            
            if last_plus != -1:
                # 存在级联电路，递归处理
                left_expr = expr[:last_plus]
                right_expr = expr[last_plus + 1:]
                left_abcd = parse_circuit_expression(left_expr)
                right_abcd = parse_circuit_expression(right_expr)
                
                # 计算级联
                def cascade_abcd(l, r):
                    # 将4x1向量转换为2x2矩阵进行计算
                    l_mat = np.array([[l[0,0], l[1,0]], [l[2,0], l[3,0]]], dtype=complex)
                    r_mat = np.array([[r[0,0], r[1,0]], [r[2,0], r[3,0]]], dtype=complex)
                    result = np.matmul(l_mat, r_mat)
                    # 将结果转换回4x1向量
                    return np.array([[result[0,0]], [result[0,1]], [result[1,0]], [result[1,1]]], dtype=complex)
                
                if isinstance(left_abcd, list):
                    return [cascade_abcd(l, r) for l, r in zip(left_abcd, right_abcd)]
                return cascade_abcd(left_abcd, right_abcd)
            
            # 处理S(...)或P(...)格式的表达式
            if expr.startswith('S(') or expr.startswith('P('):
                circuit_type = expr[0]  # S或P
                if not (expr[1] == '(' and expr[-1] == ')'):
                    raise ValueError(f"无效的{circuit_type}表达式：{expr}")
                
                inner_expr = expr[2:-1]  # 提取括号内的内容
                
                # 根据类型创建相应的电路对象
                if circuit_type == 'S':
                    return SeriesCircuit(inner_expr, frequency_ghz).get_abcd()
                else:  # circuit_type == 'P'
                    return ParallelCircuit(inner_expr, frequency_ghz).get_abcd()
            
            raise ValueError(f"无效的电路表达式：{expr}")
        except Exception as e:
            # 显示错误弹窗
            app = QtWidgets.QApplication.instance()
            if app is None:
                app = QtWidgets.QApplication([])
            QtWidgets.QMessageBox.critical(None, "解析错误", f"解析电路表达式时出错：{str(e)}")
            raise

    try:
        return parse_circuit_expression(element_str)
    except Exception as e:
        raise ValueError(f"解析电路表达式时出错：{str(e)}")


def FeedCalculation(element_str: str, frequency_ghz: Union[float, List[float]] = 1.0) -> Union[np.ndarray, List[np.ndarray]]:
    """计算馈电网络的ABCD矩阵
    
    参数：
        element_str: str，复杂电路表达式，如S(2p+3n)+P((3p+1n+50o)/3p)
        frequency_ghz: float或float列表，工作频率（GHz），默认为1.0GHz
        
    返回：
        np.ndarray或np.ndarray列表：计算得到的并联形式ABCD矩阵
    """
    # 获取ABCD矩阵
    abcd = ElementCalculation(element_str, frequency_ghz)
    
    def calculate_input_impedance(matrix: np.ndarray, load_impedance: float = 50.0) -> complex:
        """计算输入阻抗"""
        # 从4x1向量中提取ABCD参数
        A, B, C, D = matrix.reshape(-1)  # 使用reshape替代flatten
        return (A * load_impedance + B) / (C * load_impedance + D)
    
    def impedance_to_parallel_abcd(z: complex) -> np.ndarray:
        """将阻抗转换为并联形式的ABCD矩阵"""
        return np.array([[1], [0], [1/z], [1]], dtype=complex)
    
    if isinstance(abcd, list):
        # 处理频率扫描情况
        input_impedances = [calculate_input_impedance(matrix) for matrix in abcd]
        return [impedance_to_parallel_abcd(z) for z in input_impedances]
    else:
        # 处理单频率情况
        input_impedance = calculate_input_impedance(abcd)
        return impedance_to_parallel_abcd(input_impedance)
