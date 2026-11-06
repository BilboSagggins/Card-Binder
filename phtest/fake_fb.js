
(function(){
const store = { settings:{masterPin:{salt:'abc',hash:'bd4521644e7de0d1e82232cc519b3cd6b7b608426c2f8c8e1574ec4499933f21'}}, users: { kyle:{name:'Kyle',order:1,pin:{salt:'abc',hash:'c091ca128ce50048b00e132064b3476d917bc3792884f17762def89731a95cb1'}}, dustin:{name:'Dustin',order:2,pin:{salt:'abc',hash:'8336fc379abb735bba92c59402dfe41ef799ba0c35bcf6b94b39a726cfd2209f'}} },
  binders: { kyle:{ cover:{color:'#7c2d12', title:"Kyle's Vault", showTitle:true} } } };
const L = [];
const get = p => p.split('/').filter(Boolean).reduce((o,k)=>o==null?null:o[k], store) ?? null;
const put = (p,v) => { const ks=p.split('/').filter(Boolean); let o=store; ks.slice(0,-1).forEach(k=>{ if(o[k]==null||typeof o[k]!=='object') o[k]={}; o=o[k]; }); o[ks.at(-1)] = v==null?undefined:JSON.parse(JSON.stringify(v)); };
const snap = p => ({ val: () => { const v=get(p); return v==null?null:JSON.parse(JSON.stringify(v)); } });
const fire = (p = '') => L.forEach(l => { if (l.p===p || l.p.startsWith(p+'/') || p.startsWith(l.p+'/')) setTimeout(()=>l.cb(snap(l.p)),0); });
const ref = (p = '') => ({
  once(ev, cb){ const s=snap(p); cb&&cb(s); return Promise.resolve(s); },
  on(ev, cb){ if(p==='.info/connected'){ cb({val:()=>true}); return cb; } L.push({p,cb}); setTimeout(()=>cb(snap(p)),10); return cb; },
  off(){ for(let i=L.length-1;i>=0;i--) if(L[i].p===p) L.splice(i,1); },
  set(v){ put(p,v); fire(p); return Promise.resolve(); },
  remove(){ put(p,null); fire(p); return Promise.resolve(); },
  update(v){ Object.entries(v).forEach(([k,x])=>put(p+'/'+k,x)); fire(p); return Promise.resolve(); },
  child(k){ return ref(p+'/'+k); }, orderByKey(){return this}, limitToLast(){return this}
});
window.__store = store;
window.firebase = { initializeApp(){}, database(){ return { ref }; } };
})();
