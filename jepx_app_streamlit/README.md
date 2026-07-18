# jepx_app_streamlit
# JEPX Price Prediction App (Streamlit)

このアプリは、JEPXスポット価格・短期予備率・週間予備率を入力し、翌日・翌々日の価格を予測する Streamlit アプリです。

## 必要ファイル
- `app.py`（アプリ本体）
- `requirements.txt`（依存ライブラリ）
- `saved_models/` フォルダ  
  - `model_day1_*.txt`
  - `model_day2_*.txt`

## Streamlit Cloud で動かす方法
1. このリポジトリをアップロードする  
2. https://share.streamlit.io にアクセス  
3. 「New app」→ このリポジトリ → `app.py` を選択して Deploy

## 入力するCSV
- スポット価格（spot）
- 短期予備率（short）
- 週間予備率（weekly）

## 出力
- 翌日予測（df_pred1）
- 翌々日予測（df_pred2）
- prediction_data_final.csv（特徴量セット）
