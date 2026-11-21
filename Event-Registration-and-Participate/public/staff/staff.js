const api = makeApi("int_token", () => { api.store.clear(); boot(); });
const G = { ev: null, scanner: null, busy: false, last: "", lastAt: 0, timer: null };
const show = id => ["login", "home", "gate"].forEach(s => $("#" + s).hidden = s !== id);

function boot() {
  stopScanner(); const u = api.store.token ? api.store.user : null;
  if (u && u.role === "ADMIN") { location.href = "/admin/"; return; }
  if (!u || u.role !== "STAFF") { show("login"); return; }
  $("#hello").textContent = "Xin chào, " + u.fullName; show("home"); loadSchedule();
}
$("#lform").addEventListener("submit", async e => {
  e.preventDefault(); $("#lerr").hidden = true;
  try { const r = await api.post("/api/auth/login", { ...Object.fromEntries(new FormData(e.target)), portal: "internal" }, true); api.store.set(r.token, r.user); boot(); }
  catch (err) { $("#lerr").textContent = err.message; $("#lerr").hidden = false; }
});
$("#logout").onclick = async () => { try { await api.post("/api/auth/logout"); } catch { } api.store.clear(); boot(); };

/* ---------- lịch trực ---------- */
async function loadSchedule() {
  const ul = $("#sched");
  try {
    const rows = await api.get("/api/staff/schedule");
    ul.innerHTML = rows.length ? rows.map(a => `<li class="item"><div><b>${esc(a.eventName)}</b><small>${esc(a.workArea)} · ${a.shiftStartTime || a.shiftEndTime ? fmtDT(a.shiftStartTime) + " → " + fmtDT(a.shiftEndTime) : "Cả sự kiện"}</small>
      <span class="tag ${a.shiftState === "ON_SHIFT" ? "ok" : "warn"}">${SHIFT_VN[a.shiftState]}</span></div>
      <button class="btn primary" data-open="${a.eventId}" data-name="${esc(a.eventName)}">Vào cổng</button></li>`).join("")
      : `<li class="item mute">Bạn chưa được phân công sự kiện nào. Hãy liên hệ Administrator.</li>`;
  } catch (e) { ul.innerHTML = `<li class="item err">${esc(e.message)}</li>`; }
}
$("#sched").addEventListener("click", e => { const b = e.target.closest("[data-open]"); if (b) openGate(b.dataset.open, b.dataset.name); });

/* ---------- màn hình cổng ---------- */
async function openGate(id, name) {
  G.ev = { id, name }; $("#gtitle").textContent = name; show("gate"); switchTab("scan"); await refresh(); startScanner();
}
$("#back").onclick = () => { stopScanner(); show("home"); loadSchedule(); };
async function refresh() {
  try {
    const s = await api.get(`/api/staff/events/${G.ev.id}/stats`);
    $("#sReg").textContent = s.registered; $("#sIn").textContent = s.checkedIn; $("#sLeft").textContent = s.remaining;
    $("#bar").style.width = (s.registered ? s.checkedIn / s.registered * 100 : 0) + "%";
    $("#garea").textContent = "📍 " + s.workArea; const t = $("#gshift"); t.textContent = SHIFT_VN[s.shiftState]; t.className = "tag " + (s.shiftState === "ON_SHIFT" ? "ok" : "warn");
    $("#recent").innerHTML = s.recent.map(r => `<li class="item"><div><b>${esc(r.attendeeName || "Mã không hợp lệ")}</b><small>${fmtDT(r.at)} · ${r.method} · ${esc(r.staffName || "")}</small></div>
      <span class="tag ${r.outcome === "VALID" ? "ok" : r.outcome === "WRONG_EVENT" ? "warn" : "bad"}">${r.outcome}</span></li>`).join("") || `<li class="item mute">Chưa có lượt quét.</li>`;
  } catch (e) { toast(e.message); }
}
function switchTab(t) {
  $$(".tabs button").forEach(b => b.classList.toggle("on", b.dataset.tab === t));
  ["scan", "find", "recent"].forEach(x => $("#t-" + x).hidden = x !== t);
  if (t === "recent") refresh();
}
$(".tabs").addEventListener("click", e => { const b = e.target.closest("[data-tab]"); if (b) switchTab(b.dataset.tab); });

