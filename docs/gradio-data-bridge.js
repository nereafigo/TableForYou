/* Table For You — Puente Gradio (fase 1). No cambia la presentación del HTML.
 * Todas las consultas PostgREST/RPC atraviesan Gradio. Auth usa Supabase Auth
 * para persistir/refrescar el JWT; el servidor nunca usa service_role.
 */
'use strict';
let _tfyBridgeClient=null, _tfyBridgeUrl='';
async function tfyBridgeRequest(op){
  const url=String(window.TFY_CONFIG?.gradioApiUrl||'').trim().replace(/\/$/,'');
  if(!/^https:\/\/[a-z0-9.-]+\.gradio\.live$/i.test(url))throw Error('Configura una URL vigente https://xxxx.gradio.live en docs/config.js');
  if(!_tfyBridgeClient || _tfyBridgeUrl!==url){
    const {Client}=await import('https://cdn.jsdelivr.net/npm/@gradio/client@2.5.1/dist/index.min.js');
    _tfyBridgeClient=await Client.connect(url);_tfyBridgeUrl=url;
  }
  // getSession es local y no envía credenciales al puente salvo JWT vigente.
  const {data:{session}}=await window.tfyAuthClient.auth.getSession();
  const call={...op,token:session?.access_token||''};
  const response=await _tfyBridgeClient.predict('/tfy_web_query',{request_json:JSON.stringify(call)});
  let payload=response?.data?.[0];
  if(typeof payload==='string') {try{payload=JSON.parse(payload)}catch(_){}}
  if(!payload || typeof payload!=='object')throw Error('Respuesta inesperada de la API Gradio');
  if(!payload.ok)throw Error(payload.error||'Error de comunicación con Gradio');
  return payload;
}
class TFYQuery{
  constructor(table){this.q={op:'select',table,filters:[],orders:[]}}
  select(columns='*',options={}){this.q.columns=columns;this.q.count=options?.count;return this}
  insert(values){this.q.op='insert';this.q.values=values;return this}
  update(values){this.q.op='update';this.q.values=values;return this}
  upsert(values,opts={}){this.q.op='upsert';this.q.values=values;this.q.onConflict=opts.onConflict;return this}
  delete(){this.q.op='delete';return this}
  eq(column,value){return this._filter(column,'eq',value)}
  lt(column,value){return this._filter(column,'lt',value)}
  lte(column,value){return this._filter(column,'lte',value)}
  gt(column,value){return this._filter(column,'gt',value)}
  gte(column,value){return this._filter(column,'gte',value)}
  ilike(column,value){return this._filter(column,'ilike',value)}
  like(column,value){return this._filter(column,'like',value)}
  is(column,value){return this._filter(column,'is',value)}
  in(column,value){return this._filter(column,'in',value)}
  contains(column,value){return this._filter(column,'cs',value)}
  _filter(column,op,value){this.q.filters.push({column,op,value});return this}
  or(expr){this.q.or=expr;return this}
  order(column,options={}){this.q.orders.push({column,ascending:options.ascending!==false});return this}
  range(start,end){this.q.start=start;this.q.end=end;return this}
  limit(n){this.q.limit=n;return this}
  single(){this.q.single=true;return this}
  maybeSingle(){this.q.maybeSingle=true;return this}
  async _execute(){try{let r=await tfyBridgeRequest(this.q);return {data:r.data,count:r.count,error:null}}catch(e){return {data:null,count:null,error:{message:e?.message||String(e)}}}}
  then(resolve,reject){return this._execute().then(resolve,reject)}
}
function tfyEnableGradioBackend(supabaseClient){
  window.tfyAuthClient=supabaseClient;
  // Mantener Auth sin cambios para refrescar la sesión y usar RLS.
  supabaseClient.from=table=>new TFYQuery(table);
  supabaseClient.rpc=async (name,values={})=>{
    try{const r=await tfyBridgeRequest({op:'rpc',name,values});return {data:r.data,error:null}}
    catch(e){return {data:null,error:{message:e?.message||String(e)}}}
  };
  return supabaseClient;
}
