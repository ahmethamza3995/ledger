
(function () {
  // === Config & helpers ======================================================
  const apiBase = '/api/v1/';
  const tz = 'Europe/Istanbul';

  const isAdmin = (window.USER_ROLE === 'Admin');
  const showDeletedEl = document.getElementById('showDeleted'); // Admin değilse null
  const bulkHardBtn = document.getElementById('bulkHardDeleteBtn'); // Admin değilse null

  const FILTERS_STORAGE_KEY = 'ledger_filters_v1';
  const FILTER_IDS = ['date_from','date_to','type','payment_method','subcategory','min_amount','max_amount','search'];

  let showDeleted = false;
  let dt;
  let exportCount = []; // Manager için son 60 sn sayaç
  let selectedIds = new Set();

  // --- DEBUG: seçili id'leri görmek için ---
  window.SELECTED_IDS = selectedIds;
  window.SHOW_DELETED = () => showDeleted;
  // ----------------------------------------

  function formatTRY(value) {
    return new Intl.NumberFormat('tr-TR', {
      style: 'currency',
      currency: 'TRY',
      minimumFractionDigits: 2
    }).format(value);
  }
  function formatDT(iso) { return iso ? dayjs.utc(iso).tz(tz).format('DD.MM.YYYY HH:mm') : ''; }
  function toLocalInput(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    const p = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
  }
  function toISO(dtLocal) { try { return new Date(dtLocal).toISOString(); } catch { return null; } }
  async function fetchJSON(url) {
    const r = await fetch(url, { credentials: 'same-origin' });
    if (!r.ok) throw new Error('Network');
    return r.json();
  }
  function getCSRF() {
    return document.cookie.split('; ').find(x => x.startsWith('csrftoken='))?.split('=')[1] || window.CSRF_TOKEN;
  }
  function qs(id) { return document.getElementById(id); }

  function buildQuery() {
    const p = new URLSearchParams();
    const g = id => { const el = qs(id); return el ? el.value : ''; };
    if (g('date_from')) p.set('date_from', new Date(g('date_from')).toISOString());
    if (g('date_to')) p.set('date_to', new Date(g('date_to')).toISOString());
    if (g('type')) p.set('type', g('type'));
    if (g('payment_method')) p.set('payment_method', g('payment_method'));
    if (g('subcategory')) p.set('subcategory', g('subcategory'));
    if (g('min_amount')) p.set('min_amount', g('min_amount'));
    if (g('max_amount')) p.set('max_amount', g('max_amount'));
    if (g('search')) p.set('search', g('search'));
    p.set('page_size', '100000');
    if (showDeleted) p.set('only_deleted', '1');
    return p.toString();
  }

  // === Saved filters (localStorage) ==========================================
  function saveFiltersToLocalStorage() {
    try {
      const obj = { showDeleted };
      FILTER_IDS.forEach(id => { const el = qs(id); if (el) obj[id] = el.value; });
      localStorage.setItem(FILTERS_STORAGE_KEY, JSON.stringify(obj));
    } catch (_) {}
  }

  function loadSavedFilters() {
    try {
      const raw = localStorage.getItem(FILTERS_STORAGE_KEY);
      if (!raw) return;
      const obj = JSON.parse(raw);

      FILTER_IDS.forEach(id => {
        const el = qs(id);
        if (el && obj[id] !== undefined) el.value = obj[id];
      });

      if (showDeletedEl && typeof obj.showDeleted === 'boolean') {
        showDeletedEl.checked = obj.showDeleted;
        showDeleted = obj.showDeleted;
      }
    } catch (_) {}
  }

  function attachFilterAutosave() {
    FILTER_IDS.forEach(id => {
      const el = qs(id);
      if (!el) return;
      el.addEventListener('change', saveFiltersToLocalStorage);
      // typing search instantly saved as well (optional):
      if (id === 'search') el.addEventListener('input', saveFiltersToLocalStorage);
    });
    if (showDeletedEl) showDeletedEl.addEventListener('change', saveFiltersToLocalStorage);
    const applyBtn = qs('applyFilters');
    if (applyBtn) applyBtn.addEventListener('click', saveFiltersToLocalStorage);
    const clearBtn = qs('clearFilters');
    if (clearBtn) clearBtn.addEventListener('click', () => {
      try { localStorage.removeItem(FILTERS_STORAGE_KEY); } catch(_) {}
    });
  }

  // === Summary cards ==========================================================
  function ensureSummaryCardsContainer() {
    let el = document.getElementById('summaryCards');
    if (!el) {
      el = document.createElement('div');
      el.id = 'summaryCards';
      el.className = 'summary-cards card';
      const toolbar = document.querySelector('.toolbar');
      if (toolbar) toolbar.insertAdjacentElement('afterend', el);
      else document.querySelector('.container')?.prepend(el);
    }
    return el;
  }

  function renderSummaryCards(list) {
    const el = ensureSummaryCardsContainer();
    const totalIncome = list.filter(x => x.type === 'INCOME')
                            .reduce((s,x) => s + parseFloat(x.amount || 0), 0);
    const totalExpense = list.filter(x => x.type === 'EXPENSE')
                             .reduce((s,x) => s + parseFloat(x.amount || 0), 0);
    const net = totalIncome - totalExpense;

    
    const netClass = net >= 0 ? 'pos' : 'neg';

    el.innerHTML = `
      <div class="metrics">
        <div class="metric">
          <div class="metric-label">Gelir Toplamı</div>
          <div class="metric-value pos">${formatTRY(totalIncome)}</div>
          <div class="metric-sub">Filtrelere göre</div>
        </div>
        <div class="metric">
          <div class="metric-label">Gider Toplamı</div>
          <div class="metric-value neg">${formatTRY(totalExpense)}</div>
          <div class="metric-sub">Filtrelere göre</div>
        </div>
        <div class="metric">
          <div class="metric-label">Net</div>
          <div class="metric-value ${netClass}">${formatTRY(net)}</div>
          <div class="metric-sub">${showDeleted ? 'Silinenler görünümünde' : 'Aktif kayıtlar'}</div>
        </div>
        <div class="metric">
          <div class="metric-label">Kayıt Sayısı</div>
          <div class="metric-value">${list.length}</div>
          <div class="metric-sub">Tabloda gösterilen</div>
        </div>
      </div>
    `;
  }

  // Filters (fill selects) 
  async function populateFilters() {
    const [pms, scs] = await Promise.all([
      fetchJSON(apiBase + 'payment-methods/'),
      fetchJSON(apiBase + 'subcategories/')
    ]);
    const pmSel = qs('payment_method'), scSel = qs('subcategory');
    (pms.results || pms).forEach(pm => {
      const o = document.createElement('option'); o.value = pm.id; o.textContent = pm.name; pmSel && pmSel.appendChild(o);
    });
    (scs.results || scs).forEach(sc => {
      const o = document.createElement('option'); o.value = sc.id; o.textContent = sc.name; scSel && scSel.appendChild(o);
    });

    // Edit modal dropdown cache
    window._PM_CACHE = (pms.results || pms);
    window._SC_CACHE = (scs.results || scs);
  }

  // DataTables export buttons 
  function beforeExportWrapper(action) {
    if (!window.CAN_EXPORT) return action;
    return async (e, dt, node, cfg) => {
      if (window.USER_ROLE === 'Manager') {
        const now = Date.now();
        exportCount = exportCount.filter(t => now - t < 60000);
        if (exportCount.length >= 10) { alert('Son 60 saniyede 10 ihracat sınırına ulaştınız.'); return; }
        exportCount.push(now);
      }
      fetch(apiBase + 'export-log/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRF(), 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ query: buildQuery() })
      }).catch(() => { });
      action(e, dt, node, cfg);
    };
  }
  function makeExportButtons() {
    if (!window.CAN_EXPORT) return [];
    const filename = () => `transactions_${dayjs().tz(tz).format('YYYYDDMM_HHmm')}`;
    return [
      { extend: 'excelHtml5', text: 'Excel', title: 'İşlemler', filename, exportOptions: { columns: [1, 2, 3, 4, 5, 6] }, action: beforeExportWrapper($.fn.dataTable.ext.buttons.excelHtml5.action) },
      { extend: 'csvHtml5', text: 'CSV', title: 'İşlemler', filename, exportOptions: { columns: [1, 2, 3, 4, 5, 6] }, action: beforeExportWrapper($.fn.dataTable.ext.buttons.csvHtml5.action) },
      { extend: 'pdfHtml5', text: 'PDF', title: 'İşlemler', filename, exportOptions: { columns: [1, 2, 3, 4, 5, 6] }, action: beforeExportWrapper($.fn.dataTable.ext.buttons.pdfHtml5.action) },
    ];
  }

  // Row render helpers
  function renderCheckbox(id) { return `<input type="checkbox" class="checkbox row-select" data-id="${id}">`; }
  function renderActions(row) {
    const id = row.id;
    if (!row._raw.is_active) {
      // Silinmiş kayıt
      let html = '';
      if (window.CAN_RESTORE) {
        html += `<button class="btn secondary btn-restore" data-id="${id}" title="Geri Yükle">Geri Yükle</button>`;
      }
      if (isAdmin) {
        html += ` <button class="btn danger btn-hard-delete" data-id="${id}" title="Kalıcı Sil">Kalıcı Sil</button>`;
      }
      return `<div class="actions-cell">${html}</div>`;
    }
    // Aktif kayıt
    return `<div class="actions-cell">
              <button class="btn secondary btn-edit" data-id="${id}" title="Düzenle">Düzenle</button>
              <button class="btn danger btn-delete" data-id="${id}" title="Sil">Sil</button>
            </div>`;
  }

  // === Table load & paint =====================================================
  async function loadTable() {
    const url = apiBase + 'transactions/?' + buildQuery();
    const data = await fetchJSON(url);
    const list = (data.results || data);

    // ÖZET KARTLARI: her yüklemede hesapla/göster
    renderSummaryCards(list);

    const rows = list.map(x => ({
      id: x.id,
      select: renderCheckbox(x.id),
      dt: formatDT(x.transaction_date),
      amt: formatTRY(Number(x.amount)),
      pm: x.payment_method_name || x.payment_method,
      type: x.type === 'INCOME' ? 'Gelir' : 'Gider',
      sc: x.subcategory_label || x.subcategory,
      desc: x.description || '',
      receipt: x.receipt_thumbnail_url ? `<a href="${x.receipt_download_url}"><img class="thumbnail" src="${x.receipt_thumbnail_url}" alt="thumb"></a>` : '',
      actions: '', // sonra doldur
      _raw: x
    }));
    rows.forEach(r => { r.actions = renderActions(r); });

    if (dt) {
      dt.clear(); dt.rows.add(rows).draw();
      repaint();
      selectedIds.clear();
      window.SELECTED_IDS = selectedIds;
      const sa = qs('selectAll'); if (sa) sa.checked = false;
      updateBulkButton();
      return;
    }

    dt = $('#transactionsTable').DataTable({
      data: rows,
      responsive: true,
      dom: window.CAN_EXPORT ? 'Bfrtip' : 'frtip',
      buttons: window.CAN_EXPORT ? makeExportButtons() : [],
      columns: [
        { data: 'select', orderable: false, searchable: false },
        { data: 'dt' }, { data: 'amt' }, { data: 'pm' }, { data: 'type' }, { data: 'sc' }, { data: 'desc' },
        { data: 'receipt', orderable: false, searchable: false },
        { data: 'actions', orderable: false, searchable: false },
      ],
      language: {
        search: "Ara:", lengthMenu: "Göster _MENU_ kayıt",
        info: "_TOTAL_ kayıttan _START_ - _END_ arası", infoEmpty: "Kayıt yok",
        zeroRecords: "Eşleşen kayıt bulunamadı",
        paginate: { first: "İlk", last: "Son", next: "İleri", previous: "Geri" },
        buttons: { copy: "Kopyala", excel: "Excel", csv: "CSV", pdf: "PDF" }
      },
      createdRow: function (row, data) {
        row.classList.remove('income', 'expense');
        row.classList.add(data.type === 'Gelir' ? 'income' : 'expense');
        if (!data._raw.is_active) { row.style.opacity = .7; }
      }
    });
    updateBulkButton();
  }

  function repaint() {
    dt.rows().every(function () {
      const d = this.data(); const n = this.node();
      n.classList.remove('income', 'expense');
      n.classList.add(d.type === 'Gelir' ? 'income' : 'expense');
      if (!d._raw.is_active) n.style.opacity = .7; else n.style.opacity = 1;
    });
  }

  // === Bulk button state & toggle ============================================
  function updateBulkButton() {
    const btn = qs('bulkActionBtn');

    if (showDeleted && window.CAN_RESTORE) {
      // Silinen görünümü: toplu restore
      btn.textContent = 'Seçilenleri Geri Yükle';
      btn.classList.remove('danger'); btn.classList.add('secondary');
      btn.disabled = selectedIds.size === 0;

      // Yalnız Admin: toplu KALICI SİL görünür olsun
      if (bulkHardBtn) {
        bulkHardBtn.style.display = 'inline-block';
        bulkHardBtn.disabled = selectedIds.size === 0;
      }
    } else {
      // Normal görünüm: toplu soft delete
      btn.textContent = 'Seçilenleri Sil';
      btn.classList.add('danger'); btn.classList.remove('secondary');
      btn.disabled = selectedIds.size === 0;

      if (bulkHardBtn) {
        bulkHardBtn.style.display = 'none';
        bulkHardBtn.disabled = true;
      }
    }
  }

  if (showDeletedEl) {
    showDeletedEl.addEventListener('change', function () {
      showDeleted = this.checked;
      selectedIds.clear();
      window.SELECTED_IDS = selectedIds;
      const sa = qs('selectAll'); if (sa) sa.checked = false;
      updateBulkButton();
      saveFiltersToLocalStorage();
      loadTable();
    });
  }

  // === Selection handlers =====================================================
  $(document).on('change', '.row-select', function () {
    const id = Number(this.dataset.id);
    if (this.checked) selectedIds.add(id); else selectedIds.delete(id);
    window.SELECTED_IDS = selectedIds;
    qs('bulkActionBtn').disabled = selectedIds.size === 0 || (showDeleted && !window.CAN_RESTORE);
    if (bulkHardBtn && showDeleted && isAdmin) {
      bulkHardBtn.disabled = selectedIds.size === 0;
    }
  });

  $('#selectAll').on('change', function () {
    const checked = this.checked;
    $('.row-select').each(function () {
      this.checked = checked;
      const id = Number(this.dataset.id);
      if (checked) selectedIds.add(id); else selectedIds.delete(id);
    });
    window.SELECTED_IDS = selectedIds;
    qs('bulkActionBtn').disabled = selectedIds.size === 0 || (showDeleted && !window.CAN_RESTORE);
    if (bulkHardBtn && showDeleted && isAdmin) {
      bulkHardBtn.disabled = selectedIds.size === 0;
    }
  });

  // === Single actions: delete / restore / hard delete ========================
  $(document).on('click', '.btn-delete', async function () {
    const id = this.dataset.id;
    if (!confirm('Bu işlemi silmek istiyor musunuz?')) return;
    const r = await fetch(apiBase + `transactions/${id}/`, {
      method: 'DELETE', credentials: 'same-origin', headers: { 'X-CSRFToken': getCSRF() }
    });
    if (r.status === 204) await loadTable();
    else {
      const data = await r.json().catch(() => ({}));
      alert('Silinemedi: ' + (data.detail || r.statusText));
    }
  });

  $(document).on('click', '.btn-restore', async function () {
    const id = this.dataset.id;
    if (!window.CAN_RESTORE) { alert('Yetkiniz yok.'); return; }
    const r = await fetch(apiBase + `transactions/${id}/restore/`, {
      method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': getCSRF() }
    });
    if (r.ok) await loadTable();
    else {
      const data = await r.json().catch(() => ({}));
      alert('Geri yüklenemedi: ' + (data.detail || r.statusText));
    }
  });

  // Tekil hard delete
  $(document).on('click', '.btn-hard-delete', async function () {
    const id = this.dataset.id;
    if (!isAdmin) { alert('Yalnız Admin kalıcı silebilir.'); return; }
    if (!confirm('Bu işlemi KALICI olarak silmek istiyor musunuz? Bu işlem geri alınamaz.')) return;

    const r = await fetch(apiBase + `transactions/${id}/hard-delete/`, {
      method: 'DELETE',
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': getCSRF() }
    });
    if (r.status === 204) {
      await loadTable();
    } else {
      const data = await r.json().catch(() => ({}));
      alert('Kalıcı silinemedi: ' + (data.detail || r.statusText));
    }
  });

  // Toplu hard delete — delegation (buton sonradan görünse bile çalışır)
  $(document).on('click', '#bulkHardDeleteBtn', async function () {
    if (!isAdmin) { alert('Yalnız Admin kalıcı silebilir.'); return; }
    if (this.disabled) return;
    if (selectedIds.size === 0) return;
    if (!confirm(`Seçili ${selectedIds.size} kaydı KALICI olarak silmek istiyor musunuz? Bu işlem geri alınamaz.`)) return;

    const ids = Array.from(selectedIds);
    let ok = 0, fail = 0;
    for (const id of ids) {
      const r = await fetch(apiBase + `transactions/${id}/hard-delete/`, {
        method: 'DELETE',
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': getCSRF() }
      });
      if (r.status === 204) ok++; else fail++;
    }
    if (fail) alert(`${ok} kayıt kalıcı silindi, ${fail} kayıt silinemedi.`);
    await loadTable();
  });

  // === Bulk soft delete / restore ===========================================
  $('#bulkActionBtn').on('click', async function () {
    if (selectedIds.size === 0) return;

    if (showDeleted) {
      if (!window.CAN_RESTORE) { alert('Yetkiniz yok.'); return; }
      if (!confirm(`Seçili ${selectedIds.size} kaydı geri yüklemek istiyor musunuz?`)) return;

      let ok = 0, fail = 0;
      for (const id of Array.from(selectedIds)) {
        const r = await fetch(apiBase + `transactions/${id}/restore/`, {
          method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': getCSRF() }
        });
        if (r.ok) ok++; else fail++;
      }
      if (fail) alert(`${ok} kayıt geri yüklendi, ${fail} kayıt başarısız.`);
      await loadTable();

    } else {
      if (!confirm(`Seçili ${selectedIds.size} kaydı silmek istiyor musunuz?`)) return;

      let ok = 0, fail = 0;
      for (const id of Array.from(selectedIds)) {
        const r = await fetch(apiBase + `transactions/${id}/`, {
          method: 'DELETE', credentials: 'same-origin', headers: { 'X-CSRFToken': getCSRF() }
        });
        if (r.status === 204) ok++; else fail++;
      }
      if (fail) alert(`${ok} kayıt silindi, ${fail} kayıt silinemedi.`);
      await loadTable();
    }
  });

  // === Edit modal ============================================================
  function openEditModal(rowData) {
    const b = qs('editBackdrop');
    qs('editId').value = rowData.id;
    qs('editAmount').value = Number(rowData._raw.amount);
    qs('editType').value = rowData._raw.type;
    qs('editDate').value = toLocalInput(rowData._raw.transaction_date);
    qs('editDesc').value = rowData._raw.description || '';

    const pmSel = qs('editPM'); pmSel.innerHTML = '';
    (window._PM_CACHE || []).forEach(pm => { const o = document.createElement('option'); o.value = pm.id; o.textContent = pm.name; pmSel.appendChild(o); });
    pmSel.value = rowData._raw.payment_method;

    const scSel = qs('editSC'); scSel.innerHTML = '';
    const empty = document.createElement('option'); empty.value = ''; empty.textContent = '(Seçim yok)'; scSel.appendChild(empty);
    (window._SC_CACHE || []).forEach(sc => { const o = document.createElement('option'); o.value = sc.id; o.textContent = sc.name; scSel.appendChild(o); });
    scSel.value = rowData._raw.subcategory;

    qs('editSCName').value = '';
    qs('editMsg').textContent = '';
    b.style.display = 'flex';
  }
  function closeEditModal() { qs('editBackdrop').style.display = 'none'; }

  $(document).on('click', '.btn-edit', function () {
    const id = Number(this.dataset.id);
    const row = dt.rows().data().toArray().find(r => r.id === id);
    if (!row) return;
    openEditModal(row);
  });
  const cancelBtn = qs('editCancel');
  if (cancelBtn) cancelBtn.addEventListener('click', closeEditModal);

  const editForm = qs('editForm');
  if (editForm) {
    editForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      const id = qs('editId').value;
      const payload = {};
      const amt = Number(qs('editAmount').value);
      if (!(amt > 0)) { qs('editMsg').textContent = 'Tutar pozitif olmalı.'; return; }
      payload.amount = amt.toFixed(2);
      payload.type = qs('editType').value;
      const iso = toISO(qs('editDate').value);
      if (!iso) { qs('editMsg').textContent = 'Tarih/saat geçersiz.'; return; }
      payload.transaction_date = iso;
      payload.payment_method = Number(qs('editPM').value);
      const scName = qs('editSCName').value.trim();
      const scSel = qs('editSC').value;
      if (scName) { payload.subcategory_name = scName; }
      else if (scSel) { payload.subcategory = Number(scSel); }
      else { qs('editMsg').textContent = 'Alt tür seçin veya yeni bir isim girin.'; return; }
      payload.description = qs('editDesc').value;

      const r = await fetch(apiBase + `transactions/${id}/`, {
        method: 'PATCH', credentials: 'same-origin',
        headers: { 'X-CSRFToken': getCSRF(), 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (r.ok) { closeEditModal(); await loadTable(); }
      else { const data = await r.json().catch(() => ({})); qs('editMsg').textContent = 'Kaydedilemedi: ' + (JSON.stringify(data) || r.statusText); }
    });
  }

  // === Filters buttons ========================================================
  const applyBtn = qs('applyFilters');
  if (applyBtn) applyBtn.addEventListener('click', () => { saveFiltersToLocalStorage(); loadTable(); });

  const clearBtn = qs('clearFilters');
  if (clearBtn) clearBtn.addEventListener('click', () => {
    ['date_from', 'date_to', 'type', 'payment_method', 'subcategory', 'min_amount', 'max_amount', 'search'].forEach(id => {
      const el = qs(id); if (!el) return;
      if (el.tagName === 'SELECT') el.selectedIndex = 0; else el.value = '';
    });
    try { localStorage.removeItem(FILTERS_STORAGE_KEY); } catch(_) {}
    loadTable();
  });

  // === Init ==================================================================
  (async function init() {
    await populateFilters();
    loadSavedFilters();          // localStorage → UI
    attachFilterAutosave();      // UI değişince localStorage'a yaz
    updateBulkButton();          // showDeleted restore edildiyse butonları güncelle
    await loadTable();
  })();
})();
