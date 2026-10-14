"""运行：python -m unittest test_morphology -v（backend 目录）。"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import trimesh
from fastapi.testclient import TestClient

from app.main import app
from app.morphology import measure_mesh, measure_profile
from app import storage
from app.uncertainty import orient_upright,normalize_mesh


class MorphologyTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.db_patch=patch('app.storage.DB_PATH',str(Path(self.directory.name)/'test.sqlite3'))
        self.db_patch.start()
        self.client = TestClient(app)
        self.user=self.client.post('/api/auth/register',json={'username':'tester','password':'test-password'}).json()
        self.items=storage.artifacts()

    def tearDown(self):
        self.db_patch.stop()
        self.directory.cleanup()

    @staticmethod
    def cylinder():
        mesh = trimesh.creation.cylinder(radius=2, height=10, sections=64)
        mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
        return mesh

    def test_cylinder_known_dimensions(self):
        result = measure_mesh(self.cylinder())
        self.assertAlmostEqual(result['height'], 30)
        self.assertAlmostEqual(result['maxBellyDiameter'], 12, places=4)
        self.assertAlmostEqual(result['mouthDiameter'], 12, places=4)
        self.assertAlmostEqual(result['footDiameter'], 12, places=4)
        self.assertAlmostEqual(result['heightBellyRatio'], 2.5, places=4)
        self.assertAlmostEqual(result['bellyPosition'], .5, places=4)

    def test_scale_and_translation_invariance(self):
        mesh = self.cylinder()
        first = measure_mesh(mesh)
        mesh.apply_scale(7)
        mesh.apply_translation([100, -20, 300])
        second = measure_mesh(mesh)
        for key in ['maxBellyDiameter', 'mouthDiameter', 'footDiameter', 'heightBellyRatio', 'bellyPosition']:
            self.assertAlmostEqual(first[key], second[key], places=5)

    def test_profile_known_shape_and_belly_position(self):
        result = measure_profile([[2, 5], [5, 12], [1, 15]])
        self.assertAlmostEqual(result['maxBellyDiameter'], 30)
        self.assertAlmostEqual(result['mouthDiameter'], 6)
        self.assertAlmostEqual(result['footDiameter'], 12)
        self.assertAlmostEqual(result['bellyPosition'], .7)
        self.assertEqual(result['bellyPositionLabel'], '偏上')

    def test_invalid_geometry(self):
        for profile in [[], [[1, 0], [2, 0]], [[-1, 0], [2, 1]], [[1, 0], [float('nan'), 1]]]:
            with self.assertRaises(ValueError):
                measure_profile(profile)
        with self.assertRaises(ValueError):
            measure_mesh(trimesh.Trimesh())

    def test_z_up_reconstruction_keeps_top_up(self):
        mesh=trimesh.creation.cone(radius=2,height=10,sections=64)
        upright=normalize_mesh(orient_upright(mesh),30)
        measured=measure_mesh(upright)
        self.assertLess(measured['mouthDiameter'],measured['footDiameter'])
        self.assertAlmostEqual(upright.bounds[0,1],0)
        self.assertAlmostEqual(upright.bounds[1,1],30)

    def test_historical_compare_and_measure(self):
        response = self.client.post('/api/compare', json={'leftId': self.items[0]['id'], 'rightId': self.items[1]['id']})
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(len(result['rows']), 6)
        self.assertEqual(result['leftMeasurement']['source'], 'profile')
        self.assertAlmostEqual(result['leftMeasurement']['heightBellyRatio'], 30/(2*max(r for r,y in self.items[0]['shape'])))
        for side in ['leftMeasurement', 'rightMeasurement']:
            self.assertEqual(result[side]['height'], 30)
        response = self.client.post('/api/measure', json={'artifactId': self.items[2]['id']})
        self.assertEqual(response.status_code, 200)

    def test_glb_scene_transform_and_uploaded_compare(self):
        task_id = '11111111-1111-4111-8111-111111111111'
        storage.save_reconstruction(task_id,{'status':'success'},self.user['id'])
        scene = trimesh.Scene()
        transform = trimesh.transformations.translation_matrix([4, 12, 7])
        scene.add_geometry(self.cylinder(), transform=transform)
        with tempfile.TemporaryDirectory() as directory, patch('app.config.OUTPUT_DIR', directory):
            scene.export(str(Path(directory) / f'{task_id}.glb'))
            url = f'http://localhost:8000/files/{task_id}/mesh.glb'
            result = self.client.post('/api/measure', json={'modelUrl': url})
            self.assertEqual(result.status_code, 200, result.text)
            self.assertAlmostEqual(result.json()['heightBellyRatio'], 2.5, places=4)
            result = self.client.post('/api/compare', json={
                'leftId': 'uploaded', 'leftModelUrl': url, 'rightId': self.items[1]['id']})
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json()['leftMeasurement']['source'], 'mesh')

    def test_api_invalid_inputs(self):
        for payload in [{}, {'modelUrl': 'file:///etc/passwd'}, {'modelUrl': 'http://localhost/files/../main.py'},
                        {'artifactId': 'unknown'}, {'artifactId': 'song-ruyao', 'modelUrl': 'test'}]:
            result = self.client.post('/api/measure', json=payload)
            self.assertIn(result.status_code, [404, 422])
        result = self.client.post('/api/compare', json={'leftId': 'unknown', 'rightId': 'song-ruyao'})
        self.assertEqual(result.status_code, 404)

    def test_same_artifact_comparison(self):
        result = self.client.post('/api/compare', json={'leftId': self.items[0]['id'], 'rightId': self.items[0]['id']})
        self.assertEqual(result.status_code, 200)
        for row in result.json()['rows']:
            self.assertEqual(row['left'], row['right'])
        self.assertIn('比例相近', result.json()['insight'])


if __name__ == '__main__':
    unittest.main()
