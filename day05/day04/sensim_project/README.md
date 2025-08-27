# Sensim - 传感器数据模拟器与分析工具
![测试覆盖率](https://img.shields.io/badge/coverage-95%25-green)

一个用于嵌入式系统开发的传感器数据处理工具，支持数据生成、异常检测和统计分析，
帮助开发者快速验证传感器数据处理算法。

## 功能特点
- 生成多种类型的模拟传感器数据
- 支持 Z-score 和 IQR 两种异常值过滤算法
- 自动分析数据统计特征与趋势
- 提供直观的命令行界面和可编程 API
- 完善的测试用例确保可靠性

## 安装方法

### 使用 pipx（推荐，隔离环境）
```bash
pipx install git+https://github.com/yourusername/sensim.git
# 首次使用建议：pipx ensurepath  sada sacomasda