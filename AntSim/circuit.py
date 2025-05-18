import numpy as np
import re
from typing import Union, List, Tuple

def parse_circuit_string(circuit_str: str, frequency_ghz: Union[float, List[float]] = 1.0) -> Union[complex, List[complex]]:
    """解析表示元件关系的字符串。
    
    字符串格式规则：
    - p: 代表pF（皮法）
    - n: 代表nH（纳亨）
    - o: 代表欧姆
    - +: 代表串联
    - /: 代表并联
    - 支持使用括号表示优先级
    
    示例：
    - "10p+20n": 10pF电容串联20nH电感
    - "(100o+10n)/50o": (100欧姆电阻串联10nH电感)并联50欧姆电阻
    
    参数：
        circuit_str: str，表示电路元件关系的字符串
        frequency_ghz: float或float列表，工作频率（GHz），默认为1.0GHz
        
    返回：
        complex或complex列表：解析后的电路阻抗。当输入频率为单个值时返回complex，
        当输入频率为列表时返回对应的阻抗列表
    """
    # 移除所有空白字符
    circuit_str = re.sub(r'\s+', '', circuit_str)
    
    def parse_value(value_str: str) -> Union[complex, List[complex]]:
        """解析元件值字符串，转换为复数阻抗。"""
        # 提取数值和单位
        match = re.match(r'(\d+\.?\d*)(p|n|o)', value_str)
        if not match:
            raise ValueError(f"无效的元件值格式：{value_str}")
            
        value, unit = float(match.group(1)), match.group(2)
        
        # 处理频率数组情况
        if isinstance(frequency_ghz, (list, tuple)):
            impedances = []
            for freq in frequency_ghz:
                omega = 2 * 3.14159 * freq * 1e9  # 使用当前频率计算角频率
                
                if unit == 'p':  # 电容，单位pF
                    # 电容的阻抗：Z = -j/(ωC)
                    capacitance = value * 1e-12  # 转换为法拉
                    impedances.append(complex(0, -1 / (omega * capacitance)))
                elif unit == 'n':  # 电感，单位nH
                    # 电感的阻抗：Z = jωL
                    inductance = value * 1e-9  # 转换为亨利
                    impedances.append(complex(0, omega * inductance))
                else:  # 电阻，单位欧姆
                    impedances.append(complex(value, 0))
            return impedances
        else:
            # 单个频率的情况
            omega = 2 * 3.14159 * frequency_ghz * 1e9  # 使用传入的频率计算角频率
            
            if unit == 'p':  # 电容，单位pF
                # 电容的阻抗：Z = -j/(ωC)
                capacitance = value * 1e-12  # 转换为法拉
                return complex(0, -1 / (omega * capacitance))
            elif unit == 'n':  # 电感，单位nH
                # 电感的阻抗：Z = jωL
                inductance = value * 1e-9  # 转换为亨利
                return complex(0, omega * inductance)
            else:  # 电阻，单位欧姆
                return complex(value, 0)
    
    def find_matching_parenthesis(s: str, start: int) -> int:
        """找到匹配的右括号位置。"""
        count = 1
        for i in range(start + 1, len(s)):
            if s[i] == '(':
                count += 1
            elif s[i] == ')':
                count -= 1
                if count == 0:
                    return i
        raise ValueError("括号不匹配")
    
    def parse_expression(expr: str) -> Union[complex, List[complex]]:
        """递归解析表达式。"""
        # 如果表达式中没有运算符，则为单个元件
        if '+' not in expr and '/' not in expr:
            return parse_value(expr)
        
        # 查找最后一个运算符
        operators = []
        i = 0
        while i < len(expr):
            if expr[i] == '(':
                i = find_matching_parenthesis(expr, i)
            elif expr[i] in '+/':
                operators.append((i, expr[i]))
            i += 1
        
        if not operators:
            # 如果没有找到运算符，可能是被括号包围的表达式
            if expr[0] == '(' and expr[-1] == ')':
                return parse_expression(expr[1:-1])
            else:
                return parse_value(expr)
        
        # 获取最后一个运算符
        op_pos, op = operators[-1]
        
        # 分割表达式
        left = expr[:op_pos]
        right = expr[op_pos + 1:]
        
        # 递归处理左右表达式
        z1 = parse_expression(left)
        z2 = parse_expression(right)
        
        # 根据运算符计算结果
        if op == '+':
            # 串联：Z = Z1 + Z2
            if isinstance(z1, list):
                return [z1[i] + z2[i] for i in range(len(z1))]
            return z1 + z2
        else:  # op == '/'
            # 并联：Z = (Z1 * Z2)/(Z1 + Z2)
            if isinstance(z1, list):
                return [(z1[i] * z2[i])/(z1[i] + z2[i]) for i in range(len(z1))]
            return (z1 * z2)/(z1 + z2)
    
    return parse_expression(circuit_str)

