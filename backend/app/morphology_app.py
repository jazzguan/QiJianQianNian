"""仅运行形态对比服务，无需TripoSR或云端模型。"""
from fastapi import FastAPI
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .morphology_routes import router

app=FastAPI(title='器见千年 · 形态对比')
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173',
                                              'http://localhost:5175','http://127.0.0.1:5175'],allow_methods=['*'],allow_headers=['*'])
app.include_router(router)
DIST=Path(__file__).resolve().parents[2]/'dist'
if (DIST/'assets').is_dir(): app.mount('/assets',StaticFiles(directory=DIST/'assets'),name='assets')

@app.get('/health')
def health(): return {'ok':True,'module':'morphology'}

@app.get('/')
def root(): return RedirectResponse('/comparison')

@app.get('/comparison')
def comparison_page():
    if not (DIST/'index.html').is_file(): raise HTTPException(404,'请先执行 npm run build')
    return FileResponse(DIST/'index.html')
