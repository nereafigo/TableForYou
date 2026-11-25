/* FASE 1: toda la lógica se ejecuta en la aplicación Gradio del Colab. */
'use strict';
(()=>{
 const cfg=window.TFY_CONFIG||{};
 const url=String(cfg.gradioApiUrl||'').trim().replace(/\/+$/,'');
 const status=document.getElementById('connection-state');
 const notice=document.getElementById('notice');
 const frame=document.getElementById('gradio');
 const wrap=document.getElementById('frame-wrap');
 const link=document.getElementById('open-original');
 const valid=/^https:\/\/[a-z0-9-]+\.gradio\.live$/i.test(url);
 if(!valid){
   status.textContent='Falta configurar Gradio';
   notice.hidden=false;
   notice.innerHTML='<strong>Configura el enlace de Colab</strong>Abre <code>docs/config.js</code> y pega el enlace <code>https://…gradio.live</code> que muestra la fase 29. Después publica los cambios en GitHub.';
   return;
 }
 status.textContent='Gradio configurado · comprobando disponibilidad';
 link.href=url;link.hidden=false;
 wrap.hidden=false;
 frame.src=url;
 // Una carga del iframe no prueba que Gradio esté vivo: podría mostrar un error de red.
 frame.addEventListener('load',()=>{status.textContent='Gradio abierto · comprueba el acceso y la sesión';});
 // CORS impide verificar el contenido del iframe; mostramos un aviso sin bloquear el acceso.
 window.setTimeout(()=>{
   if(status.textContent.includes('comprobando')){
     notice.hidden=false;
     notice.innerHTML='<strong>Si la aplicación no aparece:</strong> usa «Abrir Gradio aparte». Comprueba que Colab sigue encendido, que la URL no ha caducado y que publicaste la configuración nueva.';
   }
 },20000);
})();
