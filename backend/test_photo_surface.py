"""验证真实纹饰投影的左右、上下方向和背面覆盖。"""
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
from pygltflib import GLTF2
from app.photo_surface import photo_surface,profile_mesh,apply_photo_texture,export_photo_model


class PhotoSurfaceTests(unittest.TestCase):
    @staticmethod
    def fixture():
        pixels=np.zeros((240,160,3),dtype=np.uint8)
        mask=np.zeros((240,160),dtype=bool);mask[20:220,40:120]=True
        pixels[20:220,40:80]=[240,20,20]
        pixels[20:220,80:120]=[20,20,240]
        pixels[20:60,40:120]=[20,240,20]
        return Image.fromarray(pixels),mask

    def test_photo_direction_and_mirrored_back(self):
        image,mask=self.fixture()
        profile,atlas,metadata=photo_surface(image,mask,size=257)
        pixels=np.asarray(atlas)
        # u≈.92 是模型正面左侧，u≈.08 是正面右侧。
        self.assertGreater(int(pixels[128,235,0]),200)
        self.assertGreater(int(pixels[128,20,2]),200)
        self.assertGreater(int(pixels[10,0,1]),200)
        np.testing.assert_allclose(pixels[128,20].astype(float),pixels[128,108],atol=10)
        np.testing.assert_allclose(pixels[128,236].astype(float),pixels[128,148],atol=10)
        np.testing.assert_allclose(pixels[128,0].astype(float),pixels[128,128],atol=10)
        self.assertAlmostEqual(profile[0][1],0)
        self.assertAlmostEqual(profile[-1][1],30)
        self.assertEqual(metadata['coverage'],'symmetric-full')
        self.assertGreaterEqual(metadata['version'],2)

    def test_mesh_uv_matches_vessel_coordinates(self):
        image,mask=self.fixture();profile,atlas,_=photo_surface(image,mask,size=128)
        mesh=apply_photo_texture(profile_mesh(profile,32),atlas)
        uv=mesh.visual.uv
        front=(mesh.vertices[:,2]>4)&(abs(mesh.vertices[:,0])<.01)
        self.assertTrue(front.any())
        self.assertTrue(np.all((uv[front,0]<.01)|(uv[front,0]>.99)))
        self.assertTrue(np.allclose(uv[:,1],mesh.vertices[:,1]/30))
        self.assertTrue(np.isfinite(uv).all())

    def test_glb_contains_texture_and_unlit_material(self):
        image,mask=self.fixture();profile,atlas,_=photo_surface(image,mask,size=128)
        mesh=apply_photo_texture(profile_mesh(profile,32),atlas)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'photo.glb';export_photo_model(mesh,path)
            gltf=GLTF2().load_binary(str(path))
            self.assertEqual(len(gltf.images),1)
            self.assertIn('KHR_materials_unlit',gltf.extensionsUsed)
            self.assertEqual(gltf.materials[0].pbrMetallicRoughness.baseColorFactor,[1,1,1,1])
            self.assertIsNotNone(gltf.materials[0].pbrMetallicRoughness.baseColorTexture)
            primitive=gltf.meshes[0].primitives[0]
            self.assertIsNotNone(primitive.attributes.TEXCOORD_0)
            self.assertIsNone(primitive.attributes.COLOR_0)

if __name__=='__main__':unittest.main()
