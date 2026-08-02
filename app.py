# ============================================
# ブロック1：spot_summary CSV を読み込み、df_area を作成
# ============================================

import pandas as pd
import streamlit as st
import numpy as np


# スポットサマリー（spot_summary_* と同じ列構造の CSV）
spot_file = st.file_uploader("スポットサマリーCSVを選択（列構造が spot_summary_* と同じもの）", type=["csv"])

if spot_file is not None:
    # --- spot_summary 読み込み ---
    df_spot = pd.read_csv(spot_file, encoding="cp932")

    # 受渡日を datetime に変換
    df_spot["受渡日"] = pd.to_datetime(df_spot["受渡日"], errors="coerce")

    # 時刻コード（1〜48）→ 30分刻みの時間（分）
    df_spot["時刻"] = (df_spot["時刻コード"] - 1) * 30

    # datetime を作成
    df_spot["datetime"] = df_spot["受渡日"] + pd.to_timedelta(df_spot["時刻"], unit="m")

    # --- melt して area × datetime × jepx_price に変換 ---
    df_area = df_spot.melt(
        id_vars=["datetime"],
        value_vars=[
            "エリアプライス北海道(円/kWh)",
            "エリアプライス東北(円/kWh)",
            "エリアプライス東京(円/kWh)",
            "エリアプライス中部(円/kWh)",
            "エリアプライス北陸(円/kWh)",
            "エリアプライス関西(円/kWh)",
            "エリアプライス中国(円/kWh)",
            "エリアプライス四国(円/kWh)",
            "エリアプライス九州(円/kWh)"
        ],
        var_name="area",
        value_name="jepx_price"
    )

    # area 名を短縮名に変換
    df_area["area"] = (
        df_area["area"]
        .str.replace("エリアプライス", "")
        .str.replace("(円/kWh)", "")
    )

    st.write("スポットサマリー（df_area）")
    st.dataframe(df_area.head())


# ============================================
# ブロック2：spot_summary の過去3日を df_prev として作成
# ============================================

