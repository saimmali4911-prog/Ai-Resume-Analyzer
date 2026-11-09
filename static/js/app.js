const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=t=>String(t??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const ring=(v,l)=>`<div class="ring" style="--v:${+v||0}"><div><b>${+v||0}</b><small>${esc(l)}</small></div></div>`;
const bar=(l,v)=>`<div class="mb-3"><div class="d-flex justify-content-between small"><span>${esc(l)}</span><b>${+v||0}%</b></div><div class="bar"><i data-w="${+v||0}"></i></div></div>`;
const list=(t,a,c='')=>Array.isArray(a)&&a.length?`<div class="col-md-6"><div class="cardx ${c}"><h6>${t}</h6><ul class="mb-0">${a.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div></div>`:'';
const chips=(a,c='')=>(a||[]).map(x=>`<span class="chip ${c}">${esc(x)}</span>`).join('');
const cap=s=>s.charAt(0).toUpperCase()+s.slice(1).replace(/_/g,' ');
const txt=v=>Array.isArray(v)?v.join(', '):v;

const R={
analysis:(d,s)=>`<div class="row g-3 mb-3"><div class="col-md-4"><div class="cardx text-center"><h6>Overall Score</h6>${ring(s,'/ 100')}</div></div>
<div class="col-md-8"><div class="cardx"><canvas id="ch" height="130"></canvas></div></div></div>
<div class="row g-3 mb-3"><div class="col-md-5"><div class="cardx">${Object.entries(d.scores||{}).map(([k,v])=>bar(cap(k),v)).join('')}</div></div>
<div class="col-md-7"><div class="cardx"><h6>Detailed Feedback</h6><p class="mb-0">${esc(d.feedback)}</p></div></div></div>
<div class="row g-3 mb-3">${list('✅ Strengths',d.strengths,'ok')}${list('⚠️ Weaknesses',d.weaknesses,'bad')}${list('Missing Information',d.missing)}${list('Areas Requiring Improvement',d.improvements)}</div>
<div class="row g-3">${Object.entries(d.sections||{}).map(([k,v])=>`<div class="col-md-4"><div class="cardx"><h6>${esc(cap(k))}</h6><p class="small mb-0">${esc(txt(v))}</p></div></div>`).join('')}</div>`,
ats:(d,s)=>{const r=d.rule||{};return `<div class="row g-3 mb-3"><div class="col-md-4"><div class="cardx text-center"><h6>ATS Score</h6>${ring(s,'/ 100')}<span class="chip mt-2">${esc(d.status)}</span></div></div>
<div class="col-md-8"><div class="cardx"><h6>Formatting &amp; structure checks</h6>${(r.checks||[]).map(c=>`<div class="d-flex gap-2 mb-2"><i class="bi ${c.ok?'bi-check-circle-fill text-success':'bi-x-circle-fill text-danger'}"></i><div><b>${esc(c.name)}</b><div class="small text-muted">${esc(c.detail)}</div></div></div>`).join('')}</div></div></div>
<div class="cardx mb-3" style="height:auto"><h6>Missing sections</h6>${chips(r.missing,'bad')||'<span class="text-success">None — all core sections found 🎉</span>'}</div>
<div class="row g-3">${list('Detected Issues',d.semantic_issues,'bad')}${list('Keyword Optimization',d.keyword_suggestions)}${list('Actionable Recommendations',d.recommendations,'ok')}</div>
<p class="small text-muted mt-3">This is an estimate (60% rule-based, 40% TF-IDF). It does not guarantee compatibility with every ATS.</p>`},
match:(d,s)=>`<div class="row g-3 mb-3"><div class="col-md-4"><div class="cardx text-center"><h6>Job Match</h6>${ring(s,'% match')}</div></div>
<div class="col-md-8"><div class="cardx"><canvas id="ch" height="120"></canvas></div></div></div>
<div class="row g-3 mb-3"><div class="col-md-6"><div class="cardx"><h6>Matching skills</h6>${chips(d.matching_skills,'good')||'—'}</div></div>
<div class="col-md-6"><div class="cardx"><h6>Missing skills</h6>${chips(d.missing_skills,'bad')||'—'}</div></div>
<div class="col-12"><div class="cardx"><h6>Recommended keywords</h6>${chips(d.keywords)||'—'}</div></div>
<div class="col-md-6"><div class="cardx"><h6>Experience comparison</h6><p class="mb-0">${esc(d.experience_comparison)}</p></div></div>
<div class="col-md-6"><div class="cardx"><h6>Education comparison</h6><p class="mb-0">${esc(d.education_comparison)}</p></div></div></div>
<div class="row g-3">${list('Relevant Experience',d.relevant_experience,'ok')}${list('Missing Qualifications',d.missing_qualifications,'bad')}${list('Improvement Suggestions',d.suggestions)}</div>`,
improve:(d)=>`<div class="row g-3 mb-3"><div class="col-md-6"><div class="cardx"><h6>Original</h6><div class="cmp" id="orig">${esc(d.original)||'<span class="text-muted">—</span>'}</div></div></div>
<div class="col-md-6"><div class="cardx" style="border:2px solid #a5b4fc"><div class="d-flex justify-content-between"><h6>Improved</h6><button class="btn btn-sm btn-grad" data-copy="#impr"><i class="bi bi-clipboard"></i> Copy</button></div><div class="cmp" id="impr">${esc(d.improved)}</div></div></div></div>
<div class="row g-3"><div class="col-md-6"><div class="cardx"><h6>Strong action verbs</h6>${chips(d.action_verbs)||'—'}</div></div><div class="col-md-6"><div class="cardx"><h6>Recommended skills</h6>${chips(d.recommended_skills)||'—'}</div></div>
${list('What changed',d.changes)}${d.notes?`<div class="col-md-6"><div class="cardx"><h6>Notes</h6><p class="mb-0">${esc(d.notes)}</p></div></div>`:''}</div>`
};
const C={
analysis:d=>new Chart($('#ch'),{type:'radar',data:{labels:Object.keys(d.scores||{}).map(cap),datasets:[{data:Object.values(d.scores||{}),backgroundColor:'#4f46e533',borderColor:'#4f46e5',pointBackgroundColor:'#8b5cf6'}]},options:{scales:{r:{min:0,max:100}},plugins:{legend:{display:false}}}}),
match:d=>new Chart($('#ch'),{type:'bar',data:{labels:['Required','Matching','Missing'],datasets:[{data:[(d.required_skills||[]).length,(d.matching_skills||[]).length,(d.missing_skills||[]).length],backgroundColor:['#6366f1','#22c55e','#ef4444'],borderRadius:8}]},options:{plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,ticks:{precision:0}}}}})
};

