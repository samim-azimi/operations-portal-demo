import hashlib,math,re
from app.config import settings
from app.models import KnowledgeBaseArticle

def _embedding(text,dimensions=256):
    vector=[0.0]*dimensions
    for token in re.findall(r"[a-z0-9]+",text.lower()):
        digest=int(hashlib.sha256(token.encode()).hexdigest()[:8],16)
        vector[digest%dimensions]+=1.0
    norm=math.sqrt(sum(x*x for x in vector)) or 1.0
    return [x/norm for x in vector]

def _collection():
    import chromadb
    client=chromadb.PersistentClient(path=settings.chroma_path)
    return client.get_or_create_collection("helpdesk_kb",metadata={"hnsw:space":"cosine"})

def index_article(article):
    try:
        text=f"{article.title} {article.category} {article.problem_description} {article.solution} {' '.join(article.tags or [])}"
        _collection().upsert(ids=[str(article.id)],embeddings=[_embedding(text)],documents=[text],metadatas=[{"title":article.title,"category":article.category}])
    except Exception:
        pass

def search_articles(db,query,limit=3):
    ids=[]
    try:
        result=_collection().query(query_embeddings=[_embedding(query)],n_results=limit)
        ids=[int(x) for x in (result.get("ids") or [[]])[0]]
    except Exception:
        pass
    articles=[]
    if ids:
        found={a.id:a for a in db.query(KnowledgeBaseArticle).filter(KnowledgeBaseArticle.id.in_(ids)).all()}
        articles=[found[x] for x in ids if x in found]
    if not articles:
        words=set(re.findall(r"[a-z0-9]+",query.lower()))
        all_articles=db.query(KnowledgeBaseArticle).all()
        articles=sorted(all_articles,key=lambda a:len(words & set(re.findall(r"[a-z0-9]+",f"{a.title} {a.problem_description} {' '.join(a.tags or [])}".lower()))),reverse=True)[:limit]
    return [{"id":a.id,"title":a.title,"category":a.category,"solution":a.solution} for a in articles]
