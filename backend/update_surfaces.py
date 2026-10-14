"""用已下载照片生成有纹饰的馆藏 GLB；修复现有上传模型的纹理。"""
import argparse
import json
import sqlite3
from pathlib import Path
import trimesh
from PIL import Image
from app import config,storage
from app.photo_surface import PHOTO_SURFACE_VERSION,collection_surface,photo_surface,apply_photo_texture,export_photo_model

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--uploaded-only',action='store_true');args=parser.parse_args()
    seed=storage.DATA_DIR/'artifacts.json';media=storage.DATA_DIR/'images'
    if not args.uploaded_only:
        items=json.loads(seed.read_text(encoding='utf-8'))
        for i,item in enumerate(items):
            items[i]=collection_surface(item,media)
            seed.write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8')
            print('TEXTURED_COLLECTION',item['id'],flush=True)
    processed={}
    for database in [Path(storage.DB_PATH),Path(config.BASE_DIR)/'cache'/'smoke.sqlite3']:
        if not database.exists():continue
        db=sqlite3.connect(database)
        try:
            for task_id,data in db.execute("SELECT id,data FROM reconstructions WHERE json_extract(data,'$.status')='success'").fetchall():
                task=json.loads(data)
                if task.get('textureProjection',{}).get('version')==PHOTO_SURFACE_VERSION:continue
                image_path=Path(config.OUTPUT_DIR,f'{task_id}.jpg');mesh_path=Path(config.OUTPUT_DIR,f'{task_id}.glb')
                if not image_path.is_file() or not mesh_path.is_file():continue
                if task_id not in processed:
                    _,atlas,projection=photo_surface(Image.open(image_path))
                    mesh=trimesh.load(mesh_path,force='mesh',process=False)
                    mesh=apply_photo_texture(mesh,atlas);export_photo_model(mesh,mesh_path)
                    low=mesh.simplify_quadric_decimation(face_count=min(18000,len(mesh.faces)))
                    low=apply_photo_texture(low,atlas)
                    export_photo_model(low,Path(config.OUTPUT_DIR,f'{task_id}.preview.glb'))
                    processed[task_id]=projection
                task['textureProjection']=processed[task_id]
                task['porcelain']['textureProjection']=processed[task_id]
                task['porcelain']['modelMethod']='TripoSR 单图重建 + 前后镜像纹饰'
                task['modelUrl']=f'/files/{task_id}/mesh.glb?v=photo-{PHOTO_SURFACE_VERSION}'
                task['porcelain']['modelUrl']=task['modelUrl']
                task['previewUrl']=f'/files/{task_id}/preview.glb?v=photo-{PHOTO_SURFACE_VERSION}'
                if task.get('report'):
                    task['report']['note']='表面可观测性根据法线朝向估计。正面纹饰来自照片，背面采用正面镜像纹理。'
                db.execute('UPDATE reconstructions SET data=? WHERE id=?',(json.dumps(task,ensure_ascii=False),task_id))
                print('TEXTURED_UPLOAD',task_id,flush=True)
            db.commit()
        finally:db.close()

if __name__=='__main__':main()
