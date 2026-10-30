"""定义实体共用的 ID 和 UTC 时间生成方法。"""
from datetime import datetime, timezone
from uuid import uuid4

def uid(): return uuid4().hex

def now(): return datetime.now(timezone.utc).replace(tzinfo=None)
