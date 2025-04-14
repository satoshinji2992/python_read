import os
import sys
import asyncio
import argparse
import datetime
import openai
from python_read import PythonCodeAnalyzer, analyze_python_file_async

# 设置 OpenAI API 参数
API_KEY = os.getenv("API_KEY")
API_BASE_URL = os.getenv("BASE_URL", "https://api.deepseek.com")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")

# 初始化客户端
client = openai.OpenAI(
    api_key=API_KEY,
    base_url=API_BASE_URL
)

async def analyze_and_debug_file(file_path, model_name=MODEL_NAME):
    """分析单个Python文件并生成调试报告"""
    print(f"正在分析文件: {file_path}")
    
    # 记录分析时间
    import_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. 使用异步方法生成分析报告
    try:
        # 检查文件是否存在
        if not os.path.isfile(file_path):
            print(f"错误: 文件 {file_path} 不存在")
            return None
        
        # 使用python_read的异步分析函数
        analysis_result = await analyze_python_file_async(file_path, model_name)
        analyzer = analysis_result["analyzer"]
        analysis_report = analysis_result["report"]
        
        # 保存分析报告
        analysis_output_file = f"{os.path.splitext(file_path)[0]}_analysis.md"
        with open(analysis_output_file, 'w', encoding='utf-8') as f:
            f.write(analysis_report)
        
        print(f"分析报告已保存至: {analysis_output_file}")
        
        # 2. 使用分析结果生成调试报告
        debug_report = await generate_debug_report(file_path, analyzer, analysis_report, import_time)
        
        # 保存调试报告
        debug_output_file = f"{os.path.splitext(file_path)[0]}_debug.md"
        with open(debug_output_file, 'w', encoding='utf-8') as f:
            f.write(debug_report)
        
        print(f"调试报告已保存至: {debug_output_file}")
        
        return {
            "analysis_file": analysis_output_file,
            "debug_file": debug_output_file,
            "analyzer": analyzer,
            "analysis_report": analysis_report,
            "debug_report": debug_report
        }
    except Exception as e:
        print(f"分析过程中出错: {str(e)}")
        return None

async def generate_debug_report(file_path, analyzer, analysis_report, import_time):
    """根据分析报告生成调试建议"""
    filename = os.path.basename(file_path)
    
    # 读取源代码
    with open(file_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    # 准备重要的上下文信息
    function_summaries = []
    for function in analyzer.functions:
        function_info = f"### {function['name']}\n"
        function_info += f"- 签名: `{analyzer.format_function_declaration(function)}`\n"
        function_info += f"- 文档: {function.get('generated_doc', '无生成文档')[:200]}...\n"
        
        # 添加调用关系
        call_graph = analyzer.analyze_code_flow(function['name'])
        calls = call_graph.get(function['name'], [])
        if calls:
            function_info += f"- 调用: {', '.join(calls)}\n"
        
        # 添加变量信息
        var_info = analyzer.analyze_variables(function['name'])
        vars_data = var_info.get(function['name'], {})
        if vars_data:
            var_list = list(vars_data.items())[:5]  # 限制数量
            function_info += "- 变量: " + ", ".join([f"{name}({data['type']})" for name, data in var_list])
            if len(vars_data) > 5:
                function_info += f" 及其他{len(vars_data) - 5}个"
            function_info += "\n"
            
        function_summaries.append(function_info)
    
    # 准备导入模块信息
    module_info = "### 导入模块\n"
    for module in analyzer.imports[:10]:  # 限制数量以节省空间
        module_info += f"- {module}\n"
    if len(analyzer.imports) > 10:
        module_info += f"... 及其他 {len(analyzer.imports) - 10} 个模块\n"
    
    # 构建调试上下文
    debug_context = f"""# 文件分析摘要: {filename}

## 导入模块信息
{module_info}

## 函数摘要
{"".join(function_summaries)}
"""

    # 使用AI生成调试报告
    prompt = f"""
你是一名专业的Python代码调试和审查专家。我向你提供一个Python源文件和它的代码分析报告。请帮我找出代码中可能存在的问题并提供修复建议。

源代码:
```python
{source_code}
```

代码分析摘要:
{debug_context}

完整分析报告:
{analysis_report}...  # 截取部分分析报告以控制长度

请提供一份调试报告，包括:
1. 代码质量评估 - 评估整体代码质量和结构
2. 潜在bug分析 - 指出可能的错误和逻辑问题
3. 改进建议 - 提供具体的改进方案和示例代码
4. 安全问题 - 识别任何安全隐患
5. 性能优化 - 提出性能改进建议

针对AI生成的代码，请特别注意这些常见问题:
- 未处理的边界条件和异常情况
- 不一致的变量命名和函数签名
- 功能重复或未完全实现
- 缺少错误处理
- 未充分测试的假设

请提供具体的行号引用和详细的修复建议。
"""

    try:
        # 我们使用同步客户端来调用API
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "你是一位精通Python的高级代码审查和调试专家。你擅长发现AI生成代码中的问题并提供实用的修复方案。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=3500
        )
        
        debug_content = response.choices[0].message.content
        
        # 生成完整的调试报告
        debug_report = f"""# {filename} 调试报告

## 文件信息
- 文件名: {filename}
- 分析时间: {import_time}
- 函数数量: {len(analyzer.functions)}
- 导入模块数量: {len(analyzer.imports)}

## 调试结果
{debug_content}

---
*此调试报告基于代码分析和AI辅助生成。它提供了可能的问题和建议，但仍需开发者的专业判断。*
"""
        return debug_report
    except Exception as e:
        error_msg = f"生成调试报告时出错: {str(e)}"
        print(error_msg)
        return f"# {filename} 调试报告\n\n## 错误\n\n{error_msg}\n\n请确保API密钥正确设置并检查网络连接。"

# 供其他模块调用的函数
async def analyze_file_for_repo(file_path, model_name=MODEL_NAME):
    """供repo_read.py调用的文件分析函数"""
    return await analyze_and_debug_file(file_path, model_name)

# 独立运行的入口点
async def run_analysis(file_path, model_name=MODEL_NAME):
    """运行分析的异步函数"""
    result = await analyze_and_debug_file(file_path, model_name)
    if result:
        print(f"完成分析，结果保存在：")
        print(f"  - 分析报告: {result['analysis_file']}")
        print(f"  - 调试报告: {result['debug_file']}")
    return result

def main():
    parser = argparse.ArgumentParser(description='Python代码分析与调试工具')
    parser.add_argument('file_path', help='要分析的Python文件路径')
    parser.add_argument('--model', default=MODEL_NAME, help='使用的AI模型')
    args = parser.parse_args()
    
    # 运行分析
    asyncio.run(run_analysis(args.file_path, args.model))

if __name__ == "__main__":
    main()
