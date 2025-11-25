(async function(){
  const apiBase = '/api/v1/';
  const form = document.getElementById('txForm');
  const pmSelect = document.getElementById('pmSelect');
  const scSelect = document.getElementById('subcatSelect');
  const scName = document.getElementById('subcatName');
  const msg = document.getElementById('msg');
  const tz = 'Europe/Istanbul';

  async function fetchJSON(url){
    const r = await fetch(url, {credentials:'same-origin'});
    if(!r.ok) throw new Error('Network');
    return r.json();
  }

  function setMsg(text, ok=false){
    msg.textContent = text || '';
    msg.className = ok ? 'success' : 'error';
  }

  // Fill selects
  try {
    const [pms, scs] = await Promise.all([
      fetchJSON(apiBase + 'payment-methods/'),
      fetchJSON(apiBase + 'subcategories/')
    ]);
    (pms.results || pms).forEach(pm=>{
      const o = document.createElement('option'); o.value = pm.id; o.textContent = pm.name; pmSelect.appendChild(o);
    });
    const empty = document.createElement('option'); empty.value=''; empty.textContent='(Seçim yok)'; scSelect.appendChild(empty);
    (scs.results || scs).forEach(sc=>{
      const o = document.createElement('option'); o.value = sc.id; o.textContent = sc.name; scSelect.appendChild(o);
    });
  } catch(e){
    setMsg('Seçenekler yüklenemedi. Lütfen sayfayı yenileyin.');
  }

  function toISO(dtLocal){
    // datetime-local -> ISO UTC
    // dtLocal: "YYYY-MM-DDTHH:mm"
    try { return new Date(dtLocal).toISOString(); } catch(e){ return null; }
  }

  function getCSRF(){
    return document.cookie.split('; ').find(x=>x.startsWith('csrftoken='))?.split('=')[1] || window.CSRF_TOKEN;
  }

  form.addEventListener('submit', async (ev)=>{
    ev.preventDefault();
    setMsg('');

    const fd = new FormData(form);

    // subcategory: yeni isim öncelikli
    const name = (scName.value || '').trim();
    const scSelected = scSelect.value;
    if (name){
      fd.set('subcategory_name', name);
      fd.delete('subcategory'); // id'yi gönderme
    } else if (scSelected){
      fd.set('subcategory', scSelected);
      fd.delete('subcategory_name');
    } else {
      setMsg('Alt tür seçin veya yeni bir isim girin.');
      return;
    }

    // tarih ISO
    const dtLocal = fd.get('transaction_date');
    const iso = toISO(dtLocal);
    if (!iso){ setMsg('Tarih/saat geçersiz.'); return; }
    fd.set('transaction_date', iso);

    // amount pozitif mi
    const amt = Number(fd.get('amount'));
    if (!(amt > 0)){ setMsg('Tutar pozitif olmalı.'); return; }

    // Gönder
    try{
      const r = await fetch(apiBase + 'transactions/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {'X-CSRFToken': getCSRF()},
        body: fd
      });
      if (r.status === 201){
        setMsg('İşlem kaydedildi, yönlendiriliyorsunuz...', true);
        setTimeout(()=>{ window.location.href = '/transactions/'; }, 600);
      } else {
        const data = await r.json().catch(()=> ({}));
        const detail = typeof data === 'object' ? JSON.stringify(data) : (data || r.statusText);
        setMsg('Kaydedilemedi: ' + detail);
      }
    } catch(e){
      setMsg('Ağ hatası. Lütfen tekrar deneyin.');
    }
  });
})();
