"""账号隔离、资料检索和学习记录的集成测试。"""
import io
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app, startup
from app import storage
from app.platform_routes import learning_tasks
from app.providers import parse_object,ProviderError


class PlatformTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=patch('app.storage.DB_PATH',str(Path(self.temp.name)/'test.sqlite3'));self.db.start()
        storage.initialize()
        self.client=TestClient(app)
        self.other=TestClient(app)
        self.user=self.client.post('/api/auth/register',json={'username':'甲用户','password':'correct-password'}).json()
        self.other_user=self.other.post('/api/auth/register',json={'username':'乙用户','password':'another-password'}).json()
        self.items=storage.artifacts()

    def tearDown(self):
        self.client.close();self.other.close();self.db.stop();self.temp.cleanup()

    def test_auth_and_expiration(self):
        self.assertEqual(self.client.get('/api/auth/me').json()['user']['id'],self.user['id'])
        self.assertEqual(TestClient(app).post('/api/auth/login',json={'username':'甲用户','password':'wrong-password'}).status_code,401)
        with storage.connect() as db:
            password=db.execute('SELECT password FROM users WHERE id=?',(self.user['id'],)).fetchone()[0]
            self.assertNotIn('correct-password',password)
            db.execute('UPDATE sessions SET expires=0 WHERE user_id=?',(self.user['id'],))
        self.assertEqual(self.client.get('/api/learning').status_code,401)

    def test_library_filters_and_sources(self):
        self.assertGreaterEqual(len(self.items),5)
        item=self.items[0]
        found=self.client.get('/api/artifacts',params={'dynasty':item['dynasty'],'category':item['category'],'q':item['name']}).json()['items']
        self.assertTrue(any(x['id']==item['id'] for x in found))
        for x in found:
            self.assertEqual(x['dynasty'],item['dynasty']);self.assertEqual(x['license'],'CC0');self.assertTrue(x['sources'])
        self.assertEqual(self.client.get('/api/porcelain/does-not-exist').status_code,404)

    def test_matching_respects_category(self):
        category=self.items[0]['category']
        matches=self.client.post('/api/evolution/match',json={'category':category,'features':[]}).json()['matches']
        self.assertEqual(len(matches),5)
        for match in matches:
            if match['porcelainId']: self.assertEqual(storage.artifact_by_id(match['porcelainId'])['category'],category)
        unknown=self.client.post('/api/evolution/match',json={'category':'不存在的器型','features':[]}).json()['matches']
        self.assertTrue(all(x['porcelainId'] is None and x['emptyReason'] for x in unknown))

    def test_favorites_progress_and_server_grading(self):
        item=self.items[0]
        self.assertEqual(self.client.post('/api/favorites/'+item['id']).status_code,200)
        self.client.post('/api/learning/events',json={'artifactId':item['id'],'durationSeconds':59})
        task=learning_tasks(True)[0]
        public=self.client.get('/api/learning/tasks').json()['items'][0]
        self.assertNotIn('correctAnswer',public)
        result=self.client.post('/api/learning/attempts',json={'taskId':task['id'],'answer':task['correctAnswer']}).json()
        self.assertTrue(result['correct'])
        summary=self.client.get('/api/learning').json()
        self.assertEqual(summary['completedTasks'],1);self.assertEqual(summary['durationSeconds'],59)
        self.assertIn(item['id'],summary['favorites'])
        self.assertEqual(self.other.get('/api/learning').json()['favorites'],[])
        self.client.post('/api/learning/attempts',json={'taskId':task['id'],'answer':task['correctAnswer']})
        self.assertEqual(self.client.get('/api/learning').json()['completedTasks'],1)

    def test_rag_binds_selected_artifact(self):
        item=self.items[0]
        with patch('app.knowledge.text_completion',return_value='馆方记载的工艺。[1]') as model:
            answer=self.client.post('/api/ask',json={'porcelainId':item['id'],'question':'这件器物是什么工艺？'}).json()
            self.assertEqual(answer['sources'][0]['url'],item['sources'][0]['url'])
            self.assertEqual(len(answer['sources']),1)
            prompt=model.call_args.args[0][-1]['content']
            self.assertIn(item['name'],prompt);self.assertIn(item['summary'],prompt)
        with patch('app.knowledge.text_completion',side_effect=ProviderError('服务超时')):
            self.assertEqual(self.client.post('/api/ask',json={'porcelainId':item['id'],'question':'制作工艺'}).status_code,502)

    def test_model_privacy_persistence_and_restart(self):
        task_id='11111111-1111-4111-8111-111111111111'
        storage.save_reconstruction(task_id,{'taskId':task_id,'status':'success','porcelain':{'id':task_id},'created':time.time()},self.user['id'])
        self.assertEqual(self.client.get('/api/model/'+task_id).status_code,200)
        self.assertEqual(self.other.get('/api/model/'+task_id).status_code,404)
        self.assertEqual(self.other.get('/api/task/'+task_id).status_code,404)
        self.assertEqual(self.other.post('/api/models/'+task_id+'/save').status_code,404)
        self.assertEqual(self.other.post('/api/learning/events',json={'artifactId':task_id}).status_code,404)
        self.assertEqual(self.client.post('/api/models/'+task_id+'/save').status_code,200)
        storage._initialized=None
        self.assertTrue(self.client.get('/api/models').json()['items'][0]['saved'])
        storage.save_reconstruction('interrupted',{'status':'processing'},self.user['id'])
        startup();self.assertEqual(storage.reconstruction('interrupted')['status'],'error')

    def test_upload_validation_and_vision(self):
        self.assertEqual(TestClient(app).post('/api/reconstruct',files={'file':('image.jpg',b'invalid','image/jpeg')}).status_code,401)
        self.assertEqual(self.client.post('/api/reconstruct',files={'file':('image.jpg',b'invalid','image/jpeg')}).status_code,422)
        image=io.BytesIO();Image.new('RGB',(50,50),'white').save(image,format='PNG')
        with patch('app.platform_routes.vision_completion',return_value={'category':'碗','type':'白色碗','features':['宽口'],'note':'可见碗状器物'}):
            response=self.client.post('/api/recognize',files={'file':('image.png',image.getvalue(),'image/png')})
            self.assertEqual(response.json()['category'],'碗')
        self.assertEqual(parse_object('```json\n{"category":"罐"}\n```')['category'],'罐')
        with self.assertRaises(ProviderError):parse_object('[]')

    def test_explanation_grading_uses_collection_evidence(self):
        task=next(x for x in learning_tasks(True) if x.get('inputType')=='text')
        with patch('app.platform_routes.text_completion',return_value='{"correct":true,"feedback":"表达了馆藏记载的工艺。"}') as model:
            result=self.client.post('/api/learning/attempts',json={'taskId':task['id'],'answer':task['correctAnswer']})
            self.assertTrue(result.json()['correct'])
            self.assertIn(task['correctAnswer'],model.call_args.args[0][-1]['content'])
        self.assertEqual(self.client.get('/api/learning').json()['completedTasks'],1)
        with patch('app.platform_routes.text_completion',return_value='{"correct":"yes"}'):
            self.assertEqual(self.client.post('/api/learning/attempts',json={'taskId':task['id'],'answer':'学生的解释文字'}).status_code,502)

if __name__=='__main__':unittest.main()
