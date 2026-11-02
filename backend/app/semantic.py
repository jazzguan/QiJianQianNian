"""BGE中文向量、SQLite持久化与FAISS余弦检索。"""
import hashlib
import json
import os
import threading
from functools import lru_cache
from pathlib import Path

import numpy as np
from . import storage

MODEL_ID='BAAI/bge-small-zh-v1.5'
MODEL_PATH=Path(os.environ.get('QJQN_EMBEDDING_PATH',str(Path(__file__).resolve().parents[1]/'cache'/'bge-small-zh-v1.5')))
_model_lock=threading.RLock()


@lru_cache(maxsize=1)
def encoder():
    import torch
    from transformers import AutoModel,AutoTokenizer
    if not (MODEL_PATH/'model.safetensors').is_file():
        raise RuntimeError('语义检索权重未安装，请执行 python setup_semantic.py')
    torch.set_num_threads(min(8,os.cpu_count() or 2))
    tokenizer=AutoTokenizer.from_pretrained(str(MODEL_PATH),local_files_only=True)
    model=AutoModel.from_pretrained(str(MODEL_PATH),local_files_only=True,use_safetensors=True).eval()
    return tokenizer,model


def embed(texts,query=False):
    import torch
    with _model_lock:
        tokenizer,model=encoder(); vectors=[]
        for start in range(0,len(texts),8):
            batch=texts[start:start+8]
            if query: batch=['为这个句子生成表示以用于检索相关文章：'+x for x in batch]
            encoded=tokenizer(batch,padding=True,truncation=True,max_length=512,return_tensors='pt')
            with torch.inference_mode():
                values=model(**encoded).last_hidden_state[:,0]
                values=torch.nn.functional.normalize(values,p=2,dim=1)
                vectors.append(values.numpy().astype('float32'))
        return np.vstack(vectors)


def search(query,documents,limit=8):
    import faiss
    if not documents: return []
    storage.initialize()
    with _model_lock,storage.connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS knowledge_vectors(id TEXT PRIMARY KEY,fingerprint TEXT NOT NULL,model TEXT NOT NULL,vector BLOB NOT NULL)')
        cached={r['id']:r for r in db.execute('SELECT * FROM knowledge_vectors WHERE model=?',(MODEL_ID,))}
        missing=[]; fingerprints={}
        for doc in documents:
            fingerprint=hashlib.sha256(doc['text'].encode()).hexdigest();fingerprints[doc['id']]=fingerprint
            if doc['id'] not in cached or cached[doc['id']]['fingerprint']!=fingerprint: missing.append(doc)
        if missing:
            vectors=embed([x['text'] for x in missing])
            for doc,vector in zip(missing,vectors):
                db.execute('INSERT OR REPLACE INTO knowledge_vectors VALUES(?,?,?,?)',
                    (doc['id'],fingerprints[doc['id']],MODEL_ID,vector.tobytes()))
                cached[doc['id']]={'vector':vector.tobytes()}
        vectors=np.stack([np.frombuffer(cached[x['id']]['vector'],dtype='float32') for x in documents])
        index=faiss.IndexFlatIP(vectors.shape[1]);index.add(vectors)
        values,positions=index.search(embed([query],query=True),min(limit,len(documents)))
        return [(float(score),documents[int(i)]) for score,i in zip(values[0],positions[0]) if i>=0]


def status():
    return {'model':MODEL_ID,'available':(MODEL_PATH/'model.safetensors').is_file(),'store':'SQLite + FAISS IndexFlatIP'}