if spot_file is not None:
    # 最新日を取得
    latest_date = df_spot["受渡日"].max()

    # ★ 過去3日分を抽出
    start_date = latest_date - pd.Timedelta(days=3)

    mask = (
        (df_area["datetime"].dt.date >= start_date.date()) &
        (df_area["datetime"].dt.date <= latest_date.date())
    )

    df_prev = df_area[mask].copy()

    # slot（1〜48）
    df_prev["slot"] = (
        df_prev["datetime"].dt.hour * 2 +
        (df_prev["datetime"].dt.minute // 30) +
        1
    )

    df_prev = df_prev.sort_values(["area", "slot"])

    st.write("過去3日分スポット（df_prev）")
    st.dataframe(df_prev.head())

# ============================================
# ブロック3：短期予備率CSVを読み込み、df_res2 を作成
# ============================================

short_file = st.file_uploader(
    "短期予備率CSVを選択（short_term_reserve.csv と同じ列構造）",
    type=["csv"]
)

if short_file is not None:
    df_res = pd.read_csv(short_file, encoding="cp932")

    df_res["対象年月日"] = pd.to_datetime(df_res["対象年月日"], errors="coerce")
    df_res["時刻"] = pd.to_timedelta(df_res["時刻"] + ":00") - pd.to_timedelta(30, unit="m")
    df_res["datetime"] = df_res["対象年月日"] + df_res["時刻"]

    df_res2 = df_res[["datetime", "エリア", "広域予備率(%)"]].copy()
    df_res2.columns = ["datetime", "area", "reserve_ratio"]

    st.write("df_res2")
    st.dataframe(df_res2.head())

# ============================================
# ブロック4：df_prev に短期予備率を結合
# ============================================

if spot_file is not None and short_file is not None:
    df_prev = df_prev.merge(df_res2, on=["datetime", "area"], how="left")

    cols_prev = df_prev.columns
    if "reserve_ratio_x" in cols_prev and "reserve_ratio_y" in cols_prev:
        df_prev["reserve_ratio"] = df_prev["reserve_ratio_y"]
        df_prev = df_prev.drop(columns=["reserve_ratio_x", "reserve_ratio_y"])

    st.write("df_prev（短期予備率結合後）")
    st.dataframe(df_prev.head())

# ============================================
# ブロック5：翌日・翌々日の datetime を生成
# ============================================

if spot_file is not None and short_file is not None:
    prev_date = df_prev["datetime"].dt.date.max()

    pred1_date = prev_date + pd.Timedelta(days=1)
    pred2_date = prev_date + pd.Timedelta(days=2)

    times_pred1 = pd.date_range(start=pd.Timestamp(pred1_date), periods=48, freq="30min")
    times_pred2 = pd.date_range(start=pd.Timestamp(pred2_date), periods=48, freq="30min")

    areas = df_prev["area"].unique()

    df_pred1 = pd.DataFrame({
        "datetime": np.repeat(times_pred1, len(areas)),
        "area": np.tile(areas, len(times_pred1))
    })

    df_pred2 = pd.DataFrame({
        "datetime": np.repeat(times_pred2, len(areas)),
        "area": np.tile(areas, len(times_pred2))
    })

    st.write("df_pred1（翌日）")
    st.dataframe(df_pred1.head())

    st.write("df_pred2（翌々日）")
    st.dataframe(df_pred2.head())

# ============================================
# ブロック6：過去3日＋予測日1＋予測日2を結合
# ============================================

if spot_file is not None and short_file is not None:
    # ★ フィルタを消す（過去3日分すべてを使う）
    df_prev_use = df_prev[["datetime", "area", "jepx_price", "reserve_ratio"]].copy()

    df_all = pd.concat(
        [df_prev_use, df_pred1, df_pred2],
        ignore_index=True
    )

    st.write("df_all（過去3日＋翌日＋翌々日）")
    st.dataframe(df_all.head())

# ============================================
# ブロック7：エリア座標
# ============================================

area_coords = {
    "北海道": (43.06417, 141.34694),
    "東北": (39.70361, 141.15250),
    "東京": (35.68944, 139.69167),
    "中部": (35.18028, 136.90667),
    "北陸": (36.59444, 136.62556),
    "関西": (34.68639, 135.52),
    "中国": (34.66167, 133.935),
    "四国": (34.06583, 134.55944),
    "九州": (33.60639, 130.41806)
}


# ============================================
# ブロック8：気象データ取得 → 補間 → df_all に結合（過去3日＋予測日2まで）
# ============================================

import requests

def fetch_weather(lat, lon, start_date, end_date):
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        "&hourly=temperature_2m,shortwave_radiation"
        f"&start_date={start_date}&end_date={end_date}"
        "&timezone=Asia/Tokyo"
    )
    r = requests.get(url)
    return r.json()

def interpolate_weather(weather_json):
    df = pd.DataFrame({
        "datetime": pd.to_datetime(weather_json["hourly"]["time"]),
        "temp": weather_json["hourly"]["temperature_2m"],
        "solar": weather_json["hourly"]["shortwave_radiation"]
    })
    df = df.set_index("datetime").resample("30min").interpolate(limit_direction="both")
    return df.reset_index()

if spot_file is not None and short_file is not None:
    # ★ 過去3日分＋予測日2まで
    start_date_weather = (prev_date - pd.Timedelta(days=3)).strftime("%Y-%m-%d")
    end_date_weather   = (pred1_date + pd.Timedelta(days=2)).strftime("%Y-%m-%d")

    weather_all = []
    for area, (lat, lon) in area_coords.items():
        wjson = fetch_weather(lat, lon, start_date_weather, end_date_weather)
        wdf = interpolate_weather(wjson)
        wdf["area"] = area
        weather_all.append(wdf)

    df_weather = pd.concat(weather_all, ignore_index=True)

    df_all = df_all.merge(df_weather, on=["datetime", "area"], how="left")

    st.write("df_all（気象データ結合後）")
    st.dataframe(df_all.head())

