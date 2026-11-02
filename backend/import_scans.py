"""导入Smithsonian开放的完整觚式瓶扫描，保留纹理和来源。"""
import io
import json
import re
from pathlib import Path
from urllib.parse import urlencode
from PIL import Image
import trimesh
from import_collection import fetch,parts
from app.providers import parse_object,text_completion
from app.morphology import normalize_mesh,measure_mesh

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data';MEDIA=DATA/'images';CACHE=ROOT/'cache'


def run():
    path=CACHE/'smithsonian-all-catalog.json'
    if path.is_file(): results=json.loads(path.read_text(encoding='utf-8'))
    else:
        with fetch('https://3d-api.si.edu/api/v1.0/content/file/search?'+urlencode({'q':'porcelain','file_type':'glb','rows':100})) as response: results=json.load(response)
    chosen={}
    for row in results['rows']:
        content=row['content']
        if content['quality']=='Low' and 'beaker-shaped vase' in row['title'].lower(): chosen[content['model_url']]=row
    for package,row in chosen.items():
        key='si-'+package.split(':')[1]; seed=DATA/'artifacts.json'
        existing=json.loads(seed.read_text(encoding='utf-8'))
        if any(x['id']==key and x.get('sourceUpAxis')=='z' for x in existing): continue
        print('导入官方扫描 '+row['title'],flush=True)
        metadata_path=CACHE/(key+'.json')
        if metadata_path.is_file(): raw=json.loads(metadata_path.read_text(encoding='utf-8'))
        else:
            with fetch('https://api.si.edu/openaccess/api/v1.0/search?'+urlencode({'api_key':'DEMO_KEY','q':package,'rows':1})) as response:
                raw=json.load(response)['response']['rows'][0]['content']
            metadata_path.write_text(json.dumps(raw,ensure_ascii=False),encoding='utf-8')
        free=raw['freetext']; descriptive=raw['descriptiveNonRepeating']
        dates='；'.join(x['content'] for x in free.get('date',[]))
        if 'Qing' not in dates: raise ValueError('该扫描年代不在当前清代导入范围')
        descriptions=[x['content'] for x in free.get('notes',[]) if x['label']=='Description']
        physical=free.get('physicalDescription',[])
        medium='；'.join(x['content'] for x in physical if x['label']=='Medium')
        dimensions='；'.join(x['content'] for x in physical if x['label']=='Dimensions')
        translated_path=CACHE/(key+'-cn.json')
        if translated_path.is_file(): cn=json.loads(translated_path.read_text(encoding='utf-8'))
        else:
            prompt='忠实翻译下列馆方字段为中文，输出JSON：name,technique,description,history（仅年代/文化）,formFeatures,decorationFeatures,craftFeatures（后三项数组）。不补写资料中没有的用途或知识。'+json.dumps(dict(title=row['title'],date=dates,medium=medium,description=descriptions),ensure_ascii=False)
            cn=parse_object(text_completion([{'role':'user','content':prompt}],max_tokens=1200))
            translated_path.write_text(json.dumps(cn,ensure_ascii=False),encoding='utf-8')
        source_model=CACHE/(key+'-source.glb')
        if not source_model.is_file():
            with fetch(row['content']['uri']) as response: source_model.write_bytes(response.read())
        mesh=normalize_mesh(trimesh.load(source_model,force='scene',process=False).to_geometry(),'z')
        measurement=measure_mesh(mesh)
        mesh.export(str(MEDIA/(key+'.glb')))
        pictures=[x for x in descriptive.get('online_media',{}).get('media',[]) if x.get('type')=='Images' and x.get('usage',{}).get('access')=='CC0']
        if not pictures: raise ValueError('扫描记录缺少CC0配图')
        with fetch(pictures[0]['content']+'&max=1280') as response: picture=Image.open(io.BytesIO(response.read())).convert('RGB')
        picture.thumbnail((1280,1600));picture.save(MEDIA/(key+'.jpg'),quality=88,optimize=True)
        height=re.search(r'\bH\s*(?:x[^:]+)?\s*:\s*([\d.]+)',dimensions)
        artifact=dict(id=key,name=cn['name'],originalName=row['title'],dynasty='qing',dynastyName='清',period=dates,category='瓶',
            summary=cn.get('technique',medium),description=cn.get('description',''),history=cn.get('history',dates),
            shape=measurement['shape'],params=measurement,physicalHeightCm=float(height[1]) if height else None,
            formFeatures=cn.get('formFeatures',[]),decorationFeatures=cn.get('decorationFeatures',[]),craftFeatures=cn.get('craftFeatures',[]),
            material=medium,use='',parts=parts(),imageUrl=f'/media/{key}.jpg',modelUrl=f'/media/{key}.glb',
            measurementsText=dimensions,modelMethod='Smithsonian 官方三维扫描',geometrySource='scan',sourceUpAxis='z',
            institution=descriptive.get('data_source','Smithsonian'),accessionNumber=descriptive['record_ID'],sourceUrl=descriptive['record_link'],license='CC0',
            sources=[dict(title=row['title'],institution=descriptive.get('data_source','Smithsonian'),url=descriptive['record_link'],license='CC0'),
                     dict(title='Smithsonian 3D 扫描',institution='Smithsonian',url='https://3d.si.edu/object/'+package,license='CC0')],
            originalMetadata=raw,originalModelUrl=row['content']['uri'],
            glaze=dict(color='#ede5d3',roughness=.5,metalness=0,clearcoat=0,decoration='bluewhite'))
        existing=json.loads(seed.read_text(encoding='utf-8'))
        seed.write_text(json.dumps([x for x in existing if x['id']!=key]+[artifact],ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'扫描完成 {key}：{len(mesh.faces)}面，内径={measurement.get("innerMouthDiameter")}',flush=True)


if __name__=='__main__': run()
