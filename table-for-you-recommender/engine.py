"""Motor Table For You: funciones Fase 28.1 de Isma, sin algoritmos extra."""
from __future__ import annotations
import numpy as np
import pandas as pd
import ast, re, math
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics.pairwise import cosine_similarity

_catalogo_modelo=None
_modelo=None
_vectorizador=None
_matriz=None
_ids_modelo=None
_POS_IDS=set()

PESO_TEXTO_TFY = 0.55

PESO_CATEGORIAS_TFY = 0.15

PESO_MECANICAS_TFY = 0.15

PESO_ATRIBUTOS_TFY = 0.15

PESO_CONTENIDO_TFY = 0.70

PESO_PREFERENCIAS_TFY = 0.18

PESO_POPULARIDAD_TFY = 0.12

_TFY_CATS = None

_TFY_MECHS = None

_TFY_NUMERIC = None

_TFY_CATALOG_SIGNATURE = None

def _tfy_lista_atributo(valor):
    """Convierte listas del CSV (incluidas cadenas tipo "['X', 'Y']") en conjuntos normalizados."""
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return set()
    if isinstance(valor, (list, tuple, set)):
        valores = list(valor)
    else:
        texto = str(valor).strip()
        if not texto:
            return set()
        try:
            parseado = ast.literal_eval(texto)
            valores = parseado if isinstance(parseado, (list, tuple, set)) else [parseado]
        except (ValueError, SyntaxError):
            valores = re.split(r'[,;|]', texto)
    return {str(x).strip().lower() for x in valores if str(x).strip() and str(x).strip().lower() not in {'nan', 'none'}}

def _tfy_jaccard(a, b):
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0

def _tfy_num(valor):
    try:
        x = float(valor)
        return x if np.isfinite(x) else np.nan
    except (TypeError, ValueError):
        return np.nan

def preparar_caracteristicas_hibridas(catalogo):
    """Prepara características alineadas con el orden del índice TF-IDF original."""
    global _TFY_CATS, _TFY_MECHS, _TFY_NUMERIC, _TFY_CATALOG_SIGNATURE
    if _matriz is None or _catalogo_modelo is None:
        raise RuntimeError('Ejecuta primero la fase 7.2 para construir el índice TF-IDF.')
    if len(catalogo) != len(_catalogo_modelo) or not np.array_equal(
        pd.to_numeric(catalogo['id']).to_numpy(), _ids_modelo
    ):
        raise ValueError('El catálogo cambió de orden o contenido. Reconstruye el índice de la fase 7.2.')
    _TFY_CATS = [_tfy_lista_atributo(v) for v in _catalogo_modelo.get('boardgamecategory', pd.Series(['']*len(_catalogo_modelo)))]
    _TFY_MECHS = [_tfy_lista_atributo(v) for v in _catalogo_modelo.get('boardgamemechanic', pd.Series(['']*len(_catalogo_modelo)))]
    columnas = ['minplayers','maxplayers','playingtime','averageweight']
    _TFY_NUMERIC = {}
    for col in columnas:
        serie = pd.to_numeric(_catalogo_modelo[col], errors='coerce') if col in _catalogo_modelo else pd.Series(np.nan, index=_catalogo_modelo.index)
        mediana = float(serie.median()) if serie.notna().any() else 0.0
        minimo = float(serie.min()) if serie.notna().any() else 0.0
        maximo = float(serie.max()) if serie.notna().any() else 1.0
        rango = max(maximo - minimo, 1.0)
        _TFY_NUMERIC[col] = {'values': serie.fillna(mediana).to_numpy(dtype=float), 'known': serie.notna().to_numpy(), 'range': rango}
    _TFY_CATALOG_SIGNATURE = tuple(_ids_modelo.tolist())
    return {'juegos': len(_catalogo_modelo), 'categorias_conocidas': sum(bool(x) for x in _TFY_CATS),
            'mecanicas_conocidas': sum(bool(x) for x in _TFY_MECHS)}

