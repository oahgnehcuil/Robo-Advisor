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

# 這裡設定：最多重試 3 次，等待時間隨次數增加（2s, 4s, 8s...），僅針對 Rate Limit 錯誤重試
@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(is_rate_limit_error),
    reraise=True # 重試失敗後最後還是會拋出錯誤供外部捕捉
)
def call_gemini_api(client, prompt):
    return client.models.generate_content(
        model="gemini-2.5-flash",
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