import tempfile
from pathlib import Path
from app.configuration import set_config_path
_test_data_dir = Path(tempfile.mkdtemp(prefix='hireflow-tests-'))
_test_config = _test_data_dir / 'test.env'
_test_config.write_text(f'DATA_DIR={_test_data_dir.as_posix()}\nAI_MODE=demo\n', encoding='utf-8')
set_config_path(_test_config)
import pytest
from app.db import Base, engine, SessionLocal
from app.entities import Position

@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for name in ('Python后端工程师','Java后端工程师'):
            db.add(Position(title=name))
        db.commit()
    yield