def _tfy_similitud_atributos(pos_seed):
    """Devuelve similitud 0..1 entre el juego semilla y todo el catálogo."""
    n = len(_catalogo_modelo)
    texto = cosine_similarity(_matriz, _matriz[int(pos_seed)]).ravel()
    cat = np.array([_tfy_jaccard(x, _TFY_CATS[int(pos_seed)]) for x in _TFY_CATS], dtype=float)
    mech = np.array([_tfy_jaccard(x, _TFY_MECHS[int(pos_seed)]) for x in _TFY_MECHS], dtype=float)
    sims_num = []
    for col in ['minplayers','maxplayers','playingtime','averageweight']:
        info = _TFY_NUMERIC[col]
        seed_value = info['values'][int(pos_seed)]
        dif = np.abs(info['values'] - seed_value) / info['range']
        sim = np.clip(1.0 - dif, 0.0, 1.0)
        sim[~info['known']] = 0.0
        if not info['known'][int(pos_seed)]:
            sim[:] = 0.0
        sims_num.append(sim)
    numerica = np.mean(np.vstack(sims_num), axis=0)
    return np.clip(PESO_TEXTO_TFY*texto + PESO_CATEGORIAS_TFY*cat +
                   PESO_MECANICAS_TFY*mech + PESO_ATRIBUTOS_TFY*numerica, 0.0, 1.0)

def _tfy_preferencias_usuario(pref):
    pref = pref or {}
    categorias = {str(x).strip().lower() for x in (pref.get('preferred_categories') or []) if str(x).strip()}
    mecanicas = {str(x).strip().lower() for x in (pref.get('preferred_mechanics') or []) if str(x).strip()}
    return categorias, mecanicas

def _tfy_puntuacion_popularidad(catalogo):
    """Popularidad conservadora basada en average y usersrated del catálogo BGG."""
    votos = pd.to_numeric(catalogo.get('usersrated', 0), errors='coerce').fillna(0).clip(lower=0)
    media = pd.to_numeric(catalogo.get('average', 0), errors='coerce').fillna(0).clip(0,10)
    votos_log = np.log1p(votos.to_numpy(dtype=float))
    denom = max(float(np.nanmax(votos_log)) if len(votos_log) else 0.0, 1.0)
    popularidad = votos_log / denom
    calidad = media.to_numpy(dtype=float) / 10.0
    # Una media alta con muy pocos votos no domina la clasificación.
    confianza = votos.to_numpy(dtype=float) / (votos.to_numpy(dtype=float) + 50.0)
    return np.clip(0.65*popularidad + 0.35*calidad*confianza, 0.0, 1.0)

def _tfy_scores_hibridos(seed_weights, pref=None):
    """Puntuación para todos los juegos. seed_weights: {game_id: peso}; negativos penalizan."""
    n = len(_catalogo_modelo)
    pos_ids = {int(g): i for i, g in enumerate(_ids_modelo)}
    pesos_validos = [(pos_ids[int(g)], float(w)) for g,w in seed_weights.items()
                     if int(g) in pos_ids and np.isfinite(float(w)) and abs(float(w)) > 1e-9]
    positivos = [(p,w) for p,w in pesos_validos if w > 0]
    negativos = [(p,abs(w)) for p,w in pesos_validos if w < 0]
    contenido = np.zeros(n, dtype=float)
    if positivos:
        suma = sum(w for _,w in positivos)
        contenido = sum((_tfy_similitud_atributos(p)*w for p,w in positivos), np.zeros(n))/suma
    if negativos:
        suma_neg = sum(w for _,w in negativos)
        penalizacion = sum((_tfy_similitud_atributos(p)*w for p,w in negativos), np.zeros(n))/suma_neg
        contenido = np.clip(contenido - 0.30*penalizacion, 0.0, 1.0)
    cats_pref, mechs_pref = _tfy_preferencias_usuario(pref)
    pref_scores = np.array([
        0.5*_tfy_jaccard(cats_pref, cats) + 0.5*_tfy_jaccard(mechs_pref, mechs)
        if cats_pref or mechs_pref else 0.0
        for cats,mechs in zip(_TFY_CATS,_TFY_MECHS)
    ], dtype=float)
    popularidad = _tfy_puntuacion_popularidad(_catalogo_modelo)
    # Renormalización cuando no hay preferencias configuradas.
    if cats_pref or mechs_pref:
        score = PESO_CONTENIDO_TFY*contenido + PESO_PREFERENCIAS_TFY*pref_scores + PESO_POPULARIDAD_TFY*popularidad
    else:
        score = 0.85*contenido + 0.15*popularidad
    return np.clip(score,0.0,1.0), contenido, pref_scores, popularidad