# ============================================
# ブロック9：週間予備率CSVを読み込み → ピボット → df_all に結合
# ============================================

weekly_file = st.file_uploader(
    "週間予備率CSVを選択（weekly_reserve.csv と同じ列構造）",
    type=["csv"]
)

if weekly_file is not None and spot_file is not None and short_file is not None:
    df_week = pd.read_csv(weekly_file, encoding="cp932")
    df_week["対象年月日"] = pd.to_datetime(df_week["対象年月日"], errors="coerce")

    df_week_pivot = df_week.pivot_table(
        index=["対象年月日", "エリア"],
        columns="区分",
        values="広域予備率(%)"
    ).reset_index()

    df_week_pivot = df_week_pivot.rename(columns={
        "対象年月日": "date",
        "エリア": "area",
        "最大需要": "weekly_max_reserve",
        "最小予備率": "weekly_min_reserve"
    })

    df_all["date"] = df_all["datetime"].dt.date
    df_week_pivot["date"] = df_week_pivot["date"].dt.date

    df_all = df_all.merge(
        df_week_pivot,
        on=["date", "area"],
        how="left",
        suffixes=("", "_new")
    )

    for col in ["weekly_max_reserve", "weekly_min_reserve"]:
        new_col = col + "_new"
        if new_col in df_all.columns:
            df_all[col] = df_all[col].fillna(df_all[new_col])
            df_all = df_all.drop(columns=[new_col])

    df_all = df_all.drop(columns=["date"])

    st.write("df_all（週間予備率結合後）")
    st.dataframe(df_all.head())

# ============================================
# ブロック10：曜日（weekday）＋祝日（holiday=0/1）を付与
# ============================================

if spot_file is not None and short_file is not None:
    # 曜日（0=月曜, 6=日曜）
    df_all["weekday"] = df_all["datetime"].dt.weekday

    # 祝日判定（0=平日, 1=祝日）
    import jpholiday
    df_all["holiday"] = df_all["datetime"].dt.date.apply(
        lambda x: 1 if jpholiday.is_holiday(x) else 0
    )

    st.write("df_all（曜日＋祝日付与後）")
    st.dataframe(df_all.head())


# ============================================
# ブロック11：予測日1モデル用の特徴量生成（学習コードと完全一致）
# ============================================