class SeriesCircuit:
    """串联电路类，用于计算串联电路的ABCD矩阵"""
    
    def __init__(self, circuit_str: str, frequency_ghz: Union[float, List[float]] = 1.0):
        """初始化串联电路
        
        参数：
            circuit_str: str，表示串联电路的字符串
            frequency_ghz: float或float列表，工作频率（GHz），默认为1.0GHz
        """
        self.circuit_str = circuit_str
        self.frequency_ghz = frequency_ghz
        self.impedance = parse_circuit_string(circuit_str, frequency_ghz)
        self._calculate_abcd()
    
    def _calculate_abcd(self):
        """计算串联电路的ABCD矩阵
        
        串联电路的ABCD矩阵为：
        | 1  Z |
        | 0  1 |
        其中Z为串联阻抗
        """
        if isinstance(self.impedance, list):
            # 处理频率数组情况
            self.abcd = []
            for z in self.impedance:
                abcd = np.array([[1], [z], [0], [1]], dtype=complex)
                self.abcd.append(abcd)
        else:
            # 单个频率情况
            self.abcd = np.array([[1], [self.impedance], [0], [1]], dtype=complex)
    
    def get_abcd(self) -> Union[np.ndarray, List[np.ndarray]]:
        """获取ABCD矩阵
        
        返回：
            np.ndarray或np.ndarray列表：ABCD矩阵。当输入频率为单个值时返回单个矩阵，
            当输入频率为列表时返回矩阵列表
        """
        return self.abcd

class ParallelCircuit:
    """并联电路类，用于计算并联电路的ABCD矩阵"""
    
    def __init__(self, circuit_str: str, frequency_ghz: Union[float, List[float]] = 1.0):
        """初始化并联电路
        
        参数：
            circuit_str: str，表示并联电路的字符串
            frequency_ghz: float或float列表，工作频率（GHz），默认为1.0GHz
        """
        self.circuit_str = circuit_str
        self.frequency_ghz = frequency_ghz
        self.impedance = parse_circuit_string(circuit_str, frequency_ghz)
        self._calculate_abcd()
    
    def _calculate_abcd(self):
        """计算并联电路的ABCD矩阵
        
        并联电路的ABCD矩阵为：
        | 1  0 |
        | 1/Z 1 |
        其中Z为并联阻抗
        """
        if isinstance(self.impedance, list):
            # 处理频率数组情况
            self.abcd = []
            for z in self.impedance:
                abcd = np.array([[1], [0], [1/z], [1]], dtype=complex)
                self.abcd.append(abcd)
        else:
            # 单个频率情况
            self.abcd = np.array([[1], [0], [1/self.impedance], [1]], dtype=complex)
    
    def get_abcd(self) -> Union[np.ndarray, List[np.ndarray]]:
        """获取ABCD矩阵
        
        返回：
            np.ndarray或np.ndarray列表：ABCD矩阵。当输入频率为单个值时返回单个矩阵，
            当输入频率为列表时返回矩阵列表
        """
        return self.abcd