def _tfy_aplicar_filtros_contexto(datos, disponibilidad=None, jugadores=None, complejidad=None):
    if disponibilidad not in (None,0,''):
        d = tfy_clean_int(disponibilidad,'duración máxima',True,1)
        datos = datos[pd.to_numeric(datos['playingtime'],errors='coerce').notna() & (pd.to_numeric(datos['playingtime'],errors='coerce') <= d)]
    if jugadores not in (None,0,''):
        j = tfy_clean_int(jugadores,'jugadores',True,1)
        mn = pd.to_numeric(datos['minplayers'],errors='coerce')
        mx = pd.to_numeric(datos['maxplayers'],errors='coerce')
        datos = datos[mn.notna() & mx.notna() & (mn <= j) & (mx >= j)]
    if complejidad not in (None,0,''):
        c = tfy_clean_float(complejidad,'complejidad máxima',0,5)
        peso = pd.to_numeric(datos['averageweight'],errors='coerce')
        datos = datos[peso.notna() & (peso <= c)]
    return datos

def _tfy_diversificar_resultados(indices, scores, limite):
    """Selección MMR ligera: conserva relevancia y reduce repetición de categorías/mecánicas."""
    restantes = [int(i) for i in indices]
    elegidos = []
    while restantes and len(elegidos) < limite:
        mejor = None; mejor_score = -1e9
        for i in restantes:
            redundancia = 0.0
            if elegidos:
                redundancia = max(
                    0.5*_tfy_jaccard(_TFY_CATS[i],_TFY_CATS[j]) + 0.5*_tfy_jaccard(_TFY_MECHS[i],_TFY_MECHS[j])
                    for j in elegidos
                )
            mmr = 0.85*float(scores[i]) - 0.15*redundancia
            if mmr > mejor_score or (mmr == mejor_score and (mejor is None or int(_ids_modelo[i]) < int(_ids_modelo[mejor]))):
                mejor,mejor_score=i,mmr
        elegidos.append(mejor); restantes.remove(mejor)
    return elegidos


# Funciones mínimas que en Colab ya se definían en las fases anteriores.
def tfy_clean_int(x, name, required=True, min_value=1):
    if x in (None, '', 0) and not required:
        return None
    v=int(x)
    if v<min_value:raise ValueError(f'{name}: valor inválido')
    return v

def tfy_clean_float(x, name, min_value=0, max_value=5):
    v=float(x)
    if not min_value<=v<=max_value:raise ValueError(f'{name}: valor inválido')
    return v

# Fase 7.2: se conserva el vectorizador y vecinos del notebook.
def reconstruir_indice(catalogo):
    global _catalogo_modelo, _modelo, _vectorizador, _matriz, _ids_modelo
    if catalogo.empty:raise ValueError('Catálogo vacío')
    textos=catalogo['description'].fillna('').astype(str)
    textos=textos.where(textos.str.strip().ne(''),catalogo['name'].fillna('').astype(str))
    _vectorizador=TfidfVectorizer(stop_words='english',max_features=20000,ngram_range=(1,2),min_df=1)
    _matriz=_vectorizador.fit_transform(textos)
    _modelo=NearestNeighbors(metric='cosine',algorithm='brute').fit(_matriz)
    _ids_modelo=catalogo['id'].astype('int64').to_numpy()
    _catalogo_modelo=catalogo.copy().reset_index(drop=True)
    return len(_catalogo_modelo)


