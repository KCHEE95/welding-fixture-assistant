# 焊接工装设计副驾驶

这是一个基于 Streamlit 的辅助工具，用于快速生成钣金焊接工装的设计思路。  
上传 STL 模型，选择产品类型，即可获得老师傅般的工装建议。

## 部署到 Streamlit Cloud

1. Fork 或下载本仓库。
2. 登录 https://share.streamlit.io ，点击 "New app"。
3. 选择本仓库，设置主文件为 `app.py`。
4. 点击 Deploy，等待部署完成即可使用。

## 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