// sidebar active link + mobile menu
$$('.side a').forEach(a=>{if(a.pathname===location.pathname)a.classList.add('active')});
$('#menu')?.addEventListener('click',()=>$('.side').classList.toggle('open'));

// AI tool pages — Flask version: read csrf_token from hidden input, not Django cookie
const f=$('#toolform');
if(f){const kind=f.dataset.kind;
 const show=res=>{$('#result').innerHTML=R[kind](res.data,res.score);setTimeout(()=>$$('.bar i').forEach(b=>b.style.width=b.dataset.w+'%'),60);C[kind]&&C[kind](res.data);$('#result').scrollIntoView({behavior:'smooth'})};
 f.addEventListener('submit',async e=>{e.preventDefault();const b=$('button[type=submit]',f),sp=$('.spin');b.disabled=true;sp.classList.remove('d-none');$('#alert').innerHTML='';
  try{
   // Flask-WTF: csrf_token is in a hidden form field (not a cookie)
   const fd=new FormData(f);
   const r=await fetch(f.dataset.url,{method:'POST',body:fd});
   let j;try{j=await r.json()}catch{throw new Error('Unexpected server response.')}
   if(!r.ok)throw new Error(j.error||'Request failed');show(j)}
  catch(err){$('#alert').innerHTML=`<div class="alert alert-danger">${esc(err.message)} Click "Run Analysis" to retry.</div>`}
  finally{b.disabled=false;sp.classList.add('d-none')}});
 const L=$('#loaded');if(L&&L.textContent.trim()!=='null')show(JSON.parse(L.textContent));
}

// copy to clipboard
document.addEventListener('click',e=>{const b=e.target.closest('[data-copy]');if(!b)return;
 navigator.clipboard.writeText($(b.dataset.copy).innerText).then(()=>{const o=b.innerHTML;b.innerHTML='<i class="bi bi-check2"></i> Copied';setTimeout(()=>b.innerHTML=o,1500)})});

// upload: drag & drop + client validation + preview modal
const drop=$('#drop');
if(drop){const inp=$('#fileinp'),max=+$('#upform').dataset.max;
 const pick=()=>{const fl=inp.files[0];if(!fl)return;const ok=/\.(pdf|docx)$/i.test(fl.name);
  if(!ok||fl.size>max*1048576){alert(!ok?'Only PDF and DOCX files are allowed.':'File is larger than '+max+' MB.');inp.value='';return}
  $('#dname').textContent=fl.name+' ('+(fl.size/1024).toFixed(0)+' KB)'};
 inp.addEventListener('change',pick);
 ['dragover','dragenter'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.add('over')}));
 ['dragleave','drop'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.remove('over')}));
 drop.addEventListener('drop',e=>{inp.files=e.dataTransfer.files;pick()});
}
$$('.preview').forEach(b=>b.addEventListener('click',async()=>{const j=await (await fetch(b.dataset.url)).json();$('#pt').textContent=j.title;$('#pb').textContent=j.text;new bootstrap.Modal('#pm').show()}));

// dashboard chart
const cd=$('#chart');
if(cd&&$('#prog')){const d=JSON.parse(cd.textContent),n=Math.max(d.an.length,d.ats.length,1);
 new Chart($('#prog'),{type:'line',data:{labels:Array.from({length:n},(_,i)=>'Run '+(i+1)),datasets:[{label:'Resume score',data:d.an,borderColor:'#4f46e5',backgroundColor:'#4f46e522',fill:true,tension:.35},{label:'ATS score',data:d.ats,borderColor:'#8b5cf6',tension:.35}]},options:{scales:{y:{min:0,max:100}}}})}
