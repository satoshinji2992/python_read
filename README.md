# 代码仓库分析工具 (repo_read)



一个智能的代码仓库分析工具，使用REACT(Reasoning, Acting, and Reflecting)方法自动分析Python代码仓库，生成详细的分析报告和改进建议。特别适合分析AI生成的代码项目，包括深度学习模型实现。**仓库理解还在施工中**

## 特性

- 🧠 **REACT方法**: 使用思考、行动、反思三阶段策略自动分析代码库
- 🔍 **智能优先级排序**: 自动识别入口点文件并优化分析顺序
- ⚡ **异步并行分析**: 通过异步IO加速分析过程，支持并发控制
- 📊 **全面分析报告**: 生成函数文档、代码流程分析和变量信息
- 🐞 **调试建议**: 使用AI识别潜在问题并提供具体修复方案
- 🔗 **依赖关系追踪**: 构建模块间依赖图和函数调用关系
- 📑 **仓库级报告**: 提供整个仓库的概览和关键见解
- 🧮 **深度学习代码支持**: 特别优化用于分析深度学习模型实现

## 安装

1. 克隆仓库:
```bash
git clone https://github.com/yourusername/repo_read.git
cd repo_read
```

2. 安装依赖:
```bash
pip install -r requirements.txt
```

3. 设置环境变量:
```bash
# 设置必要的API密钥(支持OpenAI API和兼容格式的API)
export API_KEY="your_api_key_here"
export BASE_URL="https://api.deepseek.com"  # 或其他兼容OpenAI API的服务
export MODEL_NAME="deepseek-chat"  # 或其他支持的模型
```

## 使用方法

### 基本用法

分析整个代码仓库:
```bash
python repo_read.py /path/to/your/repository
```

### 高级选项

```bash
# 指定输出目录
python repo_read.py /path/to/repo --output /path/to/output_dir

# 调整并发任务数(适用于大型项目)
python repo_read.py /path/to/repo --concurrency 8
```

### 单文件分析

如果只想分析单个文件:
```bash
python analyze_issue.py /path/to/your/file.py
```

### RAG增强分析

在生成基础报告后，可以使用RAG技术进一步分析:
```bash
python report_analyzer.py /path/to/analysis_directory
```

## 工作流程

1. **收集与规划 (Reasoning)**
   - 扫描仓库中的所有Python文件
   - 识别可能的入口点文件
   - 基于文件特征分配优先级

2. **分析执行 (Acting)**
   - 并行分析各个Python文件
   - 提取模块、函数和依赖信息
   - 生成每个文件的分析报告和调试建议

3. **综合报告 (Reflecting)**
   - 构建模块和函数索引
   - 创建依赖关系图
   - 整合所有分析结果生成仓库概览

## 输出内容

分析完成后，将在指定的输出目录(默认为`<repo_path>/_analysis`)中生成:

- `<file>_analysis.md`: 每个文件的详细分析
- `<file>_debug.md`: 每个文件的调试建议
- `repo_overview.md`: 仓库概览报告
- `repo_index.json`: 函数和模块索引
- `analysis_log.md`: 分析过程日志

## 深度学习项目分析

本工具特别适合分析AI生成的深度学习代码:

- 识别常见深度学习框架(PyTorch, TensorFlow等)
- 分析模型架构和层定义
- 理解训练流程和优化方法
- 检测神经网络实现中的潜在问题

## 项目结构

```
repo_read/
├── python_read.py     # 单文件代码分析
├── analyze_issue.py   # 代码调试建议生成
├── repo_read.py       # 仓库级分析协调
├── report_analyzer.py # RAG增强分析
└── requirements.txt   # 项目依赖
```

## 扩展与集成

- **CI/CD集成**: 使用GitHub Actions自动分析PR
- **VSCode扩展**: 在编辑器中查看分析结果
- **自定义分析器**: 添加特定领域的分析逻辑

## 贡献

欢迎贡献！请先fork本项目，创建feature branch，再提交PR。

## 许可证

MIT

---

*注意: 本工具需要API密钥才能运行。分析质量取决于所使用的模型能力。*