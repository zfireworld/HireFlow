"""向 HiFlow Webhook 发送招聘事件。"""
import httpx
from ..config import HIFLOW_WEBHOOK_URL

async def send_event(payload: dict, event_id: str) -> None:
    """附带事件 ID 发送；HTTP 错误由同步队列负责记录和重试。"""
    async with httpx.AsyncClient(timeout=10) as client:
        result = await client.post(HIFLOW_WEBHOOK_URL, json=payload,
                                   headers={'X-HireFlow-Event-ID':event_id})
        result.raise_for_status()
