"""本地后端启动后检查基础 API，无需第三方依赖。"""
import json,sys,urllib.request
base=(sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8000').rstrip('/')
for path in ['/api/v1/health','/api/v1/stats/overview','/api/v1/applications','/api/v1/reviews']:
    try:
        with urllib.request.urlopen(base+path,timeout=8) as r:
            data=json.load(r)
            assert r.status==200
            print('[OK]',path,'items:',len(data) if isinstance(data,list) else 'object')
    except Exception as exc:
        print('[FAIL]',path,str(exc));sys.exit(1)
print('基础 API 冒烟检查通过。AI 与上传流程请在网页进行端到端验收。')
