"""在临时数据库中验证规则演示和兼容模型的完整招聘流程。"""
import argparse
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))


def main():
    parser = argparse.ArgumentParser(description='使用虚构数据验证完整招聘流程，不修改现有数据库。')
    parser.add_argument('--mode', choices=['demo', 'model', 'both'], default='demo')
    parser.add_argument('--model-config', type=Path, default=ROOT / '.env',
                        help='模型配置文件，读取 MODEL_NAME、MODEL_BASE_URL 和可选 MODEL_API_KEY')
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix='hireflow-simulation-') as data_dir:
        from app.configuration.files import ConfigFileReader
        model_values=ConfigFileReader(args.model_config).read() if args.mode in ('model','both') else {}
        model_name=model_values.get('MODEL_NAME',model_values.get('QWEN_MODEL','')).strip()
        base_url=model_values.get('MODEL_BASE_URL',model_values.get('QWEN_BASE_URL','')).strip()
        api_key=model_values.get('MODEL_API_KEY',model_values.get('QWEN_API_KEY','')).strip()
        if args.mode in ('model','both') and (not model_name or not base_url):
            parser.error('测试模型时，请在 --model-config 指定的文件中配置 MODEL_NAME 和 MODEL_BASE_URL')
        from app.configuration import set_config_path
        config_file=Path(data_dir) / 'simulation.env'
        config_file.write_text(f'DATA_DIR={Path(data_dir).as_posix()}\nAI_MODE=demo\n',encoding='utf-8')
        set_config_path(config_file)
        from fastapi.testclient import TestClient
        from app.main import app
        from app.db import engine
        import logging
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('httpx2').setLevel(logging.WARNING)

        def result(response, status=200):
            if response.status_code != status:
                raise RuntimeError(f'{response.request.url.path}: HTTP {response.status_code} {response.text[:600]}')
            return response.json()

        def run_case(client, mode):
            name, position, folder = (('林沐安', 'Python后端工程师', '规则演示') if mode == 'demo'
                                      else ('周予安', '前端工程师', '模型演示'))
            config = {'mode':'demo'} if mode == 'demo' else {
                'mode':'custom', 'model':model_name, 'base_url':base_url, 'api_key':api_key or None}
            directory = ROOT / 'examples' / folder
            resume = (directory / f'简历_{name}.txt').read_bytes()
            print(f'[{mode}] 上传 {name} 的简历', flush=True)
            file_data = result(client.post('/api/v1/files', files={'file':('resume.txt', resume, 'text/plain')}), 201)
            start = time.monotonic()
            print(f'[{mode}] 正在生成简历评估...', flush=True)
            assessment = result(client.post('/api/v1/resume-assessments',json={
                'file_id':file_data['id'], 'ai_config':config}), 201)
            evaluation = assessment['evaluation']
            print(f'[{mode}] 简历评估耗时 {time.monotonic()-start:.1f} 秒；提取姓名={evaluation["candidate_name"]}，岗位={evaluation["position"]}',flush=True)
            if evaluation['candidate_name'] != name or evaluation['position'] != position:
                print(f'[{mode}] 人工修正简历姓名或岗位后继续。',flush=True)
                evaluation['candidate_name'], evaluation['position'] = name, position
            outcome = result(client.post(f"/api/v1/resume-assessments/{assessment['id']}/decision",json={
                'decision':'INTERVIEW', 'evaluation':evaluation}))
            aid=outcome['application_id']
            assert outcome['new_stage']=='ROUND1_PENDING'

            for round_no in (1,2,3):
                schedule=result(client.post(f'/api/v1/management/applications/{aid}/interview-actions',json={
                    'action':'schedule','round_no':round_no,'scheduled_at':f'2026-11-0{round_no+1} {"10:00" if mode=="demo" else "15:00"}',
                    'interviewer':('李工','王工','赵工')[round_no-1]}))
                assert schedule['new_stage']==f'ROUND{round_no}_SCHEDULED'
                detail=result(client.get(f'/api/v1/applications/{aid}'))
                interview=next(row for row in detail['interviews'] if row['round_no']==round_no)
                transcript=(directory / f'面试_{name}_{("一","二","三")[round_no-1]}面.txt').read_bytes()
                data={'ai_mode':mode if mode=='demo' else 'custom'}
                if mode=='model': data.update(ai_model=model_name,ai_base_url=base_url,ai_api_key=api_key)
                print(f'[{mode}] 正在生成第 {round_no} 轮面试总结...',flush=True)
                start=time.monotonic()
                uploaded=result(client.post(f"/api/v1/interviews/{interview['id']}/transcripts",
                    data=data,files={'file':('transcript.txt',transcript,'text/plain')}),201)
                summary=uploaded['summary']
                scored=sum(score.get('score') is not None for score in summary['scores'])
                print(f'[{mode}] 第 {round_no} 轮耗时 {time.monotonic()-start:.1f} 秒；表现 {len(summary["performance"])} 项，建议 {len(summary["suggestions"])} 项，评分 {scored}/{len(summary["scores"])} 项',flush=True)
                if (summary['candidate_name'] not in (None,name) or summary['position'] not in (None,position)
                        or summary['round_no'] not in (None,round_no)):
                    print(f'[{mode}] 人工修正面试基本信息后继续。',flush=True)
                    summary.update(candidate_name=name,position=position,round_no=round_no)
                path=f"/api/v1/interviews/{interview['id']}/transcripts/{uploaded['id']}/decision"
                if round_no == 1:
                    pending=result(client.post(path,json={'decision':'PENDING','evaluation':summary}))
                    assert pending['new_stage']=='ROUND1_FEEDBACK'
                    final=result(client.post(f'/api/v1/management/applications/{aid}/interview-actions',json={
                        'action':'feedback','round_no':1,'evaluation':'人工复核：项目经历与岗位相关。','decision':'PASS'}))
                else:
                    final=result(client.post(path,json={'decision':'PASS','evaluation':summary}))
                expected=f'ROUND{round_no+1}_PENDING' if round_no<3 else 'OFFER_PENDING'
                assert final['new_stage']==expected
                print(f'[{mode}] 第 {round_no} 轮人工确认后进入 {expected}',flush=True)

            employment=f'/api/v1/management/applications/{aid}/employment-action'
            assert result(client.post(employment,json={'target':'OFFER_ACCEPTED'}))['new_stage']=='OFFER_ACCEPTED'
            assert result(client.post(employment,json={'target':'HIRED'}))['new_stage']=='HIRED'
            detail=result(client.get(f'/api/v1/applications/{aid}'))
            assert len(detail['interviews'])==3
            assert all(iv['transcript']['review']['decision']=='PASS' for iv in detail['interviews'])
            print(f'[{mode}] 完成：已入职，3 轮面试，{len(detail["resumes"])} 份简历，{len(detail["events"])} 条事件。',flush=True)

        try:
            with TestClient(app) as client:
                modes=['demo','model'] if args.mode=='both' else [args.mode]
                failures=[]
                for mode in modes:
                    try:
                        run_case(client,mode)
                    except Exception as exc:
                        failures.append(mode)
                        print(f'[{mode}] 流程失败：{type(exc).__name__}: {exc}',flush=True)
                if failures:
                    return 1
        finally:
            engine.dispose()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