if spot_file is not None and short_file is not None and weekly_file is not None:

    import numpy as np

    # -----------------------------
    # ① slot（30分コマ番号）
    # -----------------------------
    df_all["slot"] = df_all["datetime"].dt.hour * 2 + df_all["datetime"].dt.minute // 30

    # -----------------------------
    # ② 平日・休日フラグ
    # -----------------------------
    df_all["is_holiday_like"] = ((df_all["weekday"] >= 5) | (df_all["holiday"] == 1)).astype(int)

    # -----------------------------
    # ③ 平日ラグ（48コマ前）
    # -----------------------------
    df_weekday = df_all[df_all["is_holiday_like"] == 0].copy()
    df_weekday["price_prev_weekday"] = df_weekday.groupby("area")["jepx_price"].shift(48)

    # -----------------------------
    # ④ 休日ラグ（48コマ前）
    # -----------------------------
    df_holiday = df_all[df_all["is_holiday_like"] == 1].copy()
    df_holiday["price_prev_holiday"] = df_holiday.groupby("area")["jepx_price"].shift(48)

    # -----------------------------
    # ⑤ マージ（48コマ前）
    # -----------------------------
    df_all = df_all.merge(
        df_weekday[["datetime", "area", "price_prev_weekday"]],
        on=["datetime", "area"],
        how="left"
    )

    df_all = df_all.merge(
        df_holiday[["datetime", "area", "price_prev_holiday"]],
        on=["datetime", "area"],
        how="left"
    )

    # -----------------------------
    # ⑥ 前日価格・気象（48コマ前）
    # -----------------------------
    df_all["jepx_price_prev"] = df_all.groupby("area")["jepx_price"].shift(48)

    df_all["jepx_price_prev_ma3"] = (
        df_all.groupby("area")["jepx_price_prev"]
              .rolling(3)
              .mean()
              .reset_index(level=0, drop=True)
    )

    df_all["temp_prev"]  = df_all.groupby("area")["temp"].shift(48)
    df_all["solar_prev"] = df_all.groupby("area")["solar"].shift(48)

    df_all["temp_diff"]  = df_all["temp"]  - df_all["temp_prev"]
    df_all["solar_diff"] = df_all["solar"] - df_all["solar_prev"]

    # -----------------------------
    # ⑦ 予備率（48コマ前）
    # -----------------------------
    df_all["reserve_ratio_prev"] = df_all.groupby("area")["reserve_ratio"].shift(48)
    df_all["reserve_ratio_diff"] = df_all["reserve_ratio"] - df_all["reserve_ratio_prev"]

    df_all["reserve_ratio_inv"] = 1.0 / (df_all["reserve_ratio"] + 1e-6)

    threshold = 5.0
    df_all["reserve_low_gap"] = np.maximum(0.0, threshold - df_all["reserve_ratio"])

    # -----------------------------
    # ⑧ 週間予備率（48コマ前）
    # -----------------------------
    df_all["weekly_max_reserve_prev"] = df_all.groupby("area")["weekly_max_reserve"].shift(48)
    df_all["weekly_min_reserve_prev"] = df_all.groupby("area")["weekly_min_reserve"].shift(48)

    df_all["weekly_max_reserve_diff"] = df_all["weekly_max_reserve"] - df_all["weekly_max_reserve_prev"]
    df_all["weekly_min_reserve_diff"] = df_all["weekly_min_reserve"] - df_all["weekly_min_reserve_prev"]

    # -----------------------------
    # ⑨ 前々日（96コマ前）
    # -----------------------------
    df_all["jepx_price_prev_96"] = df_all.groupby("area")["jepx_price"].shift(96)

    df_all["temp_prev_96"]  = df_all.groupby("area")["temp"].shift(96)
    df_all["solar_prev_96"] = df_all.groupby("area")["solar"].shift(96)

    df_all["temp_diff_96"]  = df_all["temp"]  - df_all["temp_prev_96"]
    df_all["solar_diff_96"] = df_all["solar"] - df_all["solar_prev_96"]

    df_all["reserve_ratio_prev_96"] = df_all.groupby("area")["reserve_ratio"].shift(96)
    df_all["reserve_ratio_diff_96"] = df_all["reserve_ratio"] - df_all["reserve_ratio_prev_96"]

    # 平日ラグ（96コマ前）
    df_weekday_96 = df_all[df_all["is_holiday_like"] == 0].copy()
    df_weekday_96["price_prev_weekday_96"] = df_weekday_96.groupby("area")["jepx_price"].shift(96)

    df_all = df_all.merge(
        df_weekday_96[["datetime", "area", "price_prev_weekday_96"]],
        on=["datetime", "area"],
        how="left"
    )

    # 休日ラグ（96コマ前）
    df_holiday_96 = df_all[df_all["is_holiday_like"] == 1].copy()
    df_holiday_96["price_prev_holiday_96"] = df_holiday_96.groupby("area")["jepx_price"].shift(96)

    df_all = df_all.merge(
        df_holiday_96[["datetime", "area", "price_prev_holiday_96"]],
        on=["datetime", "area"],
        how="left"
    )

    # -----------------------------
    # ⑩ 欠損埋め（48系＋96系）
    # -----------------------------
    cols_fill_zero = [
        "price_prev_weekday",
        "price_prev_holiday",
        "jepx_price_prev",
        "jepx_price_prev_ma3",
        "temp_prev",
        "solar_prev",
        "temp_diff",
        "solar_diff",
        "reserve_ratio_prev",
        "reserve_ratio_diff",
        "reserve_ratio_inv",
        "reserve_low_gap",
        "weekly_max_reserve_prev",
        "weekly_min_reserve_prev",
        "weekly_max_reserve_diff",
        "weekly_min_reserve_diff",
        "jepx_price_prev_96",
        "temp_prev_96",
        "solar_prev_96",
        "temp_diff_96",
        "solar_diff_96",
        "reserve_ratio_prev_96",
        "reserve_ratio_diff_96",
        "price_prev_weekday_96",
        "price_prev_holiday_96",
    ]

    df_all[cols_fill_zero] = df_all[cols_fill_zero].fillna(0)

    st.write("予測日1モデル用の特徴量生成が完了しました")
    st.dataframe(df_all.head())

