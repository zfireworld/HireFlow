from pathlib import Path
import subprocess
import sys

import pytest
from app.configuration.files import ConfigFileReader
from app.storage.files import FileStorage


def test_configuration_reads_file_without_expanding_environment(tmp_path, monkeypatch):
    monkeypatch.setenv('PRIVATE_MODEL_SECRET', 'process-secret')
    path=tmp_path / 'settings.env'
    path.write_text('MODEL_NAME=from-file\nMODEL_API_KEY="${PRIVATE_MODEL_SECRET}"\n',encoding='utf-8')
    values=ConfigFileReader(path).read()
    assert values['MODEL_NAME']=='from-file'
    assert values['MODEL_API_KEY']=='${PRIVATE_MODEL_SECRET}'
    assert ConfigFileReader(tmp_path/'missing.env').read()=={}


def test_file_storage_rejects_paths_outside_root(tmp_path):
    root=tmp_path/'uploads';root.mkdir()
    storage=FileStorage(root)
    path=storage.write('resume.txt',b'test')
    assert storage.existing(path)==path
    assert storage.existing(tmp_path/'other.txt') is None
    with pytest.raises(ValueError): storage.write('../outside.txt',b'test')
    with pytest.raises(ValueError): storage.remove(tmp_path/'outside.txt')
    storage.remove(path)
    assert not path.exists()


def test_application_configuration_ignores_process_environment(tmp_path, monkeypatch):
    path=tmp_path/'app.env'
    data=tmp_path/'file-data'
    path.write_text(f'DATA_DIR={data.as_posix()}\nAI_MODE=model\nMODEL_NAME=file-model\n',encoding='utf-8')
    monkeypatch.setenv('AI_MODE','demo')
    monkeypatch.setenv('DATA_DIR',str(tmp_path/'wrong-data'))
    monkeypatch.setenv('QWEN_MODEL','wrong-model')
    code=("from pathlib import Path; from app.configuration import set_config_path; "
          f"set_config_path(Path({str(path)!r})); "
          "from app.config import AI_MODE, DATA_DIR, MODEL_NAME; "
          "print(AI_MODE); print(DATA_DIR); print(MODEL_NAME)")
    result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,check=True)
    lines=result.stdout.splitlines()
    assert lines==['model',str(data),'file-model']
    assert not (tmp_path/'wrong-data').exists()


def test_server_model_mode_can_use_unauthenticated_compatible_service(tmp_path):
    path=tmp_path/'app.env'
    path.write_text(f'DATA_DIR={(tmp_path / "data").as_posix()}\nAI_MODE=model\n'
                    'MODEL_NAME=example-model\nMODEL_BASE_URL=http://127.0.0.1:8123/v1\n',encoding='utf-8')
    code=("from pathlib import Path; from app.configuration import set_config_path; "
          f"set_config_path(Path({str(path)!r})); "
          "from app.services.model_settings import is_demo, require_model, model_name; "
          "require_model(); print(is_demo()); print(model_name())")
    result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,check=True)
    assert result.stdout.splitlines()==['False','example-model']
