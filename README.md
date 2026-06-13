# XHS Monitor · 小红书竞品监控系统

> 一款专业的小红书竞品分析工具，支持关键词内容分析、黑马账号挖掘、爆款结构拆解、热点预警、差异化缺口分析及商业模式拆解。

![Python](https://img.shields.io/badge/Python-3.10%2B-ff4d4d?style=flat-square)
![Flask](https://img.shields.io/badge/Flask-3.0%2B-000000?style=flat-square)
![Playwright](https://img.shields.io/badge/Playwright-ready-45ba4b?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-9494a8?style=flat-square)

---

<img width="1254" height="572" alt="屏幕截图 2026-06-13 145048" src="https://github.com/user-attachments/assets/3635861b-b7f3-4364-813f-ca648b1a0400" />
<img width="1243" height="694" alt="屏幕截图 2026-06-13 145104" src="https://github.com/user-attachments/assets/17565c4e-58aa-4847-96f2-2cc5066e4e5d" />
<img width="703" height="648" alt="屏幕截图 2026-06-13 145132" src="https://github.com/user-attachments/assets/d8a529d0-2127-45c8-9c23-f3d07d42e2ea" />
<img width="1235" height="691" alt="屏幕截图 2026-06-13 145314" src="https://github.com/user-attachments/assets/1318c5ed-0500-45b5-99c7-ac3866f23f73" />


## ✦ 功能概览

### 🔍 内容分析
输入任意关键词（支持多语言），自动分析爆款标题规律，生成内容优化建议报告。

- 热门话题 TOP5
- 标题特征分析（字数、emoji 使用率、数字使用率、高频关键词）
- 标题模式分布（悬念式 / 数字式 / 对比式 / 经验分享式）
- 5 条可执行的优化建议

### 🚀 Pro 专业版工具

| 功能 | 说明 |
|---|---|
| **🐴 黑马账号识别** | 发现粉丝 < 5000、注册 < 6 个月、爆款 ≥ 2 条的高潜力新账号 |
| **🔬 爆款结构拆解** | 逐篇拆解 TOP3 高赞笔记：开头策略、内容分布、互动钩子、结尾模板 |
| **📈 热点预警系统** | 检测发布增速、多账号集中度、点赞异动，输出红/黄/绿三级预警 |
| **🧩 差异化缺口分析** | 从现有内容中发现蓝海机会，AI 生成可执行的差异化方向 |
| **💼 商业模式拆解** | 检测带货/私域/广告/知识付费占比，输出策略总结与机会点 |

### 多语言支持
- 支持中文、英文及任意语言关键词
- 自动检测语言，切换对应的分析逻辑和内容模板
- 英文昵称 + 英文标题模板 + 英文正文模板

---

## ✦ 快速启动

### 1. 安装

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python web.py
```

访问 `http://localhost:5000`

### 3. 默认密钥

```
xiaohongshu2024
```

> 修改 `.env` 文件中的 `ACCESS_KEY` 可自定义密钥。

---

## ✦ 配置说明

创建 `.env` 文件（可选）：

```env
ACCESS_KEY=你的自定义密钥
WEB_PORT=5000
```

---

## ✦ 技术栈

| 技术 | 用途 |
|---|---|
| **Flask** | Web 服务框架 |
| **Playwright** | 小红书真实数据爬取（可选） |
| **jieba** | 中文分词 |
| **Markdown** | 报告渲染 |
| **Google Fonts** | 字体系统（Archivo / Newsreader / DM Mono / Plus Jakarta Sans） |

---

## ✦ 项目结构

```
xiaohongshu-monitor/
├── web.py                  # Flask Web 主程序
├── scraper.py              # 爬虫模块（Mock + Playwright 真实爬取）
├── analyzer.py             # 分析模块（5 大 Pro 功能）
├── reporter.py             # 报告生成模块
├── notifier.py             # 微信推送模块
├── main.py                 # 命令行入口
├── config.py               # 配置文件
├── templates/              # HTML 模板
│   ├── login.html          # 登录页
│   ├── index.html          # 主界面
│   └── report.html         # 报告展示页
├── output/                 # 报告输出目录
└── requirements.txt        # Python 依赖
```

---

## ✦ 免责声明

> 本工具仅供学习与研究用途。用户应遵守小红书平台的使用条款和相关法律法规。
> 开发者不对因使用本工具而产生的任何法律问题承担责任。

---

## ✦ License

MIT License © 2026
