/* ---- helpers svg ---- */
const NS='http://www.w3.org/2000/svg';
let CHN=0;
function svg(w,h){ const s=document.createElementNS(NS,'svg'); s.setAttribute('class','ch');
  s.setAttribute('viewBox',`0 0 ${w} ${h}`); s.setAttribute('preserveAspectRatio','xMidYMid meet'); s.dataset.n=++CHN; return s; }
function el(tag,attrs,parent){ const n=document.createElementNS(NS,tag);
  for(const k in attrs) n.setAttribute(k,attrs[k]); if(parent) parent.appendChild(n); return n; }
function txt(p,x,y,s,cls,anchor){ const t=el('text',{x,y},p); if(cls)t.setAttribute('class',cls);
  if(anchor)t.setAttribute('text-anchor',anchor); t.textContent=s; return t; }
function ticks(max,n){ const raw=max/n; const mag=Math.pow(10,Math.floor(Math.log10(raw)));
  const step=[1,2,2.5,5,10].map(m=>m*mag).find(v=>v>=raw)||mag*10;
  const out=[]; for(let v=0; v<=max*1.0001; v+=step) out.push(Math.round(v*1e6)/1e6);
  if(out[out.length-1]<max) out.push(Math.round((out[out.length-1]+step)*1e6)/1e6); return out; }
function rr(p,x,y,w,h,r,fill,cls){ r=Math.min(r,w/2,h);
  const d=`M${x},${y+h} L${x},${y+r} Q${x},${y} ${x+r},${y} L${x+w-r},${y} Q${x+w},${y} ${x+w},${y+r} L${x+w},${y+h} Z`;
  return el('path',{d,fill,class:cls||'mk'},p); }
function rrh(p,x,y,w,h,r,fill,cls){ r=Math.min(r,h/2,w);
  const d=`M${x},${y} L${x+w-r},${y} Q${x+w},${y} ${x+w},${y+r} L${x+w},${y+h-r} Q${x+w},${y+h} ${x+w-r},${y+h} L${x},${y+h} Z`;
  return el('path',{d,fill,class:cls||'mk'},p); }
/* rejilla y eje comunes */
function rejilla(s,{L,R,W,B,h,max,fmt}){ const tk=ticks(max,4), top=tk[tk.length-1];
  tk.forEach(v=>{ const y=B-(v/top)*h; if(v) el('line',{x1:L,x2:W-R,y1:y,y2:y,class:'gl'},s);
    txt(s,L-8,y+3.5,fmt?fmt(v):nf.format(v),'eje','end'); });
  el('line',{x1:L,x2:W-R,y1:B,y2:B,class:'ax'},s); return top; }
/* hover: un grupo por dato; el resto se atenúa */
function hover(g,s,html){ g.addEventListener('pointerenter',()=>{ s.classList.add('foco'); g.classList.add('on'); });
  g.addEventListener('pointermove',e=>showTip(e,html()));
  g.addEventListener('pointerleave',()=>{ s.classList.remove('foco'); g.classList.remove('on'); hideTip(); }); }
/* aparición al entrar en pantalla */
const VIO=('IntersectionObserver' in window)?new IntersectionObserver(es=>es.forEach(e=>{ if(e.isIntersecting){ e.target.classList.add('vis'); VIO.unobserve(e.target);} }),{rootMargin:'0px 0px -12% 0px'}):null;
function mirar(s){ if(VIO) VIO.observe(s); else s.classList.add('vis'); return s; }

/* ---- tarjetas ---- */
function card(o){
  const d=document.createElement('div'); d.className='card'+(o.wide?' wide':'');
  d.innerHTML=`<h3>${esc(o.t)}</h3><p class="lede">${o.lede}</p><figure></figure>
    <div class="vz-foot"><div class="legend">${o.legend||''}</div>
    <button class="tbtn" type="button">Ver tabla</button></div>
    <div class="tv" hidden></div>${o.note?`<p class="note">${o.note}</p>`:''}`;
  d.querySelector('figure').appendChild(o.chart);
  const tv=d.querySelector('.tv'), bt=d.querySelector('.tbtn');
  bt.addEventListener('click',()=>{ if(tv.hidden){ if(!tv.dataset.on){ tv.innerHTML=table(o.cols,o.rows); tv.dataset.on='1'; }
      tv.hidden=false; bt.textContent='Ocultar tabla'; } else { tv.hidden=true; bt.textContent='Ver tabla'; } });
  return d;
}
function table(cols,rows){
  return '<table><thead><tr>'+cols.map(c=>`<th>${esc(c)}</th>`).join('')+'</tr></thead><tbody>'
    + rows.map(r=>'<tr>'+r.map(c=>`<td>${typeof c==='number'?nf.format(c):esc(c)}</td>`).join('')+'</tr>').join('')
    + '</tbody></table>';
}
function lg(items){ return items.map(([c,l])=>`<span><i style="background:${c}"></i>${esc(l)}</span>`).join(''); }
function lgl(items){ return items.map(([c,l])=>`<span><i class="ln" style="background:${c}"></i>${esc(l)}</span>`).join(''); }

