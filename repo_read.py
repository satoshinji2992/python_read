import os
import sys
import asyncio
import json
import argparse
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

# 导入自定义模块
from python_read import PythonCodeAnalyzer, analyze_python_file_async
from analyze_issue import analyze_file_for_repo

class RepoAnalyzer:
    """使用REACT方法的代码仓库分析器"""
    
    def __init__(self, repo_path: str, output_dir: Optional[str] = None, max_concurrency: int = 5, debug_mode: bool = False):
        """初始化仓库分析器
        
        Args:
            repo_path: 要分析的代码仓库路径
            output_dir: 分析结果输出目录，默认为仓库路径下的_analysis子目录
            max_concurrency: 最大并发分析任务数
        """
        self.repo_path = os.path.abspath(repo_path)
        self.output_dir = output_dir or os.path.join(self.repo_path, "_analysis")
        self.max_concurrency = max_concurrency
        self.debug_mode = debug_mode

        self.python_files = []
        self.analysis_results = {}
        self.file_dependency_graph = {}
        self.module_index = {}
        self.semaphore = asyncio.Semaphore(max_concurrency)
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 初始化日志
        self.log_file = os.path.join(self.output_dir, "analysis_log.md")
        
    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"**[{timestamp}]** {message}\n\n")
        print(f"[{timestamp}] {message}")
        
    async def analyze_repo(self):
        """分析整个代码仓库，使用REACT方法自动规划策略"""
        self.log("# 开始仓库分析\n")
        
        # 步骤1: 思考 - 收集仓库信息
        await self.reason_about_repo()
        
        # 步骤2: 行动 - 执行分析任务
        await self.act_on_analysis_plan()
        
        # 步骤3: 反思 - 生成综合报告和洞察
        await self.reflect_on_results()
        
        self.log("# 仓库分析完成\n")
        return self.analysis_results
    
    async def reason_about_repo(self):
        """思考阶段：收集信息并规划分析策略"""
        self.log("## 思考阶段：收集仓库信息并规划分析策略\n")
        
        # 收集所有Python文件
        self.log("### 寻找Python文件\n")
        for root, _, files in os.walk(self.repo_path):
            # 跳过_analysis、.git、__pycache__等目录
            if any(skip_dir in root for skip_dir in ["_analysis", ".git", "__pycache__", "venv", ".venv", "env"]):
                continue
                
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.repo_path)
                    self.python_files.append({
                        "path": file_path, 
                        "rel_path": rel_path
                    })
        
        self.log(f"找到 {len(self.python_files)} 个Python文件")
        
        # 确定文件分析优先级
        self.log("### 确定文件分析优先级\n")
        
        # 1. 先检查是否有明显的入口点文件
        entry_points = []
        for file_info in self.python_files:
            file_path = file_info["path"]
            file_name = os.path.basename(file_path)
            
            # 识别可能的入口点文件
            if file_name in ["main.py", "app.py", "run.py", "server.py", "cli.py"]:
                entry_points.append(file_info)
                file_info["priority"] = 10  # 高优先级
            elif "test" in file_name.lower():
                file_info["priority"] = 1   # 低优先级
            else:
                file_info["priority"] = 5   # 中优先级
                
        self.log(f"识别到可能的入口点文件: {', '.join([os.path.basename(ep['path']) for ep in entry_points])}" if entry_points else "未识别到明显的入口点文件")
        
        # 2. 按文件大小和路径深度排序（小文件优先，路径浅的优先）
        for file_info in self.python_files:
            file_size = os.path.getsize(file_info["path"])
            path_depth = file_info["rel_path"].count(os.path.sep)
            
            # 调整优先级: 小文件+浅路径=优先处理
            size_factor = min(1.0, 10000 / max(1000, file_size))  # 文件越小，系数越接近1
            depth_factor = 1.0 / (path_depth + 1)                 # 路径越浅，系数越大
            
            # 综合优先级
            file_info["priority"] = file_info.get("priority", 5) * size_factor * depth_factor
        
        # 按优先级排序
        self.python_files.sort(key=lambda x: x["priority"], reverse=True)
        
        top_files = [os.path.basename(f["path"]) for f in self.python_files[:5]]
        self.log(f"分析优先级最高的文件: {', '.join(top_files)}")
        
        # 3. 为每个文件创建分析任务
        self.log("### 创建分析任务计划\n")
        batch_size = min(self.max_concurrency, len(self.python_files))
        self.log(f"将使用最大{self.max_concurrency}个并发任务进行分析")
    
    async def act_on_analysis_plan(self):
        """行动阶段：执行分析任务"""
        self.log("## 行动阶段：执行文件分析\n")
        
        # 创建进度跟踪
        total_files = len(self.python_files)
        completed = 0
        
        # 创建分析任务
        tasks = []
        for file_info in self.python_files:
            tasks.append(self.analyze_single_file(file_info))
            
        # 开始分析
        self.log(f"开始分析 {total_files} 个文件...")
        
        # 异步执行所有任务，使用semaphore控制并发
        results = await asyncio.gather(*tasks)
        
        # 处理结果
        for file_info, result in zip(self.python_files, results):
            if result:
                file_info["analysis_result"] = result
                self.analysis_results[file_info["rel_path"]] = result
                
        self.log(f"已完成 {len(self.analysis_results)}/{total_files} 个文件的分析")
        
    async def analyze_single_file(self, file_info):
        """分析单个Python文件"""
        file_path = file_info["path"]
        rel_path = file_info["rel_path"]
        
        # 使用信号量控制并发
        async with self.semaphore:
            try:
                self.log(f"开始分析: {rel_path}")
                
                # 使用analyze_issue.py中的函数进行分析
                result = await analyze_file_for_repo(file_path, debug=self.debug_mode)
                
                if result:
                    self.log(f"✓ 完成分析: {rel_path}")
                    
                    # 将分析报告移动到输出目录
                    if "analysis_file" in result and os.path.exists(result["analysis_file"]):
                        new_path = os.path.join(self.output_dir, f"{rel_path.replace('/', '_')}_analysis.md")
                        os.rename(result["analysis_file"], new_path)
                        result["analysis_file"] = new_path
                        
                    # 将调试报告移动到输出目录
                    if "debug_file" in result and os.path.exists(result["debug_file"]):
                        new_path = os.path.join(self.output_dir, f"{rel_path.replace('/', '_')}_debug.md")
                        os.rename(result["debug_file"], new_path)
                        result["debug_file"] = new_path
                        
                    return result
                else:
                    self.log(f"✗ 分析失败: {rel_path}")
                    return None
            except Exception as e:
                self.log(f"✗ 分析出错: {rel_path} - {str(e)}")
                return None
        
    async def reflect_on_results(self):
        """反思阶段：生成综合报告和洞察"""
        self.log("## 反思阶段：生成综合报告\n")
        
        if not self.analysis_results:
            self.log("没有成功的分析结果，无法生成综合报告")
            return
            
        # 1. 构建模块和函数的索引
        self.log("### 构建模块和函数索引")
        
        module_index = {}  # 模块名 -> 文件路径列表
        function_index = {}  # 函数名 -> 文件路径列表
        dependency_graph = {}  # 文件路径 -> 依赖的文件路径列表
        
        for rel_path, result in self.analysis_results.items():
            if "analyzer" not in result:
                continue
                
            analyzer = result["analyzer"]
            file_path = analyzer.file_path
            
            # 索引导入的模块
            for module_name in analyzer.imports:
                if module_name not in module_index:
                    module_index[module_name] = []
                module_index[module_name].append(rel_path)
                
            # 索引函数
            for function in analyzer.functions:
                func_name = function["name"]
                if func_name not in function_index:
                    function_index[func_name] = []
                function_index[func_name].append(rel_path)
                
            # 构建文件依赖关系
            dependencies = set()
            for module_name in analyzer.imports:
                # 查找仓库内的模块依赖
                for other_path in self.analysis_results:
                    other_name = os.path.splitext(os.path.basename(other_path))[0]
                    if module_name == other_name or module_name.endswith(f".{other_name}"):
                        dependencies.add(other_path)
                        
            dependency_graph[rel_path] = list(dependencies)
            
        # 保存索引
        index_file = os.path.join(self.output_dir, "repo_index.json")
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump({
                "modules": module_index,
                "functions": function_index,
                "dependencies": dependency_graph
            }, f, indent=2)
            
        self.log(f"索引已保存至: {index_file}")
        
        # 2. 生成仓库概览报告
        self.log("### 生成仓库概览报告")
        
        # 准备报告内容
        overview = f"# 代码仓库分析报告: {os.path.basename(self.repo_path)}\n\n"
        overview += f"**分析时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        overview += f"**仓库路径:** {self.repo_path}\n"
        overview += f"**Python文件总数:** {len(self.python_files)}\n"
        overview += f"**成功分析文件数:** {len(self.analysis_results)}\n\n"
        
        # 添加文件列表
        overview += "## 文件列表\n\n"
        overview += "| 文件 | 函数数 | 导入模块数 | 分析报告 | 调试报告 |\n"
        overview += "|------|--------|------------|----------|----------|\n"
        
        for rel_path, result in self.analysis_results.items():
            if "analyzer" in result:
                analyzer = result["analyzer"]
                func_count = len(analyzer.functions)
                import_count = len(analyzer.imports)
                
                analysis_link = f"[分析报告]({os.path.basename(result.get('analysis_file', ''))})" if result.get('analysis_file') else "无"
                debug_link = f"[调试报告]({os.path.basename(result.get('debug_file', ''))})" if result.get('debug_file') else "无"
                
                overview += f"| {rel_path} | {func_count} | {import_count} | {analysis_link} | {debug_link} |\n"
        
        # 添加依赖关系图
        overview += "\n## 文件依赖关系\n\n"
        overview += "```\n"
        for file, deps in dependency_graph.items():
            if deps:
                overview += f"{file} 依赖:\n"
                for dep in deps:
                    overview += f"  └─ {dep}\n"
        overview += "```\n\n"
        
        # 添加主要问题概览（从调试报告中提取）
        overview += "## 主要发现的问题\n\n"
        problem_count = 0
        
        for rel_path, result in self.analysis_results.items():
            if "debug_report" in result and result["debug_report"]:
                debug_report = result["debug_report"]
                
                # 查找"潜在bug"或"问题"部分
                problem_sections = []
                if "## 潜在bug分析" in debug_report:
                    start = debug_report.find("## 潜在bug分析")
                    end = debug_report.find("##", start + 5)
                    if end == -1:
                        end = len(debug_report)
                    problem_sections.append(debug_report[start:end])
                
                if problem_sections:
                    overview += f"### {rel_path} 中的问题\n\n"
                    for section in problem_sections:
                        overview += section + "\n\n"
                    problem_count += 1
        
        if problem_count == 0:
            overview += "没有发现明显的问题。\n\n"
        
        # 保存概览报告
        overview_file = os.path.join(self.output_dir, "repo_overview.md")
        with open(overview_file, "w", encoding="utf-8") as f:
            f.write(overview)
            
        self.log(f"仓库概览报告已保存至: {overview_file}")
        
        # 3. 生成入口点调用图
        for entry_file in [f["path"] for f in self.python_files[:5]]:  # 优先级最高的5个文件
            self.log(f"分析入口点文件: {os.path.basename(entry_file)}")
            # 这里可以添加更深入的入口点分析...
        
        # 4. 使用AI生成仓库综合总结
        self.log("### 使用AI生成仓库综合总结")
        try:
            # 导入repo_summary模块
            import repo_summary
            
            # 调用repo_summary模块生成综合报告
            summary_file = await repo_summary.generate_repo_summary(
                analysis_dir=self.output_dir,
                output_file=os.path.join(self.output_dir, "repo_ai_summary.md")
            )
            
            if summary_file:
                self.log(f"AI生成的仓库综合总结已保存至: {summary_file}")
            else:
                self.log("AI生成仓库总结失败")
        except ImportError:
            self.log("未找到repo_summary模块，跳过AI总结生成")
        except Exception as e:
            self.log(f"生成AI总结时出错: {str(e)}")
        
        self.log("综合分析完成")
        
async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Python代码仓库分析工具")
    parser.add_argument("repo_path", help="要分析的代码仓库路径")
    parser.add_argument("--output", help="分析结果输出目录")
    parser.add_argument("--concurrency", type=int, default=5, help="最大并发分析任务数")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    
    args = parser.parse_args()
    
    analyzer = RepoAnalyzer(
        repo_path=args.repo_path,
        output_dir=args.output,
        max_concurrency=args.concurrency,
        debug_mode=args.debug
    )
    
    await analyzer.analyze_repo()

if __name__ == "__main__":
    asyncio.run(main())