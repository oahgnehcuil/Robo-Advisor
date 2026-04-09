import pandas as pd
import json
from mnav import get_btc_history, fetch_company_data, COMPANIES

def run_diagnostic():
    print("🔍 [開始診斷] 直接呼叫 mnav.py 內部函式...")
    
    period = "14d"
    interval = "1d"

    # --- 步驟 1: 測試 BTC 抓取 ---
    print(f"\n1️⃣ 測試 BTC 抓取 (Ticker: BTC-USD)... ")
    btc_hist = get_btc_history(period, interval)
    
    if btc_hist.empty:
        print("❌ 錯誤: BTC 歷史資料為空！")
        print("💡 建議：檢查網路連線，或 yfinance 是否被 Yahoo 擋掉 IP。")
        return
    else:
        print(f"✅ 成功: 抓到 {len(btc_hist)} 筆 BTC 資料。")
        print(f"   最新一筆日期: {btc_hist.index[-1]}")
        print(f"   最新價格: {btc_hist['Close'].iloc[-1]:.2f}")

    # --- 步驟 2: 測試各別公司資料 ---
    print("\n2️⃣ 測試公司資料抓取與 mNAV 計算...")
    
    for company_key in COMPANIES.keys():
        print(f"\n--- 正在處理 {company_key} ({COMPANIES[company_key]['name']}) ---")
        
        result = fetch_company_data(company_key, period, interval, btc_hist)
        
        if "error" in result:
            print(f"❌ 錯誤: {result['error']}")
        else:
            latest = result['latest']
            print(f"✅ 計算成功!")
            print(f"   股票價格: {latest['stock_close']}")
            print(f"   BTC 價格 : {latest['btc_close']}")
            print(f"   mNAV 值  : {latest['mnav']}")
            print(f"   市值估計: {latest['market_cap_approx']}")

    print("\n" + "="*30)
    print("✨ 診斷結束")

if __name__ == "__main__":
    run_diagnostic()