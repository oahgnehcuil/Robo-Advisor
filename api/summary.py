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
            return JSONResponse(
                status_code=500,
                content={"error": "Missing GEMINI_API_KEY"}
            )

        client = genai.Client(api_key=api_key)

        trimmed_series = req.series[-24:] if len(req.series) > 24 else req.series

        prompt = f"""
You are a financial dashboard assistant.

Based only on the provided data, write a concise dashboard summary in Traditional Chinese.
Do not mention missing tools or APIs.
Do not ask follow-up questions.
Do not use markdown headings.

Please provide:
1. A short summary of the recent movement in mNAV and stock price
2. A short interpretation of what the change may imply
3. A short caution about uncertainty

Data:
Company name: {req.company_name}
Ticker: {req.ticker}
Latest data: {req.latest}
Recent series: {trimmed_series}
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return {"summary": response.text}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

handler = app