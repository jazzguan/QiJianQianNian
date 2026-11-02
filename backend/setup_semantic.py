"""下载本地中文语义模型并构建可持久保存的检索向量。"""
from huggingface_hub import snapshot_download
from app.semantic import MODEL_ID,MODEL_PATH

snapshot_download(MODEL_ID,local_dir=str(MODEL_PATH),allow_patterns=[
    'config.json','tokenizer*','vocab.txt','special_tokens_map.json','model.safetensors'])
from app.knowledge import knowledge_documents
from app.semantic import search
documents=knowledge_documents()
search('瓷器的制作工艺',documents,1)
print(f'已索引 {len(documents)} 条馆藏与工艺资料')