# ============================================
# ブロック12：prediction_data_final.csv の保存
# ============================================

required_cols = [
    "weekly_max_reserve",
    "weekly_min_reserve",
    "weekly_max_reserve_prev",
    "weekly_min_reserve_prev",
    "weekly_max_reserve_diff",
    "weekly_min_reserve_diff"
]

# まず df_all が存在するか確認
if 'df_all' in globals():

    # 次に必要な列が揃っているか確認
    if all(col in df_all.columns for col in required_cols):

        cols = [
            "datetime", "area", "slot",
            "jepx_price_prev_ma3",
            "reserve_ratio", "reserve_ratio_prev", "reserve_ratio_diff",
            "reserve_ratio_inv", "reserve_low_gap",
            "weekday", "holiday",
            "temp", "solar", "temp_diff", "solar_diff",
            "price_prev_weekday", "price_prev_holiday",
            "weekly_max_reserve", "weekly_min_reserve",
            "weekly_max_reserve_prev", "weekly_min_reserve_prev",
            "weekly_max_reserve_diff", "weekly_min_reserve_diff"
        ]

        # ここで初めて csv_data が作られる
        csv_data = df_all[cols].to_csv(index=False, encoding="utf-8-sig")

        # download_button は必ずガードの中に置く
        st.write("prediction_data_final.csv をダウンロードできます")
        st.download_button(
            label="prediction_data_final.csv をダウンロード",
            data=csv_data,
            file_name="prediction_data_final.csv",
            mime="text/csv"
        )



# ============================================
# ブロック14：予測日1・予測日2の特徴量抽出
# ============================================

if spot_file is not None and short_file is not None and weekly_file is not None:
    # 予測日1（翌日）
    pred1_date = prev_date + pd.Timedelta(days=1)
    df_pred1 = df_all[df_all["datetime"].dt.date == pred1_date].copy()

    # 予測日2（翌々日）
    pred2_date = prev_date + pd.Timedelta(days=2)
    df_pred2 = df_all[df_all["datetime"].dt.date == pred2_date].copy()

    st.write(f"予測日1行数: {len(df_pred1)}")
    st.write(f"予測日2行数: {len(df_pred2)}")

    st.write("df_pred1（翌日）")
    st.dataframe(df_pred1.head())

    st.write("df_pred2（翌々日）")
    st.dataframe(df_pred2.head())

# ============================================
# ブロック15：特徴量セット（学習コードと一致）
# ============================================

if spot_file is not None and short_file is not None and weekly_file is not None:
    feature_cols_day1 = [
        "slot",
        "jepx_price_prev_ma3",
        "reserve_ratio",
        "reserve_ratio_prev",
        "reserve_ratio_diff",
        "reserve_ratio_inv",
        "reserve_low_gap",
        "weekday",
        "holiday",
        "temp",
        "solar",
        "temp_diff",
        "solar_diff",
        "price_prev_weekday",
        "price_prev_holiday"
    ]

    feature_cols_day2 = [
        "slot",
        "weekday",
        "holiday",
        "temp",
        "solar",
        "jepx_price_prev_96",
        "temp_prev_96",
        "solar_prev_96",
        "temp_diff_96",
        "solar_diff_96",
        "reserve_ratio_prev_96",
        "reserve_ratio_diff_96",
        "price_prev_weekday_96",
        "price_prev_holiday_96",
        "weekly_max_reserve",
        "weekly_min_reserve",
        "weekly_max_reserve_prev",
        "weekly_min_reserve_prev",
        "weekly_max_reserve_diff",
        "weekly_min_reserve_diff",
    ]

    st.write("特徴量セット（予測日1・予測日2）を定義しました")
    st.write("feature_cols_day1:", feature_cols_day1)
    st.write("feature_cols_day2:", feature_cols_day2)

