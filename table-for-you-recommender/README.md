---
title: Table For You Fase 28
emoji: 🎲
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

# Table For You - API de la fase 28 de Isma

Se utiliza la fórmula **sin cambiar los pesos** (texto/categorías/mecánicas/atributos: 0.55/0.15/0.15/0.15; puntuación final 0.70/0.18/0.12). El TF-IDF original de la fase 7 permanece como referencia.

* Subir el CSV real exportado del Colab a `data/catalog.csv` (no hay ninguno incluido).
* La web consulta Auth, favoritos y valoraciones a Supabase; esta API **no usa claves** ni modifica Supabase.
* En Variables de Hugging Face definir `TFY_ALLOWED_ORIGINS=https://TU-USUARIO.github.io`.
* Probar `GET /health` y `POST /recommend` antes de la exposición.
* La URL del Space es estable, pero su disponibilidad depende del plan y del estado del servidor.

**Ejemplo POST:** `{"seeds":[13],"limit":5,"mode":"hybrid","ratings":{},"preferences":{}}`.

No se ha probado con el catálogo real ni se ha desplegado. Los códigos de estado de la web y el resto de funciones Supabase no dependen del servidor de recomendaciones.

## Verificación local

`python test_local.py` prueba ambos motores con datos sintéticos. Esto no sustituye a la prueba real del Space, la evaluación con valoraciones reales y los 27 casos de uso de Supabase.

## En GitHub Pages

El HTML actual utiliza `config.js` (no `config.json`): actualiza `recommendationApiUrl` con la URL del Space. No hace falta actualizar ninguna función de CRUD/Supabase. El navegador envía `POST /recommend` y el Space devuelve `items`.
