"""厘米标定、内壁、账号隔离、语义索引及四视角重建的验证。"""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import trimesh
from PIL import Image,ImageDraw
from fastapi.testclient import TestClient
from app import storage
from app.main import app,_run_task
from app.morphology import measure_mesh,calibrate
from app.multiview import reconstruct_views,apply_view_texture


def hollow_mesh():
    mesh=trimesh.creation.annulus(r_min=3,r_max=5,height=30,sections=80)
    mesh.apply_transform(trimesh.transformations.rotation_matrix(-np.pi/2,[1,0,0]))
    return mesh


def pictures():
    result=[]
    for color in ['red','green','blue','yellow']:
        image=Image.new('RGBA',(160,240),(255,255,255,0))
        ImageDraw.Draw(image).ellipse((40,10,120,230),fill=color)
        output=io.BytesIO();image.save(output,format='PNG');result.append(output.getvalue())
    return result


class GeometryExtensions(unittest.TestCase):
    def test_hollow_mouth_thickness_and_cm_calibration(self):
        measurement=calibrate(measure_mesh(hollow_mesh()),15)
        self.assertAlmostEqual(measurement['innerMouthDiameter'],6,delta=.02)
        self.assertAlmostEqual(measurement['wallThickness'],2,delta=.02)
        self.assertAlmostEqual(measurement['physical']['innerMouthDiameter'],3,delta=.02)
        self.assertAlmostEqual(measurement['physical']['wallThickness'],1,delta=.02)
        self.assertEqual(measurement['physical']['height'],15)
        with self.assertRaises(ValueError): calibrate(measurement,float('nan'))

    def test_solid_mesh_does_not_invent_inner_wall(self):
        mesh=trimesh.creation.cylinder(radius=5,height=30,sections=64)
        mesh.apply_transform(trimesh.transformations.rotation_matrix(-np.pi/2,[1,0,0]))
        result=calibrate(measure_mesh(mesh))
        self.assertIsNone(result['innerMouthDiameter'])
        self.assertIsNone(result['wallThickness'])
        self.assertIsNone(result['physical'])

    def test_four_view_geometry_and_back_photo(self):
        mesh,views=reconstruct_views(pictures(),resolution=48)
        self.assertAlmostEqual(mesh.extents[1],30,places=4)
        self.assertTrue(mesh.is_watertight)
        model=apply_view_texture(mesh,views)
        self.assertEqual(len(model.faces),len(mesh.faces))
        # 前后表面分别采样红色正面与蓝色背面，不能镜像复用正面。
        atlas=np.asarray(model.visual.material.baseColorTexture)
        for direction,channel in [(1,0),(-1,2)]:
            faces=np.flatnonzero(mesh.face_normals[:,2]*direction>.95)
            self.assertGreater(len(faces),0)
            uv=model.visual.uv[model.faces[faces]].mean(axis=1)
            pixels=atlas[np.clip(((1-uv[:,1])*(len(atlas)-1)).astype(int),0,len(atlas)-1),np.clip((uv[:,0]*(atlas.shape[1]-1)).astype(int),0,atlas.shape[1]-1)]
            self.assertGreater(float(pixels[:,channel].mean()),float(pixels[:,2-channel].mean())+100)


class ExtensionApiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.db=patch('app.storage.DB_PATH',str(self.root/'test.sqlite3'));self.db.start()
        self.outputs=patch('app.config.OUTPUT_DIR',str(self.root));self.outputs.start()
        storage.initialize();self.client=TestClient(app);self.other=TestClient(app)
        self.client.post('/api/auth/register',json={'username':'测量用户','password':'password-123'})
        self.other.post('/api/auth/register',json={'username':'另一用户','password':'password-456'})

    def tearDown(self):
        self.client.close();self.other.close();self.outputs.stop();self.db.stop();self.temp.cleanup()

    def test_import_axis_persistence_and_account_isolation(self):
        scene=trimesh.Scene(hollow_mesh())
        scene.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0]))
        response=self.client.post('/api/measure/upload',files={'file':('杯.glb',scene.export(file_type='glb'),'model/gltf-binary')},data={'upAxis':'z','heightCm':'15'})
        self.assertEqual(response.status_code,200,response.text)
        item=response.json()['artifact'];identifier=item['id']
        self.assertEqual(item['physicalHeightCm'],15)
        self.assertEqual(self.client.get(item['modelUrl']).status_code,200)
        self.assertEqual(self.other.get(item['modelUrl']).status_code,404)
        self.assertTrue(any(x['id']==identifier for x in self.client.get('/api/comparison/artifacts').json()))
        self.assertFalse(any(x['id']==identifier for x in self.other.get('/api/comparison/artifacts').json()))
        compared=self.client.post('/api/compare',json={'leftId':identifier,'rightId':identifier})
        self.assertEqual(compared.status_code,200,compared.text)
        self.assertEqual(compared.json()['leftMeasurement']['physical']['height'],15)
        self.assertEqual(self.other.post('/api/measure',json={'artifactId':identifier}).status_code,404)
        external=scene.export(file_type='glb')
        self.assertEqual(TestClient(app).post('/api/measure/upload',files={'file':('x.glb',external)}).status_code,401)

    def test_evolution_explanation_is_cached_and_cites_sources(self):
        item=storage.artifacts()[0]
        with patch('app.platform_routes.text_completion',return_value='馆藏记载的形态。[1]') as model:
            first=self.client.post('/api/evolution/explain',json={'artifactId':item['id']})
            second=self.client.post('/api/evolution/explain',json={'artifactId':item['id']})
            self.assertEqual(first.status_code,200,first.text)
            self.assertTrue(second.json()['cached']);self.assertEqual(model.call_count,1)
            self.assertEqual(first.json()['sources'][0]['url'],item['sources'][0]['url'])
        coverage=self.client.get('/api/evolution/coverage').json()
        self.assertEqual(len(coverage['periods']),5)
        self.assertEqual(coverage['total'],len(storage.artifacts()))

    def test_multiview_route_and_complete_local_pipeline(self):
        data=pictures();files=[('files',(f'{i}.png',value,'image/png')) for i,value in enumerate(data)]
        self.assertEqual(self.client.post('/api/reconstruct/multiview',files=files[:3]).status_code,422)
        with patch('app.main.threading.Thread'):
            response=self.client.post('/api/reconstruct/multiview',files=files)
        self.assertEqual(response.status_code,200,response.text);identifier=response.json()['taskId']
        recognition=dict(category='瓶',type='多视角器物',features=[],decorationFeatures=[],note='测试器物')
        with patch('app.main.inspect_image',return_value=recognition):
            _run_task(identifier,(self.root/(identifier+'.jpg')).read_bytes(),data)
        model=self.client.get('/api/model/'+identifier)
        self.assertEqual(model.status_code,200,model.text)
        self.assertEqual(model.json()['textureProjection']['coverage'],'multiview')
        self.assertEqual(self.other.get('/api/model/'+identifier).status_code,404)
        self.assertEqual(self.client.get(model.json()['modelUrl']).status_code,200)


class SemanticTests(unittest.TestCase):
    def test_real_bge_faiss_index_retrieval_and_update(self):
        from app.semantic import search
        with tempfile.TemporaryDirectory() as directory,patch('app.storage.DB_PATH',str(Path(directory)/'vectors.sqlite3')):
            documents=[dict(id='blue',text='青花瓷采用钴蓝颜料在釉下绘画。'),dict(id='white',text='德化白瓷常用分块模具制作观音瓷塑。')]
            self.assertEqual(search('青花的蓝色颜料是什么',documents,1)[0][1]['id'],'blue')
            with storage.connect() as db: self.assertEqual(db.execute('SELECT COUNT(*) FROM knowledge_vectors').fetchone()[0],2)
            documents[0]['text']='唐三彩是具有多种颜色的低温釉陶。'
            search('唐代三彩釉陶',documents,1)
            with storage.connect() as db: updated=db.execute('SELECT fingerprint FROM knowledge_vectors WHERE id=?',('blue',)).fetchone()[0]
            import hashlib
            self.assertEqual(updated,hashlib.sha256(documents[0]['text'].encode()).hexdigest())


if __name__=='__main__': unittest.main()
