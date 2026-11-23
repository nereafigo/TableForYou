"""API mínima para GitHub Pages: misma Fase 28 del Colab de Isma."""
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import engine

CATALOG=Path(os.getenv('TFY_CATALOG_PATH','data/catalog.csv'))
ERROR=None
N=0
@asynccontextmanager
async def lifespan(app):
    global ERROR,N
    try:
        N=engine.cargar_catalogo(CATALOG)
        ERROR=None
        print(f'Table For You: {N} juegos cargados')
    except Exception as exc:
        ERROR=f'{type(exc).__name__}: {exc}'
        print('ERROR:',ERROR)
    yield

app=FastAPI(title='Table For You - Fase 28',lifespan=lifespan)
origins=[x.strip().rstrip('/') for x in os.getenv('TFY_ALLOWED_ORIGINS','').split(',') if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=['GET','POST'],allow_headers=['Content-Type'])
class Input(BaseModel):
    seeds:list[int]=Field(default_factory=list,max_length=50)
    ratings:dict[str,float]=Field(default_factory=dict)
    preferences:dict=Field(default_factory=dict)
    exclude_ids:list[int]=Field(default_factory=list,max_length=500)
    limit:int=Field(10,ge=1,le=20)
    mode:str='hybrid'

@app.get('/health')
def health():return {'ok':ERROR is None and N>0,'model_loaded':ERROR is None and N>0,'catalog_size':N,'model':'Colab Isma Fase 28','error':ERROR}

@app.post('/recommend')
def recommend(data:Input):
    if ERROR is not None or N==0:raise HTTPException(503,ERROR or 'Catálogo no cargado')
    if data.mode not in ('hybrid','personalized','similar','tfidf'):
        raise HTTPException(400,'Modo no válido')
    try:
        items=engine.recomendar(data.seeds,data.ratings,data.preferences,data.limit,data.exclude_ids,baseline=data.mode=='tfidf')
        return {'ok':True,'items':items,'model':'TF-IDF fase 7' if data.mode=='tfidf' else 'Híbrido fase 28'}
    except (ValueError,KeyError,TypeError) as exc:raise HTTPException(400,str(exc))
