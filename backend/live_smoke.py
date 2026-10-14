"""通过真实视觉/文本 API 与 TripoSR 验证全流程，记录在独立的 smoke 数据库。"""
import os
import time
from pathlib import Path
os.environ['QJQN_DB_PATH']=str(Path(__file__).parent/'cache'/'smoke.sqlite3')
from fastapi.testclient import TestClient
from app.main import app
from app import storage

with TestClient(app) as client:
    username='smoke-'+str(int(time.time()))
    response=client.post('/api/auth/register',json={'username':username,'password':os.urandom(16).hex()})
    assert response.status_code==200,response.text
    items=client.get('/api/artifacts').json()['items']
    item=next(x for x in items if x['dynasty']=='song')
    response=client.post('/api/ask',json={'porcelainId':item['id'],'question':'馆藏资料记载了这件器物的什么制作工艺？'})
    assert response.status_code==200,response.text
    assert response.json()['sources']
    print('LIVE_RAG',response.json()['answer'],flush=True)
    image=storage.DATA_DIR/'images'/f'{item["id"]}.jpg'
    response=client.post('/api/reconstruct',files={'file':('collection.jpg',image.read_bytes(),'image/jpeg')})
    assert response.status_code==200,response.text
    task_id=response.json()['taskId']; previous=''
    while True:
        task=client.get('/api/task/'+task_id).json()
        if task.get('stage')!=previous:
            previous=task.get('stage');print('STAGE',task,flush=True)
        if task['status']!='processing':break
        time.sleep(3)
    assert task['status']=='success',task
    model=client.get('/api/model/'+task_id).json()
    print('LIVE_VISION',model['recognition'],flush=True)
    print('LIVE_RECONSTRUCTION',model['report'],flush=True)
    assert client.get(model['modelUrl']).status_code==200
    assert client.get(model['previewUrl']).status_code==200
    assert client.post('/api/models/'+task_id+'/save').status_code==200
    response=client.post('/api/compare',json={'leftId':task_id,'leftModelUrl':model['modelUrl'],'rightId':item['id']})
    assert response.status_code==200,response.text
    assert len(response.json()['rows'])==6
    print('LIVE_END_TO_END_PASS',flush=True)
