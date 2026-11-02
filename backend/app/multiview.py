"""四方向正交轮廓的体素交集与逐面照片投影。"""
import io
import math
import numpy as np
import trimesh
from PIL import Image
from scipy.ndimage import binary_closing,label
from skimage.measure import marching_cubes
from .morphology import normalize_mesh


def prepare_view(data,angle,session=None):
    image=Image.open(io.BytesIO(data));image.thumbnail((1200,1600))
    if image.mode=='RGBA' and np.asarray(image.getchannel('A')).min()<128:
        foreground=image
    else:
        from rembg import remove
        foreground=remove(image.convert('RGB'),session=session)
    mask=binary_closing(np.asarray(foreground.getchannel('A'))>128,iterations=1)
    regions,count=label(mask)
    if not count: raise ValueError('有照片未识别到器物前景')
    sizes=np.bincount(regions.ravel());sizes[0]=0;mask=regions==sizes.argmax()
    ys,xs=np.where(mask);top,bottom=int(ys.min()),int(ys.max());left,right=int(xs.min()),int(xs.max())
    if bottom-top<20: raise ValueError('器物在照片中过小')
    rgb=Image.new('RGB',foreground.size,'white');rgb.paste(foreground,mask=foreground.getchannel('A'))
    crop=rgb.crop((left,top,right+1,bottom+1))
    return dict(image=crop,mask=mask[top:bottom+1,left:right+1],angle=math.radians(angle),
        width=right-left+1,height=bottom-top+1)


def reconstruct_views(images,progress=None,resolution=112):
    if len(images)!=4: raise ValueError('请依次提供正面、右侧、背面、左侧四张照片')
    if not 32<=resolution<=192: raise ValueError('重建分辨率需为32至192')
    needs_removal=any(Image.open(io.BytesIO(data)).mode!='RGBA' or np.asarray(Image.open(io.BytesIO(data)).getchannel('A')).min()>=128 for data in images)
    session=None
    if needs_removal:
        from rembg import new_session
        session=new_session('u2netp')
    views=[]
    for index,data in enumerate(images):
        if progress: progress(f'分割第{index+1}个视角',25+index*8)
        views.append(prepare_view(data,index*90,session))
    radius=max(v['width']/v['height']*15 for v in views)*1.05
    grid=np.indices((resolution,resolution,resolution),dtype='float32')
    spacing=np.array([2*radius/(resolution-1),30/(resolution-1),2*radius/(resolution-1)])
    grid[0]=grid[0]*spacing[0]-radius;grid[1]*=spacing[1];grid[2]=grid[2]*spacing[2]-radius
    volume=np.ones(grid.shape[1:],dtype=bool)
    for view in views:
        horizontal=grid[0]*math.cos(view['angle'])-grid[2]*math.sin(view['angle'])
        px=np.rint(horizontal/30*(view['height']-1)+(view['width']-1)/2).astype('int32')
        py=np.rint((1-grid[1]/30)*(view['height']-1)).astype('int32')
        valid=(px>=0)&(px<view['width'])&(py>=0)&(py<view['height'])
        volume &= valid & view['mask'][np.clip(py,0,view['height']-1),np.clip(px,0,view['width']-1)]
    if volume.sum()<100: raise ValueError('四个视角轮廓无法对齐，请使用同一器物的水平四方向照片')
    if progress: progress('提取多视角表面',65)
    vertices,faces,_,_=marching_cubes(np.pad(volume,1).astype('float32'),.5,spacing=spacing)
    vertices+=np.array([-radius-spacing[0],-spacing[1],-radius-spacing[2]])
    mesh=normalize_mesh(trimesh.Trimesh(vertices,faces,process=True))
    return mesh,views


def apply_view_texture(mesh,views):
    tile=768;atlas=Image.new('RGB',(tile*2,tile*2),'white')
    frames=[]
    for index,view in enumerate(views):
        picture=view['image'].copy();picture.thumbnail((tile-4,tile-4))
        x=(index%2)*tile+(tile-picture.width)//2;y=(index//2)*tile+(tile-picture.height)//2
        atlas.paste(picture,(x,y));frames.append((x,y,picture.width,picture.height))
    directions=np.array([[math.sin(v['angle']),0,math.cos(v['angle'])] for v in views])
    chosen=np.argmax(mesh.face_normals@directions.T,axis=1)
    vertices=mesh.vertices[mesh.faces].reshape(-1,3);uv=np.empty((len(vertices),2))
    for index,view in enumerate(views):
        selected=np.repeat(chosen==index,3);points=vertices[selected]
        horizontal=points[:,0]*math.cos(view['angle'])-points[:,2]*math.sin(view['angle'])
        local_u=np.clip(horizontal/30*(view['height']-1)/(view['width']-1)+.5,0,1)
        local_v=np.clip(1-points[:,1]/30,0,1)
        x,y,w,h=frames[index]
        uv[selected,0]=(x+local_u*(w-1))/(tile*2)
        uv[selected,1]=1-(y+local_v*(h-1))/(tile*2)
    result=trimesh.Trimesh(vertices, np.arange(len(vertices)).reshape(-1,3),process=False)
    material=trimesh.visual.material.PBRMaterial(baseColorTexture=atlas,baseColorFactor=[1.,1.,1.,1.],metallicFactor=0,roughnessFactor=1,doubleSided=True)
    result.visual=trimesh.visual.texture.TextureVisuals(uv=uv,material=material)
    return result
