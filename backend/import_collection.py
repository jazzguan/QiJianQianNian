"""导入 CC0 馆藏数据、图片和照片轮廓：python import_collection.py。"""
import io
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
from PIL import Image
from scipy.ndimage import binary_closing, binary_fill_holes, label

from app.providers import ProviderError, vision_completion
from app import config
from rembg import new_session, remove
from app.photo_surface import collection_surface

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
MEDIA = DATA / 'images'
DYNASTIES = [('tang', '唐', 'Tang dynasty'), ('song', '宋', 'Song dynasty'),
             ('yuan', '元', 'Yuan dynasty'), ('ming', '明', 'Ming dynasty'), ('qing', '清', 'Qing dynasty')]
_segmentation = None


def fetch(url):
    return urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0 QiJianQianNian/1.0'}), timeout=40)


def photo_profile(image):
    global _segmentation
    image = image.convert('RGB')
    image.thumbnail((512, 768))
    if _segmentation is None: _segmentation = new_session('u2netp')
    foreground = remove(image,session=_segmentation)
    mask = np.asarray(foreground)[:,:,3] > 180
    mask = binary_fill_holes(binary_closing(mask, iterations=2))
    regions, count = label(mask)
    if not count:
        raise ValueError('照片未提取到器物轮廓')
    sizes = np.bincount(regions.ravel()); sizes[0] = 0
    mask = regions == np.argmax(sizes)
    ys, xs = np.where(mask)
    top, bottom = int(ys.min()), int(ys.max())
    height = bottom - top
    if height < 20:
        raise ValueError('照片轮廓高度不足')
    profile = []
    for y in np.linspace(bottom, top, 64):
        nearby = mask[max(top, int(y)-2):min(bottom+1, int(y)+3)]
        widths = []
        for row in nearby:
            indices = np.flatnonzero(row)
            if len(indices): widths.append(indices[-1]-indices[0]+1)
        radius = float(np.median(widths) / 2 * 30 / height) if widths else 0
        profile.append([round(radius, 4), round((bottom-y)*30/height, 4)])
    return profile


def parts(height=30):
    return [{'id': key, 'name': name, 'yMin': lo*height, 'yMax': hi*height,
             'formDescription': '', 'history': '', 'knowledge': ''}
            for key, name, lo, hi in [('foot','器足',0,.12),('mouth','器口',.92,1),
                                    ('neck','器颈',.75,.92),('decoration','纹饰区域',.45,.60),('body','器身',.12,.75)]]


def main():
    MEDIA.mkdir(parents=True, exist_ok=True)
    url = 'https://openaccess-api.clevelandart.org/api/artworks/?department=Chinese%20Art&type=Ceramic&cc0&has_image=1&limit=1000'
    with fetch(url) as response:
        source = json.load(response)
    chosen = []
    for dynasty, dynasty_name, needle in DYNASTIES:
        items = [x for x in source['data'] if needle in ' '.join(x['culture'])
                 and sum(n in ' '.join(x['culture']) for _, _, n in DYNASTIES) == 1
                 and any(t in x['title'].lower() for t in ['vase','bottle','jar'])
                 and x['share_license_status'] == 'CC0' and x['images'].get('web')]
        items.sort(key=lambda x: ('meiping' not in x['title'].lower(), 'porcelain' not in x['technique'].lower(), x['id']))
        seen = set()
        for item in items:
            base_id = item['accession_number'].rstrip('ab.')
            if base_id in seen: continue
            seen.add(base_id)
            chosen.append((dynasty, dynasty_name, item))
            if len(seen) == 4: break
        if len(seen) < 4: raise RuntimeError(f'{dynasty_name}代器物不足四件')
    translated = {}
    # 仅翻译馆方给出的字段，不补写历史事实。
    for dynasty, dynasty_name, item in chosen:
        key = f'cma-{item["id"]}'
        image_url = item['images']['web']['url']
        image_path = MEDIA / f'{key}.jpg'
        if not image_path.exists():
            with fetch(image_url) as response:
                image = Image.open(io.BytesIO(response.read())).convert('RGB')
            image.thumbnail((1280, 1600)); image.save(image_path, quality=88, optimize=True)
        profile = photo_profile(Image.open(image_path))
        raw = {k: item.get(k) for k in ['title','title_in_original_language','culture','technique','description','did_you_know','measurements']}
        prompt = ('将以下馆藏字段忠实翻译成简体中文，不补写不存在的信息。返回 JSON 对象：'
                  'name（器物名）,technique（工艺）,description（介绍）,history（仅翻译原文化/年代说明，不扩写）, '
                  'category（按原器型选择梅瓶、长颈瓶、瓶、罐之一）,formFeatures（只按标题描述的形态列数组）, '
                  'decorationFeatures（仅按资料描述的装饰列数组）,craftFeatures（仅按原工艺列数组）。'
                  '原资料缺少的字段用空字符串或空数组。原资料：'+json.dumps(raw, ensure_ascii=False))
        print(f'导入 {key} {item["title"]}', flush=True)
        cache = DATA / 'translations.json'
        if cache.exists() and not translated:
            translated.update(json.loads(cache.read_text(encoding='utf-8')))
        if key not in translated:
            for retry in range(3):
                try:
                    translated[key] = vision_completion(image_path.read_bytes(),'image/jpeg',prompt+'只翻译文字资料，不根据图片补写这些字段。')
                    break
                except ProviderError:
                    if retry == 2: raise
                    print(f'重试 {key}', flush=True)
                    time.sleep(2)
            cache.write_text(json.dumps(translated, ensure_ascii=False, indent=2), encoding='utf-8')
        cn = translated[key]
        artifact = {'id':key,'name':cn.get('name') or item['title'],'originalName':item['title'],
            'dynasty':dynasty,'dynastyName':dynasty_name,'period':item['creation_date'],
            'category':cn.get('category','瓶'),'summary':cn.get('technique',''),
            'description':cn.get('description',''),'history':cn.get('history',''),
            'shape':profile,'params':{'height':30,'maxBellyDiameter':max(r for r,h in profile)*2,
              'mouthDiameter':profile[-1][0]*2,'footDiameter':profile[0][0]*2},
            'glaze':{'color':'#ede5d3','roughness':.38,'metalness':.05,'clearcoat':.5,'decoration':'plain'},
            'formFeatures':cn.get('formFeatures',[]),'decorationFeatures':cn.get('decorationFeatures',[]),
            'craftFeatures':cn.get('craftFeatures',[]),'parts':parts(),
            'imageUrl':f'/media/{key}.jpg','measurementsText':item.get('measurements',''),
            'modelMethod':'馆藏照片轮廓旋转建模','institution':'克利夫兰艺术博物馆',
            'accessionNumber':item['accession_number'],'sourceUrl':item['url'],'license':'CC0',
            'sources':[{'title':item['title'],'institution':'克利夫兰艺术博物馆','url':item['url'],'license':'CC0'}],
            'originalMetadata':raw,'originalImageUrl':image_url,'sketchfabUrl':item.get('sketchfab_url')}
        seed = DATA / 'artifacts.json'
        artifact = collection_surface(artifact,MEDIA)
        existing = json.loads(seed.read_text(encoding='utf-8')) if seed.exists() else []
        existing = [x for x in existing if x['id'] != key] + [artifact]
        seed.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding='utf-8')
    print('20 件馆藏导入完成', flush=True)


if __name__ == '__main__': main()
