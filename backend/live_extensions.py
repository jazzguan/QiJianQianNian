"""真实云端问答、自动演化解释及官方扫描的集成验证。"""
import os
from pathlib import Path
os.environ['QJQN_DB_PATH']=str(Path(__file__).parent/'cache'/'extensions-live.sqlite3')
from fastapi.testclient import TestClient
from app.main import app
from app import storage

with TestClient(app) as client:
    items=client.get('/api/artifacts').json()['items']
    scans=[x for x in items if x.get('geometrySource')=='scan']
    assert len(scans)>=2
    measured=client.post('/api/compare',json={'leftId':scans[0]['id'],'rightId':scans[1]['id']})
    assert measured.status_code==200,measured.text
    comparison=measured.json()
    assert comparison['leftMeasurement']['source']=='mesh'
    assert comparison['leftMeasurement']['physical']['height']>0
    assert comparison['leftMeasurement']['heightBellyRatio']>1.2
    print('REAL_SCAN_COMPARE_PASS',comparison['leftMeasurement']['physical'],flush=True)
    response=client.post('/api/ask',json={'question':'青花的蓝色颜料是什么？康熙分水有什么特点？'})
    assert response.status_code==200,response.text
    answer=response.json();assert answer['sources'] and answer['retrieval'].startswith('BGE')
    print('LIVE_SEMANTIC_RAG',answer['answer'],flush=True)
    print('SOURCES',[x['url'] for x in answer['sources']],flush=True)
    left=next(x for x in items if x['dynasty']=='song' and x.get('category')=='碗')
    right=next(x for x in items if x['dynasty']=='yuan' and x.get('category')=='碗')
    response=client.post('/api/evolution/explain',json={'artifactId':right['id'],'previousId':left['id']})
    assert response.status_code==200,response.text
    assert len(response.json()['sources'])==2
    print('LIVE_EVOLUTION_EXPLAIN',response.json()['answer'],flush=True)
    print('LIVE_EXTENSIONS_PASS',flush=True)
