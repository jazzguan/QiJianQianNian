import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import trimesh
from fastapi.testclient import TestClient
from app.morphology import measure_mesh,measure_profile,normalize_mesh,diameter_of
from app.morphology_app import app
from app import morphology_routes


def cylinder(radius=2,height=12):
    mesh=trimesh.creation.cylinder(radius=radius,height=height,sections=64)
    mesh.apply_transform(trimesh.geometry.align_vectors([0,0,1],[0,1,0]))
    return mesh


class Measurements(unittest.TestCase):
    def test_rotating_calipers_rectangle_and_dense_circle(self):
        rectangle=np.array([[0,0,0],[3,0,0],[3,0,4],[0,0,4],[1,0,1]])
        self.assertAlmostEqual(diameter_of(rectangle),5)
        theta=np.linspace(0,2*np.pi,4096,endpoint=False)
        self.assertAlmostEqual(diameter_of(np.column_stack([4*np.cos(theta),np.zeros_like(theta),4*np.sin(theta)])),8)

    def test_analytic_cylinder_and_scale_translation_invariance(self):
        mesh=cylinder()
        first=measure_mesh(mesh)
        mesh.apply_scale(7);mesh.apply_translation([10,-25,4])
        second=measure_mesh(mesh)
        for key in ['height','maxBellyDiameter','mouthDiameter','footDiameter','heightBellyRatio','bellyPosition']:
            self.assertAlmostEqual(first[key],second[key],places=6)
        self.assertAlmostEqual(first['maxBellyDiameter'],10,places=4)
        self.assertAlmostEqual(first['heightBellyRatio'],3,places=4)
        self.assertAlmostEqual(first['bellyPosition'],.5,places=4)

    def test_tapered_mesh_uses_plane_intersections(self):
        mesh=cylinder(radius=1,height=12)
        factors=2+2*(mesh.vertices[:,1]+6)/12
        mesh.vertices[:,[0,2]]*=factors[:,None]
        measured=measure_mesh(mesh)
        self.assertAlmostEqual(measured['footDiameter'],10.15,delta=.08)
        self.assertAlmostEqual(measured['mouthDiameter'],19.85,delta=.08)
        self.assertGreater(measured['bellyPosition'],.98)

    def test_profile_and_landmark_position(self):
        profile=[[2,5],[5,12],[8,20],[3,25]]
        measured=measure_profile(profile)
        self.assertEqual(measured['height'],30)
        self.assertEqual(measured['maxBellyDiameter'],24)
        self.assertEqual(measured['mouthDiameter'],9)
        self.assertEqual(measured['footDiameter'],6)
        self.assertEqual(measured['bellyPosition'],.75)
        self.assertEqual(measured['bellyPositionLabel'],'偏上')
        self.assertEqual(profile[0][1],5)

    def test_up_axis_and_bottom_alignment(self):
        mesh=trimesh.creation.cylinder(radius=2,height=12,sections=64)
        normalized=normalize_mesh(mesh,'z')
        self.assertAlmostEqual(normalized.bounds[0,1],0)
        self.assertAlmostEqual(normalized.bounds[1,1],30)
        self.assertAlmostEqual(measure_mesh(normalized)['maxBellyDiameter'],10,places=4)

    def test_invalid_geometry(self):
        for profile in [[],[[1,0],[1,0]],[[1,0],[float('nan'),1]],[[0,0],[0,1]]]:
            with self.assertRaises(ValueError):measure_profile(profile)
        flat=trimesh.Trimesh(vertices=[[0,0,0],[1,0,0],[0,0,1]],faces=[[0,1,2]])
        with self.assertRaises(ValueError):measure_mesh(flat)