def cargar_catalogo(ruta):
    df=pd.read_csv(ruta)
    for col in ('id','name','description'):
        if col not in df:raise ValueError('Falta columna '+col)
    df['id']=pd.to_numeric(df['id'],errors='coerce')
    df=df.dropna(subset=['id','name']).drop_duplicates('id').reset_index(drop=True)
    df['id']=df['id'].astype('int64')
    # Valores por defecto solo para que el CSV exportado sea compatible.
    for col in ('usersrated','average','minplayers','maxplayers','playingtime','averageweight','boardgamecategory','boardgamemechanic'):
        if col not in df:df[col]=0 if col in ('usersrated','average') else ''
    reconstruir_indice(df)
    global _POS_IDS
    _POS_IDS=set(int(x) for x in _ids_modelo)
    preparar_caracteristicas_hibridas(df)
    return len(df)


def _filtrar_candidatos(df, prefs, exclude_ids):
    prefs=prefs or {}
    # Equivalencia de nombres del frontend con filtros Colab.
    minutos=prefs.get('minutes',prefs.get('preferred_max_duration'))
    jugadores=prefs.get('players')
    complejidad=prefs.get('max_complexity',prefs.get('preferred_max_complexity'))
    data=_tfy_aplicar_filtros_contexto(df,minutos,jugadores,complejidad)
    min_players=prefs.get('min_players')
    max_players=prefs.get('max_players')
    if min_players not in (None,'',0):
        data=data[pd.to_numeric(data['maxplayers'],errors='coerce')>=int(min_players)]
    if max_players not in (None,'',0):
        data=data[pd.to_numeric(data['minplayers'],errors='coerce')<=int(max_players)]
    if 'is_active' in data.columns:
        active=data['is_active'].astype(str).str.lower().isin(('true','1','t','yes'))
        data=data[active]
    return data[~data['id'].isin(set(exclude_ids))]


def recomendar(seeds, ratings=None, preferences=None, limit=10, exclude_ids=None, baseline=False):
    """Misma fórmula y diversificación fase 28; las señales las envía la web.
    No conecta a Supabase: la web consulta allí favoritos, ratings, actividad.
    """
    if _catalogo_modelo is None:raise RuntimeError('Falta cargar el catálogo')
    ratings=ratings or {};prefs=preferences or {}
    seed_weights={}
    for g in seeds or []:
        gid=int(g)
        if gid in _POS_IDS:seed_weights[gid]=1.0
    for g,s in ratings.items():
        gid=int(g);val=float(s)
        if gid not in _POS_IDS:continue
        peso=(val-6.0)/4.0
        if peso>0:seed_weights[gid]=max(seed_weights.get(gid,0.0),peso)
        elif peso<0 and gid not in seed_weights:seed_weights[gid]=max(-0.75,peso)
    # La fase 28 utiliza los nombres de campos de Supabase.
    pref={'preferred_categories':prefs.get('preferred_categories',prefs.get('categories',[])),
          'preferred_mechanics':prefs.get('preferred_mechanics',prefs.get('mechanics',[]))}
    cats,mechs=_tfy_preferencias_usuario(pref)
    if not baseline and not seed_weights and not cats and not mechs:
        return []
    excluidos=set(int(x) for x in (exclude_ids or []))|set(seed_weights)
    datos=_filtrar_candidatos(_catalogo_modelo,prefs,excluidos)
    posiciones={int(g):i for i,g in enumerate(_ids_modelo)}
    candidatos=[posiciones[int(g)] for g in datos['id'] if int(g) in posiciones]
    if not candidatos:return []
    if baseline:
        positivos=[(posiciones[g],w) for g,w in seed_weights.items() if w>0]
        if not positivos:return []
        suma=sum(w for _,w in positivos)
        scores=sum((cosine_similarity(_matriz,_matriz[p]).ravel()*w for p,w in positivos),np.zeros(len(_ids_modelo)))/suma
    else:
        scores,_,_,_=_tfy_scores_hibridos(seed_weights,pref)
    orden=sorted(candidatos,key=lambda i:(-float(scores[i]),int(_ids_modelo[i])))
    if not baseline:
        orden=_tfy_diversificar_resultados(orden[:min(250,len(orden))],scores,int(limit))
    else:orden=orden[:int(limit)]
    return [{'id':int(_ids_modelo[i]),'name':str(_catalogo_modelo.iloc[i]['name']),
             'score':round(float(scores[i]),6)} for i in orden]