# ============================================
# ブロック16：LightGBM Booster の読み込み（エリア別）
# ============================================

if spot_file is not None and short_file is not None and weekly_file is not None:
    import lightgbm as lgb
    from pathlib import Path

    BASE_DIR = Path(__file__).parent
    MODELS_DIR = BASE_DIR / "saved_models"

    models_day1_loaded = {}
    models_day2_loaded = {}

    for area in areas:
        path1 = MODELS_DIR / f"model_day1_{area}.txt"
        path2 = MODELS_DIR / f"model_day2_{area}.txt"

        if not path1.exists():
            st.error(f"Day1モデルが見つかりません: {path1}")
            continue
        if not path2.exists():
            st.error(f"Day2モデルが見つかりません: {path2}")
            continue

        models_day1_loaded[area] = lgb.Booster(model_file=str(path1))
        models_day2_loaded[area] = lgb.Booster(model_file=str(path2))

    st.success("saved_models フォルダからモデルを読み込みました")

# ============================================
# ブロック17：予測日1の予測（エリア別）
# ============================================

# 必要な変数が揃っていない段階では絶対に実行しない
required_vars = ['areas', 'df_pred1', 'feature_cols_day1', 'models_day1_loaded']
if all(name in globals() for name in required_vars):

    preds_day1 = []

    for area in areas:
        df_area = df_pred1[df_pred1["area"] == area].copy()
        X_pred = df_area[feature_cols_day1]

        booster = models_day1_loaded[area]
        y_pred = booster.predict(X_pred)

        df_area["pred_day1"] = y_pred
        preds_day1.append(df_area)

    df_pred1_out = pd.concat(preds_day1, ignore_index=True)

    st.write("予測日1の予測が完了しました")
    st.dataframe(df_pred1_out.head())

# ============================================
# ブロック18：予測日2の予測（エリア別）
# ============================================

required_vars = ['areas', 'df_pred2', 'feature_cols_day2', 'models_day2_loaded']
if all(name in globals() for name in required_vars):

    preds_day2 = []

    for area in areas:
        df_area = df_pred2[df_pred2["area"] == area].copy()
        X_pred = df_area[feature_cols_day2]

        booster = models_day2_loaded[area]
        y_pred = booster.predict(X_pred)

        df_area["pred_day2"] = y_pred
        preds_day2.append(df_area)

    df_pred2_out = pd.concat(preds_day2, ignore_index=True)

    st.write("予測日2の予測が完了しました")
    st.dataframe(df_pred2_out.head())

# ============================================
# ブロック19：予測結果をCSVとしてダウンロード
# ============================================

required_vars = ['df_pred1_out', 'df_pred2_out', 'pred1_date']
# weekly_max_reserve が df_all に存在するかもチェック
if all(name in globals() for name in required_vars) and "weekly_max_reserve" in df_all.columns:

    df_result = pd.concat([
        df_pred1_out[["datetime", "area", "pred_day1"]],
        df_pred2_out[["datetime", "area", "pred_day2"]]
    ], ignore_index=True)

    save_date = pred1_date.strftime("%Y%m%d")
    filename = f"result_{save_date}.csv"

    csv_data = df_result.to_csv(index=False, encoding="utf-8-sig")

    st.write("予測結果のCSVをダウンロードできます")
    st.download_button(
        label="予測結果をダウンロード",
        data=csv_data,
        file_name=filename,
        mime="text/csv"
    )

    st.dataframe(df_result.head())
