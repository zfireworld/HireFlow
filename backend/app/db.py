"""配置 SQLite 连接、建表基类和请求级数据库会话。"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import DB_FILE

class Base(DeclarativeBase):
    pass

engine = create_engine(f'sqlite:///{DB_FILE}', connect_args={'check_same_thread': False}, future=True)
@event.listens_for(engine, 'connect')
def sqlite_pragmas(dbapi_connection, connection_record):
    """启用外键、等待锁超时和 WAL，改善并发读写行为。"""
    cursor = dbapi_connection.cursor()
    cursor.execute('PRAGMA foreign_keys=ON')
    cursor.execute('PRAGMA busy_timeout=5000')
    cursor.execute('PRAGMA journal_mode=WAL')
    cursor.close()

SessionLocal = sessionmaker(engine, autoflush=False, expire_on_commit=False)

def get_db():
    """为每个请求提供会话，请求结束后关闭。"""
    with SessionLocal() as db:
        yield db
