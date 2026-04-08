from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from google import genai
import os

app = FastAPI()

class SummaryRequest(BaseModel):
    company_name: str
    ticker: str
    latest: dict
    series: list

@app.post("/api/summary")
def generate_summary(req: SummaryRequest):
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return {
                "summary": "AI 摘要目前未啟用，因為缺少 GEMINI_API_KEY。"
            }

        client = genai.Client(api_key=api_key)

        trimmed_series = req.series[-24:] if len(req.series) > 24 else req.series

        prompt = f"""
你是一個金融 dashboard 助理。

請只根據提供的資料，用繁體中文寫一段簡短摘要。
內容包含：
1. 最近 mNAV 與股價的變化
2. 這可能代表的意義
3. 一句保守提醒

不要使用 markdown 標題，不要條列太多點，直接寫成簡潔自然的摘要。

公司：{req.company_name}
Ticker：{req.ticker}
最新資料：{req.latest}
最近資料：{trimmed_series}
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return {"summary": response.text}

    except Exception as e:
        msg = str(e)

        if "429" in msg or "Too Many Requests" in msg or "RESOURCE_EXHAUSTED" in msg:
            return {
                "summary": "AI 摘要暫時無法取得，因為目前觸發 Gemini rate limit。請稍後再試。"
            }

        return JSONResponse(
            status_code=500,
            content={"error": msg}
        )

handler = app