/* ---------- quét QR ---------- */
async function startScanner() {
  if (G.scanner || typeof Html5Qrcode === "undefined") return;
  $("#camMsg").textContent = "Đang mở camera…";
  try {
    G.scanner = new Html5Qrcode("reader");
    await G.scanner.start({ facingMode: "environment" }, { fps: 10, qrbox: { width: 240, height: 240 } }, code => submitCode(code), () => { });
    $("#camMsg").textContent = "Đưa mã QR vào khung.";
  } catch {
    G.scanner = null; $("#camMsg").textContent = "Không mở được camera (cần HTTPS hoặc localhost và quyền camera). Dùng ô nhập mã/máy quét bên dưới.";
  }
}
async function stopScanner() { const s = G.scanner; G.scanner = null; if (s) { try { await s.stop(); s.clear(); } catch { } } }

async function submitCode(code) {
  code = String(code || "").trim(); const now = Date.now();
  if (!code || G.busy || (code === G.last && now - G.lastAt < 3000)) return;
  G.busy = true; G.last = code; G.lastAt = now;
  try { showResult(await api.post("/api/staff/check-in/scan", { qrCodeData: code, eventId: G.ev.id })); }
  catch (e) { showError(e); }
}
$("#codeForm").addEventListener("submit", e => { e.preventDefault(); const v = $("#codeIn").value; $("#codeIn").value = ""; submitCode(v); });

const LOOK = { GREEN: ["✔", "HỢP LỆ"], RED: ["✖", "TỪ CHỐI"], YELLOW: ["⚠", "KHÔNG ĐÚNG SỰ KIỆN"] };
function showResult(r) {
  navigator.vibrate && navigator.vibrate(r.signal === "GREEN" ? 80 : [200, 80, 200]);
  const box = $("#result"); box.className = "result " + r.signal; box.hidden = false;
  $("#rIcon").textContent = LOOK[r.signal][0]; $("#rTitle").textContent = r.result === "ALREADY_USED" ? "VÉ ĐÃ DÙNG" : LOOK[r.signal][1];
  $("#rName").textContent = r.attendee ? r.attendee.fullName : ""; $("#rTicket").textContent = r.attendee ? r.attendee.ticketType : "";
  let m = r.message; if (r.firstCheckin) m += ` Lần đầu: ${fmtDT(r.firstCheckin.at)} bởi ${r.firstCheckin.by || "?"} (${r.firstCheckin.method}).`;
  $("#rMsg").textContent = m; $("#rOk").focus(); clearTimeout(G.timer);
  if (r.signal === "GREEN") G.timer = setTimeout(closeResult, 2200);
  refresh();
}
function showError(e) {   // lỗi nghiệp vụ (ngoài ca, chưa phân công…) hiển thị như kết quả ĐỎ
  showResult({ result: "ERROR", signal: "RED", message: e.message });
}
function closeResult() { clearTimeout(G.timer); $("#result").hidden = true; G.busy = false; }
$("#rOk").onclick = closeResult;

/* ---------- tìm khách & check-in thủ công ---------- */
let qt;
$("#q").addEventListener("input", e => { clearTimeout(qt); qt = setTimeout(() => search(e.target.value), 300); });
async function search(q) {
  const ul = $("#found"); if (q.trim().length < 2) { ul.innerHTML = ""; return; }
  try {
    const rows = await api.get(`/api/staff/events/${G.ev.id}/attendees?q=${encodeURIComponent(q)}`);
    ul.innerHTML = rows.map(a => `<li class="item"><div><b>${esc(a.fullName)}</b><small>${esc(a.ticketType)} · ${esc(a.registrationId)}<br>${esc(a.email)}</small></div>
      ${a.checkInStatus === "CHECKED_IN" ? `<span class="tag ok">Đã vào</span>` : `<button class="btn primary" data-reg="${esc(a.registrationId)}" data-name="${esc(a.fullName)}">Check-in</button>`}</li>`).join("") || `<li class="item mute">Không tìm thấy.</li>`;
  } catch (e) { ul.innerHTML = `<li class="item err">${esc(e.message)}</li>`; }
}
let pendingReg = null;
$("#found").addEventListener("click", e => { const b = e.target.closest("[data-reg]"); if (!b) return;
  pendingReg = b.dataset.reg; $("#dwho").textContent = b.dataset.name + " · " + pendingReg; $("#note").value = ""; $("#derr").hidden = true; $("#dlg").showModal(); });
$("#dcancel").onclick = () => $("#dlg").close();
$("#dform").addEventListener("submit", async e => {
  e.preventDefault();
  try { const r = await api.post("/api/staff/check-in/manual", { registrationId: pendingReg, note: $("#note").value, eventId: G.ev.id });
    $("#dlg").close(); G.busy = true; showResult(r); search($("#q").value); }
  catch (err) { $("#derr").textContent = err.message; $("#derr").hidden = false; }
});
boot();
