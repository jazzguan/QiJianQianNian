"""新问答功能的真实 API 验证，使用独立测试数据库。"""
import os
import time
from pathlib import Path
os.environ['QJQN_DB_PATH']=str(Path(__file__).parent/'cache'/'smoke.sqlite3')
from fastapi.testclient import TestClient
from app.main import app
from app.platform_routes import learning_tasks

with TestClient(app) as client:
    client.post('/api/auth/register',json={'username':'platform-'+str(int(time.time())),'password':os.urandom(16).hex()})
    task=next(x for x in learning_tasks(True) if x.get('inputType')=='text')
    response=client.post('/api/learning/attempts',json={'taskId':task['id'],'answer':task['correctAnswer']})
    assert response.status_code==200,response.text
    assert response.json()['correct'],response.text
    print('LIVE_GRADING_PASS',response.json()['feedback'],flush=True)
    items=client.get('/api/artifacts').json()['items']
    left=next(x for x in items if x['dynasty']=='song')
    right=next(x for x in items if x['dynasty']=='yuan' and x['category']==left['category'])
    response=client.post('/api/compare/explain',json={'leftId':left['id'],'rightId':right['id']})
    assert response.status_code==200,response.text
    assert len(response.json()['sources'])==2
    print('LIVE_COMPARE_EXPLAIN_PASS',response.json()['answer'],flush=True)
