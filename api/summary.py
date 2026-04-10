from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from google import genai
import os
import logging
# 引入重試機制工具
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

app = FastAPI()

# 定義什麼樣的錯誤需要重試（針對 Rate Limit）
def is_rate_limit_error(exception):
    msg = str(exception)
    return "429" in msg or "Too Many Requests" in msg or "RESOURCE_EXHAUSTED" in msg

class SummaryRequest(BaseModel):
    company_name: str
    ticker: str
    latest: dict
    series: list

# 更新判定函數，納入 503 錯誤
def is_retryable_error(exception):
    msg = str(exception)
    # 429: Rate Limit, 503: Service Unavailable, 500: Internal Server Error
    retryable_codes = ["429", "503", "500", "RESOURCE_EXHAUSTED", "UNAVAILABLE"]
    return any(code in msg for code in retryable_codes)

# 調整重試策略
@retry(
    stop=stop_after_attempt(5), # 增加到 5 次，因為 503 通常稍縱即逝
    wait=wait_exponential(multiplier=1, min=2, max=15), # 最長等待 15 秒
    retry=retry_if_exception(is_retryable_error),
    reraise=True
)
def call_gemini_api(client, prompt):
    # 注意：這裡使用的是 gemini-2.0-flash (目前穩定版主流名稱可能是 1.5 或 2.0)
    # 如果你指的是 2.0 系列，請確保名稱正確
    return client.models.generate_content(
        model="gemini-2.0-flash", 
        contents=prompt
    )

@app.post("/api/summary")
def generate_summary(req: SummaryRequest):
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return {"summary": "AI 摘要目前未啟用，因為缺少 GEMINI_API_KEY。"}

        client = genai.Client(api_key=api_key)
        trimmed_series = req.series[-24:] if len(req.series) > 24 else req.series

        prompt = f"""
你是一個金融 dashboard 助理。
請只根據提供的資料，用繁體中文寫一段簡短摘要。
公司：{req.company_name} ({req.ticker})
最新資料：{req.latest}
最近資料：{trimmed_series}
"""

        # 呼叫帶有重試機制的 function
        response = call_gemini_api(client, prompt)
        return {"summary": response.text}

    except Exception as e:
        msg = str(e)
        # 如果重試了 3 次還是失敗，最後會走到這裡
        if is_rate_limit_error(e):
            return {
                "summary": "AI 服務目前過於繁忙，嘗試自動重連失敗。請稍候幾分鐘再手動重新整理。"
            }

        return JSONResponse(
            status_code=500,
            content={"error": msg}
        )

handler = app