class Api(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.patch=patch.object(morphology_routes,'MODEL_DIR',Path(self.tmp.name));self.patch.start()
        self.client=TestClient(app)
    def tearDown(self):
        self.client.close();self.patch.stop();self.tmp.cleanup()

    def upload(self,mesh=None,axis='y'):
        return self.client.post('/api/measure/upload',data={'upAxis':axis},
            files={'file':('vessel.glb',(mesh or cylinder()).export(file_type='glb'),'model/gltf-binary')})

    def test_catalog_and_comparison_are_computed(self):
        items=self.client.get('/api/comparison/artifacts').json()
        self.assertEqual(len(items),5)
        response=self.client.post('/api/compare',json={'leftId':items[0]['id'],'rightId':items[1]['id']})
        self.assertEqual(response.status_code,200)
        pair=response.json();self.assertEqual(len(pair['rows']),6)
        self.assertEqual(pair['left']['shape'][-1][1],30)
        self.assertEqual(pair['leftMeasurement']['method'],'自动提取')
        measured=self.client.post('/api/measure',json={'artifactId':items[0]['id']}).json()
        self.assertEqual(pair['leftMeasurement'],measured)

    def test_glb_import_download_remeasure_compare(self):
        response=self.upload();self.assertEqual(response.status_code,200,response.text)
        result=response.json();url=result['modelUrl']
        downloaded=self.client.get(url);self.assertEqual(downloaded.status_code,200)
        mesh=trimesh.load(io.BytesIO(downloaded.content),file_type='glb',force='mesh')
        self.assertAlmostEqual(mesh.bounds[0,1],0);self.assertAlmostEqual(mesh.bounds[1,1],30)
        measured=self.client.post('/api/measure',json={'modelUrl':url+'?v=1'})
        self.assertEqual(measured.status_code,200)
        pair=self.client.post('/api/compare',json={'leftModelUrl':url,'leftLabel':'导入圆柱','rightId':'song-ruyao'}).json()
        self.assertEqual(pair['leftMeasurement']['source'],'mesh')
        self.assertEqual(pair['leftLabel'],'导入圆柱')
        self.assertAlmostEqual(pair['leftMeasurement']['maxBellyDiameter'],10,places=4)
        restored=self.client.get('/api/comparison/artifacts').json()
        self.assertTrue(any(x['id']==result['artifact']['id'] and x['measurementSource']=='mesh' for x in restored))
        by_id=self.client.post('/api/compare',json={'leftId':result['artifact']['id'],'rightId':'song-ruyao'})
        self.assertEqual(by_id.status_code,200)
        self.assertEqual(by_id.json()['leftMeasurement']['source'],'mesh')

    def test_scene_node_transform_is_measured(self):
        scene=trimesh.Scene()
        matrix=np.eye(4);matrix[:3,:3]*=3;matrix[:3,3]=[21,-30,50]
        scene.add_geometry(cylinder(),transform=matrix)
        response=self.upload(scene)
        self.assertEqual(response.status_code,200,response.text)
        self.assertAlmostEqual(response.json()['measurement']['heightBellyRatio'],3,places=4)

    def test_invalid_upload(self):
        bad=self.client.post('/api/measure/upload',files={'file':('wrong.glb',b'broken','model/gltf-binary')})
        self.assertEqual(bad.status_code,422)
        self.assertEqual(self.upload(axis='unknown').status_code,422)
        large=self.client.post('/api/measure/upload',files={'file':('large.glb',b'0'*(20*1024*1024+1),'model/gltf-binary')})
        self.assertEqual(large.status_code,413)

    def test_external_and_traversal_paths_rejected(self):
        for url in ['https://example.com/model.glb','file:///C:/private.glb','/api/comparison/models/../../private.glb',
                    '/files/../../private/mesh.glb','/api/comparison/models/%2e%2e.glb']:
            self.assertEqual(self.client.post('/api/measure',json={'modelUrl':url}).status_code,422)
        self.assertEqual(self.client.post('/api/measure',json={'modelUrl':'/api/comparison/models/'+str(__import__('uuid').uuid4())+'.glb'}).status_code,404)

    def test_invalid_selection(self):
        self.assertEqual(self.client.post('/api/compare',json={}).status_code,422)
        self.assertEqual(self.client.post('/api/compare',json={'leftId':'missing','rightId':'song-ruyao'}).status_code,404)
        self.assertEqual(self.client.post('/api/measure',json={'artifactId':'song-ruyao','modelUrl':'/wrong'}).status_code,422)

if __name__=='__main__':unittest.main()
