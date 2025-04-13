import os
import ast
import importlib
import inspect
import openai
import sys
from typing import Dict, List, Tuple, Any, Optional
import argparse
import asyncio
import aiohttp
import json


# 设置OpenAI API密钥

API_KEY = os.getenv("API_KEY")
API_BASE_URL = os.getenv("BASE_URL", "https://api.deepseek.com")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")

client = openai.OpenAI(
    api_key=API_KEY,
    base_url=API_BASE_URL
)


class PythonCodeAnalyzer:
    def __init__(self, file_path: str, model: str = "deepseek-chat"):
        """初始化Python代码分析器"""
        self.file_path = file_path
        self.model = model
        self.source_code = ""
        self.tree = None
        self.imports = []
        self.functions = []
        
    def load_file(self):
        """加载Python文件"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                self.source_code = file.read()
            self.tree = ast.parse(self.source_code)
            
            # 确保当前目录加入 sys.path，以便能够导入同目录下的模块
            script_dir = os.path.dirname(os.path.abspath(self.file_path))
            if script_dir not in sys.path:
                sys.path.insert(0, script_dir)
                
            return True
        except Exception as e:
            print(f"无法加载文件: {e}")
            return False
            
    def extract_imports(self):
        """提取导入的模块"""
        self.imports = []  # 清空之前的导入列表
        
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    self.imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module
                for name in node.names:
                    if module:
                        self.imports.append(f"{module}.{name.name}")
                    else:
                        # 处理相对导入，如 from . import x
                        self.imports.append(name.name)
        
        # 移除重复项并排序
        self.imports = sorted(list(set(self.imports)))
        return self.imports

    def get_module_info(self):
        """获取导入模块的函数信息"""
        module_info = {}
        
        for module_name in self.imports:
            try:
                if '.' in module_name:
                    parts = module_name.split('.')
                    try:
                        # 尝试导入前面的模块
                        base_module = importlib.import_module(parts[0])
                        # 逐级获取属性
                        sub_item = base_module
                        for part in parts[1:-1]:  # 不包括最后一个部分
                            sub_item = getattr(sub_item, part)
                        
                        # 获取最终的子项
                        final_item = getattr(sub_item, parts[-1])
                        
                        if inspect.ismodule(final_item):
                            module_info[module_name] = self._get_module_functions(final_item)
                        else:
                            module_info[module_name] = self._get_item_doc(final_item)
                    except (ImportError, AttributeError) as e:
                        # 尝试直接导入完整路径
                        try:
                            module = importlib.import_module(module_name)
                            module_info[module_name] = self._get_module_functions(module)
                        except ImportError:
                            # 如果不行，再尝试导入父模块
                            try:
                                parent_module_name = '.'.join(parts[:-1])
                                parent_module = importlib.import_module(parent_module_name)
                                sub_item = getattr(parent_module, parts[-1])
                                
                                if inspect.ismodule(sub_item):
                                    module_info[module_name] = self._get_module_functions(sub_item)
                                else:
                                    module_info[module_name] = self._get_item_doc(sub_item)
                            except Exception as inner_e:
                                module_info[module_name] = f"无法导入: {str(inner_e)}"
                else:
                    # 直接导入模块
                    module = importlib.import_module(module_name)
                    module_info[module_name] = self._get_module_functions(module)
            except Exception as e:
                module_info[module_name] = f"无法导入模块: {str(e)}"
                
        return module_info

    def _get_module_functions(self, module):
        """获取模块中的函数信息"""
        functions = {}
        try:
            for name, item in inspect.getmembers(module):
                if inspect.isfunction(item) and not name.startswith('_'):
                    doc = self._get_item_doc(item)
                    # 确保doc是字符串
                    functions[name] = str(doc) if doc is not None else "无文档字符串"
                elif inspect.isclass(item) and not name.startswith('_'):
                    # 类信息
                    doc = inspect.getdoc(item)
                    class_info = {"__doc__": str(doc) if doc is not None else "无文档字符串"}
                    functions[f"类:{name}"] = class_info
        except Exception as e:
            # 捕获任何异常，返回错误信息
            return {"错误": f"获取模块函数时出错: {str(e)}"}
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
    
    async def generate_function_docs(self):
        """使用OpenAI生成函数文档，先做一遍简单分析作为上下文，再异步详细分析每个函数"""
        # 首先构建模块信息上下文
        module_context = "导入的模块及其功能:\n"
        for module_name, info in self.get_module_info().items():
            module_context += f"- {module_name}:\n"
            if isinstance(info, dict):
                for func_name, doc in info.items():
                    # 确保doc是字符串
                    doc_str = str(doc) if doc is not None else "无文档"
                    # 安全地截取前100个字符
                    doc_preview = doc_str[:100] + "..." if len(doc_str) > 100 else doc_str
                    module_context += f"  - {func_name}: {doc_preview}\n"
            else:
                # 确保info是字符串
                info_str = str(info) if info is not None else "无信息"
                # 安全地截取前100个字符
                info_preview = info_str[:100] + "..." if len(info_str) > 100 else info_str
                module_context += f"  {info_preview}\n"
        
        # 第一步：生成所有函数的简要概述作为上下文
        functions_overview = "函数概览:\n"
        for function in self.functions:
            # 提取函数名、参数和返回类型等基本信息
            args_str = ", ".join([f"{arg['name']}: {arg['annotation'] or '未知类型'}" for arg in function['args']])
            returns = function['returns'] or "未知类型"
            docstring = function['docstring']
            
            # 如果有docstring，使用它；否则，基于函数名和参数猜测功能
            if docstring:
                brief = docstring.split("\n")[0][:150]
            else:
                # 基于函数名称猜测功能
                name = function['name']
                brief = f"函数 {name}({args_str}) -> {returns}"
                if name.startswith("get_"):
                    brief += "，可能用于获取数据"
                elif name.startswith("set_"):
                    brief += "，可能用于设置数据"
                elif name.startswith("is_"):
                    brief += "，可能用于检查条件"
                elif name.startswith("create_") or name.startswith("generate_"):
                    brief += "，可能用于创建新对象或数据"
            
            functions_overview += f"- {function['name']}: {brief}\n"
        
        # 第二步：异步并行生成每个函数的详细文档
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i, function in enumerate(self.functions):
                task = self._generate_doc_for_function(session, i, function, module_context, functions_overview)
                tasks.append(task)
            
            # 并行执行所有任务
            await asyncio.gather(*tasks)
        
        return self.functions

    async def _generate_doc_for_function(self, session, i, function, module_context, functions_overview):
        """异步为单个函数生成详细文档"""
        print(f"开始生成 {function['name']} 的文档...")
        try:
            prompt = f"""
            分析以下Python函数并提供简洁的功能说明：
            
            ```python
            {function['body']}
            ```
            
            模块上下文信息:
            {module_context}
            
            其他函数概览:
            {functions_overview}
            
            请提供：
            1. 函数的主要功能
            2. 参数的用途
            3. 返回值的含义
            不要包含代码示例，只需提供功能描述。
            """
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是一个Python代码分析专家，擅长分析代码并提供简洁准确的功能说明。分析时应当考虑模块上下文与其他函数的概览。"},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 500
            }
            
            async with session.post(
                f"{API_BASE_URL}/v1/chat/completions", 
                headers=headers, 
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    self.functions[i]['generated_doc'] = result['choices'][0]['message']['content'].strip()
                    print(f"已生成 {function['name']} 的文档")
                else:
                    error_text = await response.text()
                    self.functions[i]['generated_doc'] = f"API请求失败: {response.status}, {error_text}"
                    print(f"生成 {function['name']} 文档时API请求失败: {response.status}")
        
        except Exception as e:
            self.functions[i]['generated_doc'] = f"无法生成文档: {str(e)}"
            print(f"生成 {function['name']} 文档时出错: {e}")
    
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
    
    async def analyze_function_issues(self, function_data):
        """使用AI分析函数的潜在问题并提供修改建议"""
        try:
            function_name = function_data['name']
            function_code = function_data['body']
            function_signature = self.format_function_declaration(function_data)
            docstring = function_data.get('docstring', "无文档字符串")
            
            prompt = f"""
    分析以下Python函数的潜在问题并提供具体的修改建议:

    函数签名：
    {function_signature}

    函数文档：
    {docstring}

    函数代码：
    ```python
    {function_code}
    请识别以下可能的问题并提供改进建议:

      1.函数设计问题（命名、参数、返回值等）
      2.代码风格与最佳实践问题
      3.可能的bug或错误处理缺陷
      4.性能优化机会
      5.文档完整性
      以Markdown格式输出，问题描述应简洁明了，修改建议应具体可行。 """
                # 使用OpenAI API生成分析结果
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一位Python代码分析专家，善于发现代码中的潜在问题并提供改进建议。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            analysis = response.choices[0].message.content.strip()
            print(f"分析完成: {function_name}")
            return {
                "function": function_name,
                "analysis": analysis
            }
        except Exception as e:
            return {
                "function": function_data.get('name', 'unknown'),
                "analysis": f"分析过程中出错: {str(e)}"
            }
    
    async def analyze_all_functions_issues(self): 
        """异步分析所有函数的潜在问题并提供修改建议""" 
        if not self.functions: print("正在提取函数信息...") 
        self.extract_functions()
        print(f"开始分析 {len(self.functions)} 个函数的潜在问题...")

        tasks = []
        for function_data in self.functions:
            tasks.append(self.analyze_function_issues(function_data))

        # 同时执行所有分析任务（不设置并发限制）
        results = await asyncio.gather(*tasks)

        print(f"函数分析完成!")
        return results
            
    
    def generate_report(self):
        """生成分析报告"""
        if not self.load_file():
            return "无法分析文件"
                    
        print("分析导入模块...")
        imports = self.extract_imports()
        module_info = self.get_module_info()
        
        print("提取函数信息...")
        functions = self.extract_functions()
        
        print("生成函数文档...")
        try:
            # 初始化所有函数的generated_doc字段，避免后续报错
            for function in self.functions:
                function['generated_doc'] = "生成中..."
                
            # 使用异步方法生成文档
            asyncio.run(self.generate_function_docs()) 
        except Exception as e:
            print(f"生成函数文档时出错: {e}")
            # 确保每个函数都有generated_doc字段
            for function in self.functions:
                if 'generated_doc' not in function:
                    function['generated_doc'] = "文档生成失败"

        print("正在分析函数的潜在问题...")
        try:
            # 使用新的异步函数分析功能，同样在同步函数中运行
            function_analyses = asyncio.run(self.analyze_all_functions_issues())
        except Exception as e:
            print(f"分析函数问题时出错: {e}")
            function_analyses = []  # 如果分析失败，使用空列表

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
            
            # 安全访问generated_doc字段
            doc = function.get('generated_doc', "未能生成功能说明")
            report += f"**功能说明:**\n\n{doc}\n\n"
            
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
                report += "\n**变量使用:**\n\n"
                report += "| 变量名 | 推断类型 | 定义行号 |\n"
                report += "|--------|----------|----------|\n"
                for var_name, var_data in variable_info[function['name']].items():
                    report += f"| {var_name} | {var_data['type']} | {var_data['line']} |\n"
            
            report += "\n---\n\n"
        
        # 在报告末尾添加问题分析和改进建议部分
        if function_analyses:
            report += "## 函数问题分析与改进建议\n\n"
            for analysis in function_analyses:
                report += f"### {analysis['function']}\n\n"
                report += analysis['analysis']
                report += "\n\n---\n\n"
        
        # 尝试生成程序摘要
        try:
            program_summary = asyncio.run(self._generate_ai_summary(os.path.basename(self.file_path), report))
            
            # 将摘要插入到报告开头
            if program_summary:
                report = f"# Python文件分析报告: {os.path.basename(self.file_path)}\n\n" + \
                        f"## 程序概述\n\n{program_summary}\n\n" + \
                        report.split("# Python文件分析报告:")[1]
        except Exception as e:
            print(f"生成程序摘要时出错: {e}")
                    
        return report

    def _generate_ai_summary(self, filename, report):
        """使用OpenAI直接生成程序摘要"""
        try:
            # 如果API密钥不可用，直接返回None
            if not API_KEY:
                print("未设置API_KEY，跳过生成AI摘要")
                return None
                
            print("正在生成程序概述...")
            
            # 限制报告长度，避免超出token限制
            max_report_length = 8000  # 根据实际模型能力调整
            if len(report) > max_report_length:
                # 提取关键部分
                report_parts = report.split('\n\n')
                # 保留开头(通常包含模块和主要功能信息)和一些关键部分
                truncated_report = '\n\n'.join(report_parts[:15])
                if len(truncated_report) > max_report_length:
                    truncated_report = truncated_report[:max_report_length] + "..."
            else:
                truncated_report = report
            
            prompt = f"""
            以下是Python文件 {filename} 的分析报告。请基于此报告生成一个简洁的程序概述，包括:
            1. 程序的主要功能和用途
            2. 核心组件和关键函数
            3. 主要依赖模块
            4. 程序的架构特点
            5. 可能的应用场景
            
            概述应该简洁清晰，不超过300字，格式为Markdown。
            
            分析报告:
            {truncated_report}
            """
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个Python代码分析专家，擅长理解程序结构并提供简洁准确的概述。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800
            )
            
            ai_summary = response.choices[0].message.content.strip()
            print("已生成程序概述")
            return ai_summary
            
        except Exception as e:
            print(f"生成程序概述时出错: {e}")
            return None

def main():
    parser = argparse.ArgumentParser(description='Python代码分析工具')
    parser.add_argument('file_path', help='要分析的Python文件路径')
    
    args = parser.parse_args()
    
    analyzer = PythonCodeAnalyzer(args.file_path, MODEL_NAME)
    
    report = analyzer.generate_report()
    # 保存报告
    output_file = f"{os.path.splitext(args.file_path)[0]}_analysis.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"分析完成! 报告已保存至: {output_file}")

if __name__ == "__main__":
    main()