/* ============ formas ============ */
// columnas simples
function cols(data,{h=190,fmt=v=>nf.format(v),lab=d=>d[0],color=SC[0],hl=null,tipfn=null,narrow=false}={}){
  const W=narrow?390:760,H=h+46,L=narrow?34:46,R=8,T=14,B=h+T;
  const s=svg(W,H); const top=rejilla(s,{L,R,W,B,h,max:Math.max(...data.map(d=>d[1]),1)});
  const bw=(W-L-R)/data.length;
  data.forEach((d,i)=>{ const g=el('g',{class:'g'},s); const x=L+i*bw, w=Math.max(2,Math.min(26,bw-3)), cx=x+(bw-w)/2;
    const hh=(d[1]/top)*h, c=hl&&hl(d)?SC[1]:color;
    const m=rr(g,cx,B-hh,w,hh,Math.min(4,w/2),c); m.style.setProperty('--i',i);
    el('rect',{x,y:T,width:bw,height:h,class:'hit'},g);
    hover(g,s,()=>tipfn?tipfn(d):`<b>${fmt(d[1])}</b>${esc(lab(d))}`); });
  const step=Math.ceil(data.length/(narrow?8:16));
  data.forEach((d,i)=>{ if(i%step) return; txt(s,L+i*bw+bw/2,B+16,lab(d),'eje','middle'); });
  return mirar(s);
}
// columnas apiladas
function stack(data,series,{h=200,lab=d=>d[0],colors=SC}={}){
  const W=760,H=h+46,L=50,R=8,T=14,B=h+T;
  const s=svg(W,H);
  const tot=data.map(d=>d.slice(1).reduce((a,b)=>a+b,0));
  const top=rejilla(s,{L,R,W,B,h,max:Math.max(...tot,1)});
  const bw=(W-L-R)/data.length;
  data.forEach((d,i)=>{ const g=el('g',{class:'g'},s); const x=L+i*bw, w=Math.min(32,bw-6), cx=x+(bw-w)/2;
    let acc=0; const vis=series.map((nm,k)=>d[k+1]?k:-1).filter(k=>k>=0), last=vis[vis.length-1];
    series.forEach((nm,k)=>{ const v=d[k+1]; if(!v) return;
      const hh=(v/top)*h, y=B-((acc+v)/top)*h;
      const m=(k===last)?rr(g,cx,y,w,Math.max(hh-2,1),4,colors[k]):el('rect',{x:cx,y:y,width:w,height:Math.max(hh-2,1),fill:colors[k],class:'mk'},g);
      m.style.setProperty('--i',i); acc+=v; });
    if(tot[i]) txt(g,cx+w/2,B-(tot[i]/top)*h-7,nf.format(tot[i]),'tot','middle');
    el('rect',{x,y:T,width:bw,height:h,class:'hit'},g);
    hover(g,s,()=>`<b>${nf.format(tot[i])}</b>${esc(lab(d))}<br>`+
      series.map((nm,k)=>d[k+1]?`<i style="background:${colors[k]}"></i>${esc(nm)} ${nf.format(d[k+1])}`:'').filter(Boolean).join('<br>')); });
  const step=Math.ceil(data.length/14);
  data.forEach((d,i)=>{ if(i%step) return; txt(s,L+i*bw+bw/2,B+16,lab(d),'eje','middle'); });
  return mirar(s);
}
// barras horizontales
function bars(data,{h=null,color=SC[0],fmt=v=>nf.format(v),maxlab=46,narrow=false}={}){
  const rowh=narrow?24:23, W=narrow?390:760, L=narrow?156:270, R=narrow?50:56, T=4;
  if(narrow) maxlab=Math.min(maxlab,26);
  const H=T+data.length*rowh+6;
  const s=svg(W,H); s.classList.add('hz'); const max=Math.max(...data.map(d=>d[1]),1);
  data.forEach((d,i)=>{ const y=T+i*rowh, g=el('g',{class:'g'},s);
    let nm=String(d[0]); const largo=nm.length>maxlab; if(largo) nm=nm.slice(0,maxlab-1)+'…';
    const t=txt(g,L-10,y+rowh/2+4,nm,'lab','end'); if(largo){ const ti=el('title',{},t); ti.textContent=d[0]; }
    const w=Math.max((d[1]/max)*(W-L-R),2);
    const m=rrh(g,L,y+4,w,rowh-8,4,typeof color==='function'?color(d,i):color); m.style.setProperty('--i',i);
    txt(g,L+w+7,y+rowh/2+4,fmt(d[1]),'val');
    el('rect',{x:0,y:y,width:W,height:rowh,class:'hit'},g);
    hover(g,s,()=>`<b>${fmt(d[1])}</b>${esc(d[2]||d[0])}`); });
  return mirar(s);
}
// línea
function line(data,{h=180,lab=d=>d[0],series=['serie'],colors=SC,area=false,mark=null}={}){
  const W=760,H=h+46,R=series.length>1?92:16,L=46,T=14,B=h+T;
  const s=svg(W,H); s.classList.add('ln');
  const ns=series.length;
  const top=rejilla(s,{L,R,W,B,h,max:Math.max(...data.map(d=>Math.max(...d.slice(1))),1)});
  const X=i=>L+(i/(data.length-1))*(W-L-R), Y=v=>B-(v/top)*h;
  const gid='ga'+s.dataset.n;
  for(let k=0;k<ns;k++){
    const pts=data.map((d,i)=>[X(i),Y(d[k+1])]);
    if(area&&ns===1){ const df=el('defs',{},s), lgd=el('linearGradient',{id:gid,x1:0,x2:0,y1:0,y2:1},df);
      el('stop',{offset:0,'stop-color':colors[k],'stop-opacity':.22},lgd); el('stop',{offset:1,'stop-color':colors[k],'stop-opacity':0},lgd);
      el('path',{d:`M${pts[0][0]},${B} `+pts.map(p=>`L${p[0]},${p[1]}`).join(' ')+` L${pts[pts.length-1][0]},${B} Z`,fill:`url(#${gid})`,class:'area'},s); }
    el('path',{d:'M'+pts.map(p=>`${p[0]},${p[1]}`).join(' L'),fill:'none',stroke:colors[k],'stroke-width':2,
      'stroke-linejoin':'round','stroke-linecap':'round',pathLength:1,class:'trazo'},s);
    if(ns>1){ const p=pts[pts.length-1]; txt(s,p[0]+8,p[1]+4,series[k],'dir'); }
  }
  if(mark) data.forEach((d,i)=>{ if(!mark(d)) return;
    el('circle',{cx:X(i),cy:Y(d[1]),r:5,fill:colors[1]||colors[0],stroke:'var(--surface)','stroke-width':2,class:'hito'},s); });
  const cross=el('line',{x1:0,x2:0,y1:T,y2:B,class:'cruz'},s);
  const dots=series.map((nm,k)=>el('circle',{r:4.5,fill:colors[k],stroke:'var(--surface)','stroke-width':2,class:'pto'},s));
  const hit=el('rect',{x:L,y:T,width:W-L-R,height:h,class:'hit'},s);
  hit.addEventListener('pointermove',e=>{
    const bb=s.getBoundingClientRect(); const px=(e.clientX-bb.left)/bb.width*W;
    let i=Math.round((px-L)/(W-L-R)*(data.length-1)); i=Math.max(0,Math.min(data.length-1,i));
    s.classList.add('foco'); cross.setAttribute('x1',X(i)); cross.setAttribute('x2',X(i));
    dots.forEach((c,k)=>{ c.setAttribute('cx',X(i)); c.setAttribute('cy',Y(data[i][k+1])); });
    showTip(e,`<b>${esc(lab(data[i]))}</b>`+series.map((nm,k)=>
      `<i style="background:${colors[k]}"></i>${esc(nm)} ${nf.format(data[i][k+1])}`).join('<br>'));
  });
  hit.addEventListener('pointerleave',()=>{ s.classList.remove('foco'); hideTip(); });
  const step=Math.ceil(data.length/14);
  data.forEach((d,i)=>{ if(i%step) return; txt(s,X(i),B+16,lab(d),'eje','middle'); });
  return mirar(s);
}
// mapa de calor
function heat(rows,colsLab,{L=300,cw=null,rowh=26,fmtc=c=>c}={}){
  const W=760; cw=cw||Math.min(64,(W-L-10)/colsLab.length);
  const H=rowh*rows.length+30;
  const s=svg(W,H); s.classList.add('hm');
  const max=Math.max(...rows.flatMap(r=>r.vals),1);
  colsLab.forEach((c,j)=>txt(s,L+j*cw+cw/2,14,fmtc(c),'eje','middle'));
  rows.forEach((r,i)=>{ const y=22+i*rowh;
    let nm=r.lab; const largo=nm.length>46; if(largo) nm=nm.slice(0,45)+'…';
    const t=txt(s,L-10,y+rowh/2+3,nm,'lab','end'); if(largo){ const ti=el('title',{},t); ti.textContent=r.lab; }
    r.vals.forEach((v,j)=>{ const tt=v/max, g=el('g',{class:'g'},s);
      const k=v===0?-1:Math.min(5,Math.floor(Math.pow(tt,.55)*6));
      const x=L+j*cw;
      const m=el('rect',{x:x+1,y:y+1,width:cw-2,height:rowh-2,rx:3,fill:k<0?'var(--surface-2)':SEQ[k],class:'mk'+(k<0?' cero':'')},g);
      m.style.setProperty('--i',i+j);
      if(v>0&&cw>36) txt(g,x+cw/2,y+rowh/2+4,nf.format(v),k>=3?'val inv':'val','middle');
      el('rect',{x,y,width:cw,height:rowh,class:'hit'},g);
      hover(g,s,()=>`<b>${nf.format(v)}</b>${esc(r.lab)} · ${esc(fmtc(colsLab[j]))}`); });
  });
  return mirar(s);
}
