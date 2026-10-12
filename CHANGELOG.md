# Changelog

本项目遵循语义化版本。格式参考 [Keep a Changelog](https://keepachangelog.com/)。

## [v0.2.0] - 2026-10-12

### Added
- **MCP 数据源**：原生支持 Streamable HTTP MCP 服务（已用麦当劳官方 MCP 实测通过）
- **字段抽取**：从 MCP 文本返回中用正则抽字段，支持 `{"op":"count"}` 计数模式
- **派生计算** `compute`：`days_until`（到期倒数）、`last_date`（取串中最后日期）
- **双模式隐私隔离**：`demo` 脱敏可公开 / `--live` 真实数据按 `sensitive` 标记自动隔离到 `output/live/`（已 gitignore）
- **GitHub Pages 在线演示**：无需安装即可查看活文档效果
- **双语 README**：中文主体 + 英文摘要 + 完整 `README_EN.md`
- **ROADMAP**：按投入产出比排序的提升路线

### Changed
- `generator.py` 重构：`data_source`（单对象）→ `data_sources`（数组，向后兼容旧格式）
- 产物文件名跟随 spec 名（`<name>.html` / `<name>.jimeng.md`），多规格互不覆盖

## [v0.1.0] - 2026-10-09

### Added
- 初始 PoC：`.livedoc` 规格格式、生成器原型、季度报告示例
- 活文档预览（HTML）+ 即梦数字分身分镜讲稿（Markdown）
