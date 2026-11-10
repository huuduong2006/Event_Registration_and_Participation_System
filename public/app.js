/* TASK 4.1 - Giao diện staff quét QR (mobile/web) */
(() => {
  const $ = (id) => document.getElementById(id);
  const store = {
    get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
    set: (k, v) => { try { localStorage.setItem(k, v); } catch {} },
    del: (k) => { try { localStorage.removeItem(k); } catch {} },
  };

  let token = store.get('token');
  let eventId = null;
  let scanner = null;
  let busy = false;                 // đang hiển thị kết quả / đang gọi API -> bỏ qua frame quét mới
  let lastCode = '', lastAt = 0;    // chống đọc lặp cùng 1 mã liên tiếp
  let audioCtx;

  // ---------- helpers ----------
  async function api(path, opts = {}) {
    const res = await fetch(path, {
      ...opts,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
    if (res.status === 401 && path !== '/api/auth/login') { logout(); throw new Error('Hết phiên'); }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `Lỗi ${res.status}`);
    return data;
  }
  const show = (id) => { ['view-login', 'view-events', 'view-main'].forEach((v) => ($(v).hidden = v !== id)); };
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmtTime = (s) => (s ? new Date(s.replace(' ', 'T') + 'Z').toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '');

  function beep(freq, ms) {
    try {
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      const o = audioCtx.createOscillator(), g = audioCtx.createGain();
      o.frequency.value = freq; o.connect(g); g.connect(audioCtx.destination);
      g.gain.value = 0.15; o.start(); o.stop(audioCtx.currentTime + ms / 1000);
    } catch {}
  }
  function feedback(result) {
    if (result === 'SUCCESS') { beep(880, 150); navigator.vibrate?.(80); }
    else { beep(220, 500); navigator.vibrate?.([200, 100, 200]); }
  }

  // ---------- đăng nhập ----------
  $('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    $('login-error').hidden = true;
    try {
      const r = await api('/api/auth/login', { method: 'POST', body: { username: $('username').value, password: $('password').value } });
      token = r.token; store.set('token', token);
      $('password').value = '';
      loadEvents();
    } catch (err) { $('login-error').textContent = err.message; $('login-error').hidden = false; }
  });
  function logout() { stopScanner(); token = null; store.del('token'); show('view-login'); }
  $('btn-logout').onclick = logout;

  // ---------- chọn sự kiện ----------
  async function loadEvents() {
    show('view-events');
    const list = $('event-list');
    list.innerHTML = '<li>Đang tải…</li>';
    try {
      const events = await api('/api/events');
      list.innerHTML = events.length ? '' : '<li>Chưa có sự kiện nào đang mở</li>';
      events.forEach((ev) => {
        const li = document.createElement('li');
        li.innerHTML = `<div><b>${esc(ev.name)}</b><small>${esc(ev.location || '')} ${esc(ev.startTime || '')}</small></div><button class="btn primary">Vào</button>`;
        li.querySelector('button').onclick = () => openEvent(ev);
        list.appendChild(li);
      });
    } catch (err) { list.innerHTML = `<li>${esc(err.message)}</li>`; }
  }
  $('btn-back').onclick = () => { stopScanner(); loadEvents(); };

  // ---------- màn hình chính ----------
  function openEvent(ev) {
    eventId = ev.id;
    $('event-name').textContent = ev.name;
    show('view-main');
    switchTab('scan');
    refreshStats();
  }

  function renderStats(s) {
    $('st-in').textContent = s.checkedIn; $('st-rem').textContent = s.remaining; $('st-total').textContent = s.total;
    $('st-bar').style.width = s.total ? `${(s.checkedIn / s.total) * 100}%` : '0';
  }
  async function refreshStats() {
    try {
      const s = await api(`/api/checkin/stats?eventId=${eventId}`);
      renderStats(s);
      $('recent-list').innerHTML = s.recent.map((r) => {
        const cls = r.result === 'SUCCESS' ? 'ok' : r.result === 'WRONG_EVENT' ? 'warn' : 'bad';
        return `<li><div><b>${esc(r.fullName || '(không xác định)')}</b><small>${fmtTime(r.at)} · ${r.method === 'MANUAL' ? 'Thủ công' : 'QR'}</small></div><span class="tag ${cls}">${r.result}</span></li>`;
      }).join('') || '<li>Chưa có lượt quét</li>';
    } catch {}
  }

  document.querySelectorAll('.tabs button').forEach((b) => (b.onclick = () => switchTab(b.dataset.tab)));
  function switchTab(name) {
    document.querySelectorAll('.tabs button').forEach((b) => b.classList.toggle('active', b.dataset.tab === name));
    ['scan', 'manual', 'recent'].forEach((t) => ($('tab-' + t).hidden = t !== name));
    if (name === 'scan') startScanner(); else stopScanner();
    if (name === 'recent') refreshStats();
  }

  // ---------- camera scanner ----------
  let cameras = [], camIdx = 0, torchOn = false;
  async function startScanner() {
    if (scanner) return;
    $('cam-msg').textContent = 'Đang khởi động camera…';
    try {
      scanner = new Html5Qrcode('reader', { formatsToSupport: [Html5QrcodeSupportedFormats.QR_CODE], verbose: false });
      cameras = await Html5Qrcode.getCameras();
      const back = cameras.findIndex((c) => /back|rear|environment|sau/i.test(c.label));
      camIdx = back >= 0 ? back : 0;
      await launchCamera();
      $('btn-cam-switch').hidden = cameras.length < 2;
    } catch (err) {
      scanner = null;
      $('cam-msg').textContent = 'Không mở được camera (cần HTTPS + cấp quyền). Dùng tab Thủ công hoặc máy quét USB.';
    }
  }
  async function launchCamera() {
    await scanner.start(
      cameras.length ? cameras[camIdx].id : { facingMode: 'environment' },
      { fps: 15, qrbox: (w, h) => { const s = Math.floor(Math.min(w, h) * 0.75); return { width: s, height: s }; }, aspectRatio: 1 },
      onDecoded, () => {}
    );
    $('cam-msg').textContent = 'Đưa mã QR vào khung';
    try { $('btn-torch').hidden = !scanner.getRunningTrackCapabilities().torch; } catch { $('btn-torch').hidden = true; }
  }
  async function stopScanner() {
    if (!scanner) return;
    const s = scanner; scanner = null;
    try { await s.stop(); s.clear(); } catch {}
  }
  $('btn-cam-switch').onclick = async () => {
    if (!scanner) return;
    await scanner.stop(); camIdx = (camIdx + 1) % cameras.length; await launchCamera();
  };
  $('btn-torch').onclick = async () => {
    try { torchOn = !torchOn; await scanner.applyVideoConstraints({ advanced: [{ torch: torchOn }] }); } catch {}
  };

  function onDecoded(text) {
    const now = Date.now();
    if (busy || (text === lastCode && now - lastAt < 4000)) return; // chống đọc lặp
    lastCode = text; lastAt = now;
    submitScan(text);
  }

  // ---------- máy quét USB/Bluetooth (giả lập bàn phím, kết thúc bằng Enter) ----------
  $('wedge').addEventListener('keydown', (e) => {
    if (e.key !== 'Enter') return;
    e.preventDefault();
    const v = e.target.value.trim(); e.target.value = '';
    if (v && !busy) submitScan(v);
  });

  // ---------- gọi API check-in ----------
  async function submitScan(code) {
    busy = true;
    try {
      const r = await api('/api/checkin/scan', { method: 'POST', body: { token: code, eventId } });
      renderStats(r.stats);
      showResult(r);
    } catch (err) {
      showResult({ result: 'INVALID', message: err.message.includes('fetch') ? 'Mất kết nối mạng – thử lại' : err.message });
    }
  }

  const META = {
    SUCCESS: { icon: '✔', title: 'HỢP LỆ' },
    ALREADY_USED: { icon: '✖', title: 'VÉ ĐÃ SỬ DỤNG' },
    INVALID: { icon: '✖', title: 'VÉ KHÔNG HỢP LỆ' },
    WRONG_EVENT: { icon: '!', title: 'SAI SỰ KIỆN' },
  };
  let autoClose;
  function showResult(r) {
    const m = META[r.result] || META.INVALID;
    const box = $('result');
    box.className = `result ${r.result}`;
    $('r-icon').textContent = m.icon;
    $('r-title').textContent = m.title;
    $('r-name').textContent = r.attendee?.fullName || '';
    $('r-ticket').textContent = r.attendee ? `Vé ${r.attendee.ticketType}` : '';
    let msg = r.message || '';
    if (r.firstCheckin) msg += `\nCheck-in lúc ${fmtTime(r.firstCheckin.at)}${r.firstCheckin.by ? ' bởi ' + r.firstCheckin.by : ''}`;
    $('r-msg').style.whiteSpace = 'pre-line';
    $('r-msg').textContent = msg;
    box.hidden = false;
    feedback(r.result);
    clearTimeout(autoClose);
    // Thành công tự đóng sau 1.5s để dòng người đi nhanh; cảnh báo đỏ/vàng phải bấm xác nhận.
    if (r.result === 'SUCCESS') autoClose = setTimeout(closeResult, 1500);
  }
  function closeResult() {
    clearTimeout(autoClose);
    $('result').hidden = true;
    busy = false;
    if (!$('tab-manual').hidden) return;
    $('wedge').focus({ preventScroll: true });
  }
  $('r-close').onclick = closeResult;

  // ---------- check-in thủ công ----------
  let searchTimer, pending = null;
  $('search').addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(doSearch, 300);
  });
  async function doSearch() {
    const q = $('search').value.trim();
    const ul = $('search-results');
    if (q.length < 2) { ul.innerHTML = ''; return; }
    try {
      const rows = await api(`/api/checkin/search?eventId=${eventId}&q=${encodeURIComponent(q)}`);
      ul.innerHTML = rows.length ? '' : '<li>Không tìm thấy</li>';
      rows.forEach((a) => {
        const li = document.createElement('li');
        li.innerHTML = `<div><b>${esc(a.fullName)}</b><small>${esc(a.email)} · ${esc(a.phone)} · ${esc(a.ticketType)}</small></div>` +
          (a.checkedIn ? `<span class="tag ok">Đã vào ${fmtTime(a.checkedInAt)}</span>` : '<button class="btn primary">Check-in</button>');
        const b = li.querySelector('button');
        if (b) b.onclick = () => openManual(a);
        ul.appendChild(li);
      });
    } catch (err) { ul.innerHTML = `<li>${esc(err.message)}</li>`; }
  }
  function openManual(a) {
    pending = a;
    $('md-name').textContent = a.fullName;
    $('md-info').textContent = `${a.email} · ${a.phone} · Vé ${a.ticketType}`;
    $('md-note').value = '';
    $('manual-dialog').showModal();
  }
  $('md-cancel').onclick = () => $('manual-dialog').close();
  $('manual-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!pending) return;
    const a = pending;
    $('manual-dialog').close();
    try {
      const r = await api('/api/checkin/manual', { method: 'POST', body: { attendeeId: a.id, eventId, note: $('md-note').value } });
      renderStats(r.stats);
      busy = true; showResult(r);
      doSearch();
    } catch (err) { alert(err.message); }
  });

  // ---------- trạng thái mạng + PWA ----------
  const setNet = () => { $('net').className = 'net ' + (navigator.onLine ? 'ok' : 'off'); };
  addEventListener('online', setNet); addEventListener('offline', setNet); setNet();
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});

  // ---------- khởi động ----------
  if (token) loadEvents(); else show('view-login');
})();
