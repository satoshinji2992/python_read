import os
import ast
import importlib
import inspect
import openai
import sys
from typing import Dict, List, Tuple, Any, Optional
import argparse


# 设置OpenAI API密钥

API_KEY = os.getenv("API_KEY")
API_BASE_URL = os.getenv("BASE_URL", "https://api.deepseek.com")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")

client = openai.OpenAI(
    api_key=API_KEY,
    base_url=API_BASE_URL
)


class PythonCodeAnalyzer:
    def __init__(self, file_path: str, model: str = "deepseek-chat", mode: int = 0):
        """初始化Python代码分析器"""
        self.file_path = file_path
        self.model = model
        self.source_code = ""
        self.tree = None
        self.imports = []
        self.functions = []
        self.mode = mode
        
    def load_file(self):
        """加载Python文件"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                self.source_code = file.read()
            self.tree = ast.parse(self.source_code)
            return True
        except Exception as e:
            print(f"无法加载文件: {e}")
            return False
            
    def extract_imports(self):
        """提取导入的模块"""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    self.imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module
                for name in node.names:
                    self.imports.append(f"{module}.{name.name}")
        return self.imports
        
    def get_module_info(self):
        """获取导入模块的函数信息"""
        module_info = {}
        for module_name in self.imports:
            try:
                # 处理from x import y情况
                if '.' in module_name:
                    parts = module_name.split('.')
                    base_module = parts[0]
                    try:
                        module = importlib.import_module(base_module)
                        sub_item = module
                        for part in parts[1:]:
                            sub_item = getattr(sub_item, part)
                        
                        if inspect.ismodule(sub_item):
                            module_info[module_name] = self._get_module_functions(sub_item)
                        else:
                            module_info[module_name] = self._get_item_doc(sub_item)
                    except Exception as e:
                        module_info[module_name] = f"无法获取信息: {str(e)}"
                else:
                    # 直接导入模块情况
                    module = importlib.import_module(module_name)
                    module_info[module_name] = self._get_module_functions(module)
            except Exception as e:
                module_info[module_name] = f"无法导入模块: {str(e)}"
                
        return module_info
    
    def _get_module_functions(self, module):
        """获取模块中的函数信息"""
        functions = {}
        for name, item in inspect.getmembers(module):
            if inspect.isfunction(item) and not name.startswith('_'):
                functions[name] = self._get_item_doc(item)
        return functions
    
    def _get_item_doc(self, item):
        """获取项目的文档字符串"""
        doc = inspect.getdoc(item)
        return doc if doc else "无文档字符串"
    
    def extract_functions(self):
        """提取文件中的函数"""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                function_info = {
                    'name': node.name,
                    'args': self._get_function_args(node),
                    'returns': self._get_return_annotation(node),
                    'body': ast.get_source_segment(self.source_code, node),
                    'docstring': ast.get_docstring(node) or "",
                    'start_line': node.lineno
                }
                self.functions.append(function_info)
        
        # 按行号排序函数
        self.functions.sort(key=lambda f: f['start_line'])
        return self.functions
    
    def _get_function_args(self, node):
        """获取函数参数"""
        args = []
        for arg in node.args.args:
            arg_info = {
                'name': arg.arg,
                'annotation': self._get_annotation(arg.annotation)
            }
            args.append(arg_info)
        return args
    
    def _get_return_annotation(self, node):
        """获取返回值注解"""
        if node.returns:
            return self._get_annotation(node.returns)
        return None
    
    def _get_annotation(self, annotation):
        """将AST注解转换为字符串"""
        if annotation is None:
            return None
        return ast.unparse(annotation)
    
    def generate_function_docs(self):
        """使用OpenAI生成函数文档，将模块信息作为上下文"""
        # 首先构建模块信息上下文
        module_context = "导入的模块及其功能:\n"
        for module_name, info in self.get_module_info().items():
            module_context += f"- {module_name}:\n"
            if isinstance(info, dict):
                for func_name, doc in info.items():
                    module_context += f"  - {func_name}: {doc[:100]}...\n"
            else:
                module_context += f"  {info[:100]}...\n"
        
        # 已分析的函数文档，作为上下文累积
        analyzed_functions_context = ""
        
        for i, function in enumerate(self.functions):
            try:
                prompt = f"""
                分析以下Python函数并提供简洁的功能说明：
                
                ```python
                {function['body']}
                ```
                
                模块上下文信息:
                {module_context}
                
                之前分析的函数:
                {analyzed_functions_context}
                
                请提供：
                1. 函数的主要功能
                2. 参数的用途
                3. 返回值的含义
                不要包含代码示例，只需提供功能描述。
                """
                
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是一个Python代码分析专家，擅长分析代码并提供简洁准确的功能说明。分析时应当考虑模块上下文与之前分析过的函数。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500
                )
                
                self.functions[i]['generated_doc'] = response.choices[0].message.content.strip()
                print(f"已生成 {function['name']} 的文档")
                
                # 将当前分析的函数添加到上下文中，供后续函数分析使用
                analyzed_functions_context += f"- {function['name']}: {self.functions[i]['generated_doc'][:150]}...\n"
                
            except Exception as e:
                self.functions[i]['generated_doc'] = f"无法生成文档: {str(e)}"
                print(f"生成 {function['name']} 文档时出错: {e}")
        
        return self.functions
    
    def generate_function_docs_two_pass(self):
        """使用两遍扫描方法生成函数文档"""
        # 首先构建模块信息上下文
        module_context = "导入的模块及其功能:\n"
        for module_name, info in self.get_module_info().items():
            module_context += f"- {module_name}:\n"
            if isinstance(info, dict):
                for func_name, doc in info.items():
                    module_context += f"  - {func_name}: {doc[:100]}...\n"
            else:
                module_context += f"  {info[:100]}...\n"
        
        # 第一遍：生成基础文档
        print("第一遍分析：生成基础文档...")
        for i, function in enumerate(self.functions):
            try:
                prompt = f"""
                分析以下Python函数并提供简洁的基础功能说明：
                
                ```python
                {function['body']}
                ```
                
                模块上下文信息:
                {module_context}
                
                请提供：
                1. 函数的主要功能
                2. 参数的用途
                3. 返回值的含义
                只需简短描述，第二轮会进行更详细分析。
                """
                
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是一个Python代码分析专家，擅长简洁描述函数功能。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=250  # 第一遍使用较少token
                )
                
                self.functions[i]['preliminary_doc'] = response.choices[0].message.content.strip()
                print(f"第一遍已生成 {function['name']} 的基础文档")
                
            except Exception as e:
                self.functions[i]['preliminary_doc'] = f"无法生成基础文档: {str(e)}"
                print(f"第一遍生成 {function['name']} 文档时出错: {e}")
        
        # 构建完整函数上下文
        full_functions_context = ""
        for function in self.functions:
            full_functions_context += f"- {function['name']}: {function.get('preliminary_doc', '无基础文档')[:150]}...\n"
        
        # 第二遍：生成更全面的文档，考虑所有函数的上下文
        print("第二遍分析：生成详细文档...")
        for i, function in enumerate(self.functions):
            try:
                prompt = f"""
                对以下Python函数进行更深入的分析，提供详细的功能说明：
                
                ```python
                {function['body']}
                ```
                
                模块上下文信息:
                {module_context}
                
                文件中所有函数的基础信息:
                {full_functions_context}
                
                请提供更详细的：
                1. 函数的主要功能和用途
                2. 参数的详细解释
                3. 返回值的含义和用途
                4. 与其他函数的关联和依赖关系
                
                基于第一轮分析的初步结果:
                {function.get('preliminary_doc', '无基础文档')}
                """
                
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是一个Python代码分析专家，擅长深入分析代码并理解函数之间的关系。在第二轮分析中，你应当参考所有函数的基础信息，提供更全面和准确的功能说明。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500
                )
                
                self.functions[i]['generated_doc'] = response.choices[0].message.content.strip()
                print(f"第二遍已生成 {function['name']} 的详细文档")
                
            except Exception as e:
                # 如果第二遍失败，使用第一遍的结果
                self.functions[i]['generated_doc'] = self.functions[i].get('preliminary_doc', f"无法生成文档: {str(e)}")
                print(f"第二遍生成 {function['name']} 文档时出错: {e}")
        
        return self.functions
    
    def format_function_declaration(self, function):
        """格式化函数声明"""
        args_str = []
        for arg in function['args']:
            if arg['annotation']:
                args_str.append(f"{arg['name']}: {arg['annotation']}")
            else:
                args_str.append(arg['name'])
        
        args_formatted = ", ".join(args_str)
        returns = f" -> {function['returns']}" if function['returns'] else ""
        
        declaration = f"def {function['name']}({args_formatted}){returns}:"
        return declaration
    
    def analyze_variables(self, function_name=None):
        """分析函数中的变量使用情况"""
        variable_info = {}
        
        target_functions = [f for f in self.functions if function_name is None or f['name'] == function_name]
        
        for function in target_functions:
            variables = {}
            # 找到函数节点
            function_node = None
            for node in ast.walk(self.tree):
                if isinstance(node, ast.FunctionDef) and node.name == function['name']:
                    function_node = node
                    break
                    
            if function_node:
                # 分析变量赋值
                for node in ast.walk(function_node):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                variables[target.id] = {
                                    'line': node.lineno,
                                    'type': self._infer_type(node.value)
                                }
            
            variable_info[function['name']] = variables
        
        return variable_info

    def _infer_type(self, node):
        """尝试推断表达式的类型"""
        if isinstance(node, ast.Constant):
            return type(node.value).__name__
        elif isinstance(node, ast.List):
            return 'list'
        elif isinstance(node, ast.Dict):
            return 'dict'
        elif isinstance(node, ast.Call):
            if hasattr(node.func, 'id'):
                return f"call:{node.func.id}"
            return 'function_call'
        return 'unknown'
    
    def analyze_code_flow(self, function_name=None):
        """分析代码执行流程，找出函数调用关系"""
        call_graph = {}
        
        # 如果指定了函数名，只分析该函数
        target_functions = [f for f in self.functions if function_name is None or f['name'] == function_name]
        
        for function in target_functions:
            calls = []
            # 解析函数体找出所有函数调用
            function_node = None
            for node in ast.walk(self.tree):
                if isinstance(node, ast.FunctionDef) and node.name == function['name']:
                    function_node = node
                    break
                    
            if function_node:
                for node in ast.walk(function_node):
                    if isinstance(node, ast.Call) and hasattr(node.func, 'id'):
                        calls.append(node.func.id)
                    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                        calls.append(f"{node.func.value.id}.{node.func.attr}" if hasattr(node.func.value, 'id') else node.func.attr)
            
            call_graph[function['name']] = calls
        
        return call_graph
    
    def detect_potential_issues(self):
        """检测代码中可能存在的问题"""
        issues = []
        
        # 检查所有函数
        for function in self.functions:
            function_node = None
            for node in ast.walk(self.tree):
                if isinstance(node, ast.FunctionDef) and node.name == function['name']:
                    function_node = node
                    break
                    
            if function_node:
                # 检查异常处理
                has_try = False
                for node in ast.walk(function_node):
                    if isinstance(node, ast.Try):
                        has_try = True
                        break
                
                # 检查是否有返回值
                has_return = False
                for node in ast.walk(function_node):
                    if isinstance(node, ast.Return):
                        has_return = True
                        break
                
                # 如果函数名称暗示返回值但没有return语句
                if (function['name'].startswith('get_') or 
                    function['name'].startswith('create_') or 
                    function['name'].startswith('generate_')) and not has_return:
                    issues.append({
                        'function': function['name'],
                        'issue': '函数名称暗示应该返回值，但没有发现return语句',
                        'severity': 'warning'
                    })
                
                # 检查是否有未使用的变量
                # ...
        
        return issues
    
    def generate_debugging_suggestions(self, function_name):
        """为特定函数生成调试建议"""
        function = next((f for f in self.functions if f['name'] == function_name), None)
        if not function:
            return f"找不到函数 {function_name}"
        
        suggestions = [
            f"# 调试 {function_name} 的建议",
            "",
            "## 插入日志语句",
            "```python",
            f"def {function_name}({', '.join(arg['name'] for arg in function['args'])}):",
            "    print(f\"进入 {function_name}\")",
        ]
        
        # 为每个参数添加日志
        for arg in function['args']:
            suggestions.append(f"    print(f\"{arg['name']} = {{{arg['name']}}}\")")
        
        suggestions.extend([
            "    # ... 原函数代码 ...",
            "    result = original_calculation",
            "    print(f\"函数 {function_name} 返回值 = {result}\")",
            "    return result",
            "```"
        ])
        
        return "\n".join(suggestions)
    
    def generate_report(self):
        """生成分析报告"""
        if not self.load_file():
            return "无法分析文件"
            
        print("分析导入模块...")
        imports = self.extract_imports()
        module_info = self.get_module_info()
        
        print("提取函数信息...")
        functions = self.extract_functions()
        
        if self.mode == 0:
            print("生成函数文档...")
            self.generate_function_docs() 

        if self.mode == 1:
            print("生成函数文档（两遍分析）...")
            self.generate_function_docs_two_pass()


        
        # 生成报告
        report = f"# Python文件分析报告: {os.path.basename(self.file_path)}\n\n"
        
        
        # 模块部分 - 简化版
        report += "## 导入的模块\n\n"
        report += "| 模块 | 类型 | 主要功能/函数 |\n"
        report += "|------|------|---------------|\n"
        for module_name, info in module_info.items():
            if isinstance(info, dict):
                funcs = ", ".join(list(info.keys())[:3])
                if len(info) > 3:
                    funcs += f"... (共{len(info)}个函数)"
                report += f"| {module_name} | 模块 | {funcs} |\n"
            else:
                short_info = info[:50] + "..." if len(info) > 50 else info
                report += f"| {module_name} | 其他 | {short_info} |\n"
        
        # 函数部分
        report += "## 文件中的函数\n\n"
        for function in self.functions:
            declaration = self.format_function_declaration(function)
            report += f"### {function['name']}\n\n"
            report += f"```python\n{declaration}\n```\n\n"
            
            report += "**参数:**\n\n"
            for arg in function['args']:
                annotation = f": {arg['annotation']}" if arg['annotation'] else ""
                report += f"- `{arg['name']}{annotation}`\n"
            
            if function['returns']:
                report += f"\n**返回值:** `{function['returns']}`\n\n"
            
            report += f"**功能说明:**\n\n{function['generated_doc']}\n\n"
            
            if function['docstring']:
                report += f"**原始文档:**\n\n{function['docstring']}\n\n"
            
            call_graph = self.analyze_code_flow(function['name'])

            if call_graph.get(function['name']):
                report += "**调用的其他函数:**\n\n"
                for call in call_graph[function['name']]:
                    report += f"- `{call}`\n"
            
            # 在函数部分添加变量信息
        variable_info = self.analyze_variables(function['name'])
        if variable_info.get(function['name']):
            report += "**变量使用:**\n\n"
            report += "| 变量名 | 推断类型 | 定义行号 |\n"
            report += "|--------|----------|----------|\n"
            for var_name, var_data in variable_info[function['name']].items():
                report += f"| {var_name} | {var_data['type']} | {var_data['line']} |\n"
            
            report += "---\n\n"
        
                # 在报告末尾添加问题检测部分
        issues = self.detect_potential_issues()
        if issues:
            report += "## 潜在问题\n\n"
            report += "| 函数 | 问题描述 | 严重程度 |\n"
            report += "|------|----------|----------|\n"
            for issue in issues:
                report += f"| {issue['function']} | {issue['issue']} | {issue['severity']} |\n"
            
            
        return report

def main():
    parser = argparse.ArgumentParser(description='Python代码分析工具')
    parser.add_argument('file_path', help='要分析的Python文件路径')
    parser.add_argument('--mode', type=int, default=0, help='分析模式 (0或1)')
    parser.add_argument('--function', help='指定要分析的函数名')
    parser.add_argument('--debug', action='store_true', help='生成调试建议')
    
    args = parser.parse_args()
    
    analyzer = PythonCodeAnalyzer(args.file_path, MODEL_NAME, args.mode)
    
    if args.debug and args.function:
        # 生成调试建议
        suggestions = analyzer.generate_debugging_suggestions(args.function)
        print(suggestions)
    else:
        # 生成完整报告
        report = analyzer.generate_report()
        # 保存报告
        output_file = f"{os.path.splitext(args.file_path)[0]}_analysis.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"分析完成! 报告已保存至: {output_file}")

if __name__ == "__main__":
    main()