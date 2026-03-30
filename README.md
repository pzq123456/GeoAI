# 启动指南

本项目是一个基于 AI 的地理空间分析工具，利用 GIS 数据与智能代理提供地块分析、空间计算和可视化服务。

## 环境要求

- **Python 版本**: 3.12
- **包管理工具**: uv (高性能 Python 包管理器)
- 需要获取 DeepSeek API 密钥以访问 AI 模型服务

## 快速启动

### 1. 安装 uv (如未安装)

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. 克隆项目并进入目录

```bash
git clone <your-repo-url>
cd <project-folder>
```

### 3. 创建虚拟环境并安装依赖

```bash
# 使用 uv 创建 Python 3.12 虚拟环境
uv venv --python 3.12

# 激活虚拟环境
# macOS / Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# 安装项目依赖
uv pip install -r requirements.txt
```

### 4. 配置环境变量

复制示例环境变量文件并填入您的 DeepSeek API 密钥：

```bash
cp .env.example .env
```

编辑 `.env` 文件，添加您的 API 密钥：

```
DEEPSEEK_API_KEY=your-api-key-here
```

### 5. 准备数据文件

确保在 `data/` 目录下存在以下 GeoJSON 文件：

- `park.json` - 公园/地块数据
- `poi.json` - 兴趣点数据

如果目录或文件不存在，程序将自动创建 `data` 目录，但您需要自行准备数据文件。

### 6. 运行项目

```bash
python main.py
```

## 项目结构

```
├── data/               # 数据目录 (GeoJSON 文件)
├── main.py             # 主程序入口
├── .env                # 环境变量 (需自行创建)
├── .env.example        # 环境变量示例
└── README.md           # 本文件
```

## 注意事项

- 确保 `data/` 目录下包含 `park.json` 和 `poi.json`，否则工具无法加载空间数据。
- 首次运行可能较慢，因为需要加载模型和空间数据。
- 若遇到 `FileNotFoundError`，请检查数据文件是否存在。

## 常见问题

### Q: 提示“缺少数据文件”怎么办？
A: 请将您的 GeoJSON 文件放入 `data/` 目录，并确保文件名与代码中一致。

### Q: 如何修改 Python 版本？
A: 本工具明确需要 Python 3.12，请使用 `pyenv` 或 `uv` 管理版本。

### Q: 如何更新依赖？
A: 使用 `uv pip install -r requirements.txt --upgrade` 更新到最新版本。