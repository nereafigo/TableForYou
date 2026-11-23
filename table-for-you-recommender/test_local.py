"""Prueba sintética de la API, sin Supabase ni claves."""
import tempfile
import pandas as pd
import engine
rows=[]
for i in range(1,15):
    rows.append(dict(id=i,name=f'Juego {i}',description=('Strategy board game' if i%2 else 'Family card game'),
                     boardgamecategory="['Strategy']" if i%2 else "['Family']",boardgamemechanic="['Drafting']",
                     minplayers=2,maxplayers=5,playingtime=50+i,averageweight=2.0,average=7.0,usersrated=100))
with tempfile.TemporaryDirectory() as d:
    p=d+'/catalog.csv'
    pd.DataFrame(rows).to_csv(p,index=False)
    assert engine.cargar_catalogo(p)==14
    h=engine.recomendar([1],limit=5)
    t=engine.recomendar([1],limit=5,baseline=True)
    assert len(h)==len(t)==5
    assert all(x['id']!=1 for x in h+t)
    assert h==engine.recomendar([1],limit=5)
    print('OK: TF-IDF fase 7 e híbrido fase 28 deterministas, sin modificar datos')
