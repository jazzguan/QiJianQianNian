"""补充唐宋元明清的碗、盘、杯、罐；只导入馆方CC0记录和图片。"""
import io
import json
from pathlib import Path
from PIL import Image
from import_collection import DYNASTIES,parts,fetch
from app.providers import text_completion,parse_object
from app.photo_surface import collection_surface

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; MEDIA=DATA/'images'; CACHE=ROOT/'cache'/'cleveland-catalog.json'


def run():
    if not CACHE.is_file():
        with fetch('https://openaccess-api.clevelandart.org/api/artworks/?department=Chinese%20Art&type=Ceramic&cc0&has_image=1&limit=1000') as response:
            CACHE.write_text(json.dumps(json.load(response),ensure_ascii=False),encoding='utf-8')
    records=json.loads(CACHE.read_text(encoding='utf-8'))['data']
    translations=DATA/'translations.json'
    cache=json.loads(translations.read_text(encoding='utf-8')) if translations.is_file() else {}
    for dynasty,dynasty_name,needle in DYNASTIES:
        for token,category in [('bowl','碗'),('dish','盘'),('cup','杯'),('jar','罐')]:
            seed=DATA/'artifacts.json'; existing=json.loads(seed.read_text(encoding='utf-8'))
            if any(x['dynasty']==dynasty and x.get('category')==category for x in existing): continue
            candidates=[x for x in records if needle in ' '.join(x['culture']) and sum(n in ' '.join(x['culture']) for _,_,n in DYNASTIES)==1
                and token in x['title'].lower() and x.get('share_license_status')=='CC0' and x.get('images',{}).get('web')]
            candidates.sort(key=lambda x:x['id'])
            if not candidates: print(f'资料缺口 {dynasty_name} {category}',flush=True); continue
            item=candidates[0]; key=f'cma-{item["id"]}'
            if any(x['id']==key for x in existing): continue
            print(f'补充 {dynasty_name} {category} {key}',flush=True)
            raw={k:item.get(k) for k in ['title','culture','technique','description','did_you_know','measurements']}
            if key not in cache:
                prompt='忠实翻译馆藏字段成简体中文，不补写未记载的知识。输出JSON：name、technique、description、history（只翻译年代/文化）、formFeatures、decorationFeatures、craftFeatures（后三项为数组）。原资料：'+json.dumps(raw,ensure_ascii=False)
                cache[key]=parse_object(text_completion([{'role':'user','content':prompt}],max_tokens=1200))
                translations.write_text(json.dumps(cache,ensure_ascii=False,indent=2),encoding='utf-8')
            cn=cache[key]; path=MEDIA/(key+'.jpg')
            if not path.is_file():
                with fetch(item['images']['web']['url']) as response: image=Image.open(io.BytesIO(response.read())).convert('RGB')
                image.thumbnail((1280,1600)); image.save(path,quality=88,optimize=True)
            artifact=dict(id=key,name=cn.get('name') or item['title'],originalName=item['title'],dynasty=dynasty,dynastyName=dynasty_name,
                period=item['creation_date'],category=category,summary=cn.get('technique',''),description=cn.get('description',''),history=cn.get('history',''),
                formFeatures=cn.get('formFeatures',[]),decorationFeatures=cn.get('decorationFeatures',[]),craftFeatures=cn.get('craftFeatures',[]),
                material=cn.get('technique',''),use='',parts=parts(),imageUrl=f'/media/{key}.jpg',measurementsText=item.get('measurements',''),
                institution='克利夫兰艺术博物馆',accessionNumber=item['accession_number'],sourceUrl=item['url'],license='CC0',
                sources=[dict(title=item['title'],institution='克利夫兰艺术博物馆',url=item['url'],license='CC0')],originalMetadata=raw,
                originalImageUrl=item['images']['web']['url'],glaze=dict(color='#ede5d3',roughness=.38,metalness=.05,clearcoat=.5,decoration='plain'))
            artifact=collection_surface(artifact,MEDIA)
            # 每次写入前重读，保留同时导入的其他机构扫描记录。
            existing=json.loads(seed.read_text(encoding='utf-8'))
            seed.write_text(json.dumps([x for x in existing if x['id']!=key]+[artifact],ensure_ascii=False,indent=2),encoding='utf-8')
    print('跨朝代常见器型补充完成',flush=True)


if __name__=='__main__': run()
