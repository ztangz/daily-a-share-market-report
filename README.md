# A股每日复盘自动化

这个项目用于在收盘后自动采集 A 股市场快照，并生成一个可托管到 GitHub Pages 的静态 HTML 看板。

## 功能

- 关键指数：上证指数、深证成指、沪深300、创业板指、科创50、中证500、中证1000、北证50
- 市场宽度：上涨家数、下跌家数、平盘家数、成交额
- 板块行情：行业板块涨跌榜、概念热度
- 涨停复盘：涨停、跌停、炸板的近似识别
- 风格观察：按流通市值构造的微盘股代理指标
- 自动化：GitHub Actions 北京时间 16:15 自动生成并部署到 GitHub Pages

## 本地运行

Windows 当前如果 `python` 指向 Microsoft Store alias，需要改用真实 Python 路径运行。

```powershell
python -m src.run_daily
```

生成结果：

- `data/raw/YYYY-MM-DD/snapshot.json`
- `data/processed/YYYY-MM-DD/market.json`
- `data/market.db`
- `reports/latest.html`
- `site/index.html`

## GitHub Pages 设置

首次推送到 GitHub 后，在仓库设置中打开 Pages，并选择 `GitHub Actions` 作为发布来源。之后工作流会在每个交易日北京时间 16:15 自动运行。

## 注意

涨停、跌停、炸板使用行情字段和板块涨跌停规则近似识别，适合日常复盘，不等同于交易所官方统计。
