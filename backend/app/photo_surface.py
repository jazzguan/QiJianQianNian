"""照片前景轮廓与前后镜像纹饰投影，保持照片颜色和上下方向。"""
import io
import threading
import time
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image
from scipy.ndimage import binary_closing, binary_fill_holes, label, map_coordinates

from . import config

_session = None
_session_lock = threading.Lock()
PHOTO_SURFACE_VERSION = 3


def segment_photo(image):
    global _session
    from rembg import new_session, remove
    with _session_lock:
        if _session is None: _session = new_session('u2netp')
    alpha = np.asarray(remove(image, session=_session))[:, :, 3]
    mask = binary_fill_holes(binary_closing(alpha > 180, iterations=2))
    regions, count = label(mask)
    if not count: raise ValueError('照片未提取到器物前景')
    sizes = np.bincount(regions.ravel()); sizes[0] = 0
    return regions == np.argmax(sizes)


def photo_surface(image, mask=None, size=1536):
    """纹理u=0/1对应正面中心，v=1对应器口；背面关于z=0平面镜像。"""
    image = image.convert('RGB')
    image.thumbnail((1024,1536))
    mask = segment_photo(image) if mask is None else np.asarray(mask,dtype=bool)
    if mask.shape != (image.height,image.width): raise ValueError('前景与照片尺寸不一致')
    ys, _ = np.where(mask)
    if not len(ys): raise ValueError('照片没有前景')
    top,bottom = int(ys.min()),int(ys.max())
    height = bottom-top
    if height<20: raise ValueError('照片轮廓高度不足')
    rows=np.arange(top,bottom+1)
    left=np.zeros(len(rows));right=np.zeros(len(rows));valid=[]
    for i,row in enumerate(rows):
        indices=np.flatnonzero(mask[row])
        if len(indices):left[i],right[i]=indices[0],indices[-1];valid.append(i)
    left=np.interp(np.arange(len(rows)),valid,left[valid])
    right=np.interp(np.arange(len(rows)),valid,right[valid])
    widths=right-left+1
    profile=[]
    for row in np.linspace(bottom,top,128):
        index=row-top
        lo,hi=max(0,int(index)-2),min(len(rows),int(index)+3)
        profile.append([round(float(np.median(widths[lo:hi])/2*30/height),4),round(float((bottom-row)*30/height),4)])
    sample_y=np.linspace(top,bottom,size)
    l=np.interp(sample_y,rows,left)[:,None]
    r=np.interp(sample_y,rows,right)[:,None]
    angle=np.linspace(0,2*np.pi,size,endpoint=True)[None,:]
    sample_x=(l+r)/2+(r-l)/2*np.sin(angle)
    sample_rows=np.broadcast_to(sample_y[:,None],sample_x.shape)
    pixels=np.asarray(image,dtype=np.float32)
    sampled=np.stack([map_coordinates(pixels[:,:,c],[sample_rows,sample_x],order=1,mode='nearest') for c in range(3)],axis=-1)
    # sin(theta)=sin(pi-theta)：前后同一x位置取相同照片颜色，侧面连续衔接。
    atlas_image=Image.fromarray(np.round(sampled).astype(np.uint8))
    # JPEG 带有格式信息，glTF 导出将其嵌入为压缩纹理。
    buffer=io.BytesIO();atlas_image.save(buffer,format='JPEG',quality=94,subsampling=0)
    atlas_image=Image.open(io.BytesIO(buffer.getvalue()))
    return profile,atlas_image,{'version':PHOTO_SURFACE_VERSION,'coverage':'symmetric-full','method':'正面照片纹饰投影与背面镜像','sourceBounds':[int(left.min()),top,int(right.max()),bottom]}


def profile_mesh(profile,segments=128):
    points=np.asarray(profile,dtype=float)
    theta=np.linspace(0,2*np.pi,segments+1)
    radius=points[:,0,None];height=points[:,1,None]
    vertices=np.stack([radius*np.sin(theta),np.broadcast_to(height,(len(points),segments+1)),radius*np.cos(theta)],axis=-1).reshape(-1,3)
    indices=np.arange(len(points)*(segments+1)).reshape(len(points),segments+1)
    a,b,c,d=indices[:-1,:-1],indices[:-1,1:],indices[1:,1:],indices[1:,:-1]
    faces=np.concatenate([np.stack([a,b,c],axis=-1).reshape(-1,3),np.stack([a,c,d],axis=-1).reshape(-1,3)])
    return trimesh.Trimesh(vertices=vertices,faces=faces,process=False)


def apply_photo_texture(mesh,atlas):
    mesh=mesh.copy()
    vertices=np.asarray(mesh.vertices)
    lo,hi=mesh.bounds[:,1]
    u=np.mod(np.arctan2(vertices[:,0],vertices[:,2])/(2*np.pi),1)
    v=(vertices[:,1]-lo)/(hi-lo)
    uv=np.column_stack([u,v])
    faces=mesh.faces.copy()
    face_u=u[faces]
    seams=np.flatnonzero(np.ptp(face_u,axis=1)>.5)
    duplicate={};extra_vertices=[];extra_uv=[]
    for face_id in seams:
        for corner,vertex_id in enumerate(faces[face_id]):
            if u[vertex_id]>=.5:continue
            if vertex_id not in duplicate:
                duplicate[vertex_id]=len(vertices)+len(extra_vertices)
                extra_vertices.append(vertices[vertex_id]);extra_uv.append(uv[vertex_id]+[1,0])
            faces[face_id,corner]=duplicate[vertex_id]
    if extra_vertices:
        vertices=np.vstack([vertices,extra_vertices]);uv=np.vstack([uv,extra_uv])
    material=trimesh.visual.material.PBRMaterial(name='Visible photograph',baseColorTexture=atlas,
        baseColorFactor=[1.,1.,1.,1.],metallicFactor=0.,roughnessFactor=.9,doubleSided=True)
    textured=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    textured.visual=trimesh.visual.texture.TextureVisuals(uv=uv,material=material)
    return textured


def export_photo_model(mesh,path):
    from pygltflib import GLTF2
    path=Path(path)
    temporary=path.with_name(f'.{path.stem}.building.glb')
    try:
        mesh.export(str(temporary))
        gltf=GLTF2().load_binary(str(temporary))
        for material in gltf.materials:
            material.extensions={**(material.extensions or {}),'KHR_materials_unlit':{}}
        gltf.extensionsUsed=list(dict.fromkeys([*(gltf.extensionsUsed or []),'KHR_materials_unlit']))
        gltf.save_binary(str(temporary))
        for retry in range(5):
            try:
                temporary.replace(path)
                break
            except OSError:
                if retry==4:raise
                time.sleep(.2)
    finally:
        if temporary.exists():temporary.unlink()


def collection_surface(artifact,media):
    image_path=Path(media)/f'{artifact["id"]}.jpg'
    profile,atlas,projection=photo_surface(Image.open(image_path))
    atlas.save(Path(media)/f'{artifact["id"]}.texture.jpg',quality=94,subsampling=0)
    mesh=apply_photo_texture(profile_mesh(profile),atlas)
    export_photo_model(mesh,Path(media)/f'{artifact["id"]}.glb')
    from .morphology import measure_profile
    return {**artifact,'shape':profile,'params':measure_profile(profile),
        'modelUrl':f'/media/{artifact["id"]}.glb?v=photo-{PHOTO_SURFACE_VERSION}',
        'textureProjection':projection,'modelMethod':'馆藏照片轮廓建模 + 前后镜像纹饰'}
