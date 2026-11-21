const api = makeApi("int_token", () => { api.store.clear(); boot(); });
const S = { view: "events", ev: null, tab: "report", page: 1, filters: {}, staff: [], charts: [] };
const app = $("#app"), dlg = $("#dlg");

/* ---------- đăng nhập ---------- */
function boot() {
  const u = api.store.token ? api.store.user : null;
  if (u && u.role === "STAFF") { location.href = "/staff/"; return; }
  const ok = u && u.role === "ADMIN";
  $("#login").hidden = ok; $("#shell").hidden = !ok;
  if (ok) { $("#who").textContent = u.fullName; go(S.view); }
}
$("#lform").addEventListener("submit", async e => {
  e.preventDefault(); hide($("#lmsg"));
  try { const r = await api.post("/api/auth/login", { ...Object.fromEntries(new FormData(e.target)), portal: "internal" }, true);
    api.store.set(r.token, r.user); boot(); } catch (err) { showErr($("#lmsg"), err); }
});

/* ---------- hộp thoại dùng chung ---------- */
let onSubmit = null;
function openDialog(title, body, submit, okText = "Lưu") {
  $("#dtitle").textContent = title; $("#dbody").innerHTML = body; $("#dok").textContent = okText; hide($("#dmsg")); onSubmit = submit;
  $("#dok").hidden = !submit; dlg.showModal();
}
$("#dform").addEventListener("submit", async e => {
  e.preventDefault(); if (!onSubmit) return;
  try { await onSubmit(Object.fromEntries(new FormData(e.target))); } catch (err) { showErr($("#dmsg"), err); }
});
const closeDlg = () => dlg.close();

/* ---------- điều hướng ---------- */
function go(view, ev) {
  S.charts.forEach(c => c.destroy()); S.charts = [];
  S.view = view; if (ev) { S.ev = ev; S.tab = "report"; S.page = 1; S.filters = {}; }
  ({ events: viewEvents, staff: viewStaff, event: viewEvent })[view]().catch(e => app.innerHTML = `<div class="alert err">${esc(e.message)}</div>`);
}
const statusTag = s => `<span class="tag ${s === "ONGOING" ? "ok" : s === "COMPLETED" ? "" : "info"}">${STATUS_VN[s]}</span>`;
const dtl = v => v ? String(v).slice(0, 16) : "";

/* ---------- Danh sách sự kiện ---------- */
async function viewEvents() {
  const list = await api.get("/api/admin/events");
  app.innerHTML = `<div class="row"><h1 class="grow">Sự kiện</h1><button class="btn primary" data-act="newEvent">+ Tạo sự kiện</button></div>
  <div class="card tablewrap"><table><thead><tr><th>Sự kiện</th><th>Thời gian</th><th>Trạng thái</th><th>Đăng ký</th><th>Check-in</th><th></th></tr></thead><tbody>
  ${list.map(e => `<tr><td><b>${esc(e.eventName)}</b><br><span class="small mute">${esc(e.location || "")}</span></td><td>${fmtDT(e.startTime)}</td><td>${statusTag(e.status)}</td>
  <td>${e.registeredCount}/${e.maxCapacity}</td><td>${e.checkedInCount}</td>
  <td><button class="btn sm primary" data-act="open" data-id="${e.eventId}">Quản lý</button></td></tr>`).join("") || `<tr><td colspan="6" class="mute">Chưa có sự kiện. Hãy tạo sự kiện đầu tiên.</td></tr>`}</tbody></table></div>`;
}
function eventForm(e = {}) {
  return `<label>Tên sự kiện<input name="eventName" value="${esc(e.eventName || "")}"></label>
  <div class="cols"><label>Bắt đầu<input type="datetime-local" name="startTime" value="${dtl(e.startTime)}"></label>
  <label>Kết thúc<input type="datetime-local" name="endTime" value="${dtl(e.endTime)}"></label></div>
  <label>Địa điểm<input name="location" value="${esc(e.location || "")}"></label>
  <label>Sức chứa tối đa<input name="maxCapacity" type="number" min="1" value="${e.maxCapacity || ""}"></label>
  <label>Mô tả<textarea name="description" rows="3">${esc(e.description || "")}</textarea></label>`;
}

/* ---------- Chi tiết sự kiện ---------- */
async function viewEvent() {
  const e = S.ev = await api.get(`/api/admin/events/${S.ev.eventId}`);
  const tabs = [["report", "Tổng quan & báo cáo"], ["tickets", "Hạng vé"], ["people", "Người tham dự"], ["staff", "Nhân sự & phân công"]];
  app.innerHTML = `<p><a href="#" data-act="back">← Danh sách</a></p>
  <div class="row"><h1 class="grow">${esc(e.eventName)}</h1>
   <select id="statusSel" aria-label="Trạng thái">${Object.entries(STATUS_VN).map(([k, v]) => `<option value="${k}" ${k === e.status ? "selected" : ""}>${v}</option>`).join("")}</select>
   <button class="btn sm" data-act="editEvent">Sửa</button><button class="btn sm danger" data-act="delEvent">Xoá</button></div>
  <p class="mute small">🕒 ${fmtDT(e.startTime)} → ${fmtDT(e.endTime)} · 📍 ${esc(e.location || "—")} · Link đăng ký:
   <a href="/e/${esc(e.uniqueUrl)}" target="_blank">${location.origin}/e/${esc(e.uniqueUrl)}</a></p>
  <div class="tabs">${tabs.map(([k, v]) => `<button class="${S.tab === k ? "on" : ""}" data-act="tab" data-tab="${k}">${v}</button>`).join("")}</div><div id="pane"></div>`;
  $("#statusSel").onchange = async ev => { await api.patch(`/api/admin/events/${e.eventId}/status`, { status: ev.target.value }); toast("Đã cập nhật trạng thái"); };
  await ({ report: tabReport, tickets: tabTickets, people: tabPeople, staff: tabStaff })[S.tab]();
}

async function tabReport() {
  const r = await api.get(`/api/admin/events/${S.ev.eventId}/report`);
  $("#pane").innerHTML = `<div class="cols"><div class="stat">Đã đăng ký<b>${r.registered}/${r.capacity}</b><span class="small mute">${r.fillRate}% sức chứa</span></div>
  <div class="stat">Đã check-in<b>${r.checkedIn}</b><span class="small mute">${r.attendanceRate}% số đăng ký</span></div>
  <div class="stat">Chưa đến<b>${r.notCheckedIn}</b></div><div class="stat">Doanh thu đăng ký<b>${money(r.revenue)}</b></div></div>
  <div class="row" style="margin:14px 0"><button class="btn" data-act="export" data-fmt="xlsx">⬇ Excel</button><button class="btn" data-act="export" data-fmt="csv">⬇ CSV</button></div>
  <div class="cols"><div class="card"><h2>Theo loại vé</h2><div class="chart"><canvas id="c1"></canvas></div></div>
  <div class="card"><h2>Check-in theo giờ</h2><div class="chart"><canvas id="c2"></canvas></div></div>
  <div class="card"><h2>Đăng ký theo ngày</h2><div class="chart"><canvas id="c3"></canvas></div></div></div>
  <div class="card" style="margin-top:12px"><h2>Nhân viên check-in</h2>${r.byStaff.map(s => `${esc(s.name)}: <b>${s.count}</b>`).join(" · ") || "<span class='mute'>Chưa có</span>"}</div>`;
  const mk = (id, type, labels, sets) => S.charts.push(new Chart($(id), { type, data: { labels, datasets: sets }, options: { maintainAspectRatio: false, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } } }));
  mk("#c1", "bar", r.byTicketType.map(t => t.name), [{ label: "Đã bán", data: r.byTicketType.map(t => t.sold), backgroundColor: "#3b82f6" },
    { label: "Đã check-in", data: r.byTicketType.map(t => t.checkedIn), backgroundColor: "#16a34a" }]);
  mk("#c2", "bar", r.checkinByHour.map(x => x.label), [{ label: "Lượt check-in", data: r.checkinByHour.map(x => x.count), backgroundColor: "#16a34a" }]);
  mk("#c3", "line", r.registrationsByDay.map(x => x.label), [{ label: "Đăng ký", data: r.registrationsByDay.map(x => x.count), borderColor: "#3b82f6" }]);
}

async function tabTickets() {
  const e = S.ev = await api.get(`/api/admin/events/${S.ev.eventId}`);
  $("#pane").innerHTML = `<div class="row"><h2 class="grow">Hạng vé</h2><button class="btn primary" data-act="newCat">+ Thêm hạng vé</button></div>
  <div class="card tablewrap"><table><thead><tr><th>Tên</th><th>Giá</th><th>Số lượng</th><th>Đã bán</th><th></th></tr></thead><tbody>
  ${e.ticketCategories.map(c => `<tr><td>${esc(c.typeName)}</td><td>${money(c.price)}</td><td>${c.quantityLimit}</td><td>${c.soldCount}</td>
  <td><button class="btn sm" data-act="editCat" data-id="${c.ticketTypeId}">Sửa</button> <button class="btn sm danger" data-act="delCat" data-id="${c.ticketTypeId}">Xoá</button></td></tr>`).join("") || `<tr><td colspan="5" class="mute">Chưa có hạng vé – khách chưa thể đăng ký.</td></tr>`}</tbody></table></div>`;
}
const catForm = c => `<label>Tên hạng vé (VIP, Standard…)<input name="typeName" value="${esc(c.typeName || "")}"></label>
  <label>Giá (VND, 0 = miễn phí)<input name="price" type="number" min="0" value="${c.price ?? 0}"></label>
  <label>Số lượng<input name="quantityLimit" type="number" min="1" value="${c.quantityLimit || ""}"></label>`;

async function tabPeople() {
  const f = S.filters, e = S.ev;
  const q = new URLSearchParams({ page: S.page, pageSize: 20, ...(f.q ? { q: f.q } : {}), ...(f.status ? { status: f.status } : {}), ...(f.type ? { ticketTypeId: f.type } : {}) });
  const r = await api.get(`/api/admin/events/${e.eventId}/attendees?${q}`);
  const pages = Math.max(1, Math.ceil(r.total / r.pageSize));
  $("#pane").innerHTML = `<form class="row" id="filter"><input class="grow" name="q" placeholder="Tìm tên / email / SĐT / mã đăng ký" value="${esc(f.q || "")}">
  <select name="status"><option value="">Mọi trạng thái</option><option value="CHECKED_IN" ${f.status === "CHECKED_IN" ? "selected" : ""}>Đã check-in</option><option value="NOT_CHECKED_IN" ${f.status === "NOT_CHECKED_IN" ? "selected" : ""}>Chưa check-in</option></select>
  <select name="type"><option value="">Mọi hạng vé</option>${e.ticketCategories.map(c => `<option value="${c.ticketTypeId}" ${f.type === c.ticketTypeId ? "selected" : ""}>${esc(c.typeName)}</option>`).join("")}</select>
  <button class="btn">Lọc</button></form>
  <div class="card tablewrap" style="margin-top:10px"><table><thead><tr><th>Mã</th><th>Họ tên</th><th>Liên hệ</th><th>Vé</th><th>Check-in</th><th>Email vé</th></tr></thead><tbody>
  ${r.items.map(a => `<tr><td class="small">${esc(a.registrationId)}</td><td>${esc(a.fullName)}</td><td class="small">${esc(a.email)}<br>${esc(a.phoneNumber || "")}</td><td>${esc(a.ticketType)}</td>
  <td>${a.checkInStatus === "CHECKED_IN" ? `<span class="tag ok">${fmtDT(a.checkedInAt)}</span><br><span class="small mute">${esc(a.checkInMethod)} · ${esc(a.checkedInBy || "")}${a.checkInNote ? " · " + esc(a.checkInNote) : ""}</span>` : `<span class="tag">Chưa</span>`}</td>
  <td><span class="tag ${a.emailStatus === "SENT" ? "ok" : a.emailStatus === "FAILED" ? "bad" : "warn"}">${a.emailStatus}</span> <button class="btn sm" data-act="resend" data-id="${a.ticketId}">Gửi lại</button></td></tr>`).join("") || `<tr><td colspan="6" class="mute">Không có dữ liệu</td></tr>`}</tbody></table></div>
  <div class="row" style="margin-top:10px;justify-content:center"><button class="btn sm" data-act="page" data-d="-1" ${S.page <= 1 ? "disabled" : ""}>‹</button><span class="small">Trang ${r.page}/${pages} · ${r.total} người</span><button class="btn sm" data-act="page" data-d="1" ${S.page >= pages ? "disabled" : ""}>›</button></div>`;
  $("#filter").onsubmit = ev => { ev.preventDefault(); S.filters = Object.fromEntries(new FormData(ev.target)); S.page = 1; tabPeople(); };
}

async function tabStaff() {
  const e = S.ev;
  const [rows, staff] = await Promise.all([api.get(`/api/admin/events/${e.eventId}/assignments`), api.get("/api/admin/staff")]);
  S.staff = staff;
  $("#pane").innerHTML = `<div class="row"><h2 class="grow">Nhân sự được phân công</h2><button class="btn primary" data-act="newAssign">+ Phân công nhân viên</button></div>
  <p class="small mute">Nhân viên chỉ check-in được tại sự kiện này trong đúng ca đã gán. Tài khoản nhân viên tạo ở mục “Nhân viên”.</p>
  <div class="card tablewrap"><table><thead><tr><th>Nhân viên</th><th>Khu vực</th><th>Ca trực</th><th></th></tr></thead><tbody>
  ${rows.map(a => `<tr><td>${esc(a.fullName)}${a.staffStatus === "INACTIVE" ? ` <span class="tag bad">Vô hiệu</span>` : ""}<br><span class="small mute">${esc(a.email)} · ${esc(a.staffId)}</span></td><td>${esc(a.workArea)}</td>
  <td>${a.shiftStartTime || a.shiftEndTime ? `${fmtDT(a.shiftStartTime)} → ${fmtDT(a.shiftEndTime)}` : "Cả sự kiện"}</td>
  <td><button class="btn sm" data-act="editAssign" data-id="${a.assignmentId}">Sửa</button> <button class="btn sm danger" data-act="delAssign" data-id="${a.assignmentId}">Gỡ</button></td></tr>`).join("") || `<tr><td colspan="4" class="mute">Chưa phân công ai.</td></tr>`}</tbody></table></div>`;
  S.assign = rows;
}
const shiftFields = a => `<label>Khu vực làm việc (Cổng A, Khu VIP…)<input name="workArea" value="${esc(a.workArea || "")}"></label>
  <div class="cols"><label>Bắt đầu ca (để trống = không giới hạn)<input type="datetime-local" name="shiftStartTime" value="${dtl(a.shiftStartTime)}"></label>
  <label>Kết thúc ca<input type="datetime-local" name="shiftEndTime" value="${dtl(a.shiftEndTime)}"></label></div>`;

/* ---------- Tài khoản nhân viên ---------- */
async function viewStaff() {
  const rows = await api.get("/api/admin/staff");
  app.innerHTML = `<div class="row"><h1 class="grow">Tài khoản nhân viên</h1><button class="btn primary" data-act="newStaff">+ Tạo tài khoản</button></div>
  <p class="small mute">Nhân viên không tự đăng ký. Bạn tạo tài khoản ở đây, sau đó phân công vào từng sự kiện.</p>
  <div class="card tablewrap"><table><thead><tr><th>Họ tên</th><th>Liên hệ</th><th>Mã</th><th>Phân công</th><th>Trạng thái</th><th></th></tr></thead><tbody>
  ${rows.map(s => `<tr><td>${esc(s.fullName)}</td><td class="small">${esc(s.email)}<br>${esc(s.phoneNumber || "")}</td><td class="small">${esc(s.userId)}</td><td>${s.assignmentCount} sự kiện</td>
  <td><span class="tag ${s.staffStatus === "ACTIVE" ? "ok" : "bad"}">${s.staffStatus === "ACTIVE" ? "Hoạt động" : "Vô hiệu"}</span></td>
  <td><button class="btn sm" data-act="toggleStaff" data-id="${s.userId}" data-to="${s.staffStatus === "ACTIVE" ? "INACTIVE" : "ACTIVE"}">${s.staffStatus === "ACTIVE" ? "Vô hiệu hoá" : "Kích hoạt"}</button></td></tr>`).join("") || `<tr><td colspan="6" class="mute">Chưa có nhân viên.</td></tr>`}</tbody></table></div>`;
}

/* ---------- hành động ---------- */
const reload = () => go(S.view);
delegate(document.body, {
  nav: el => go(el.dataset.view), dclose: closeDlg, back: () => go("events"),
  logout: async () => { try { await api.post("/api/auth/logout"); } catch { } api.store.clear(); boot(); },
  open: el => go("event", { eventId: el.dataset.id }),
  tab: el => { S.tab = el.dataset.tab; S.page = 1; reload(); },
  page: el => { S.page += Number(el.dataset.d); tabPeople(); },
  newEvent: () => openDialog("Tạo sự kiện", eventForm(), async b => { const e = await api.post("/api/admin/events", b); closeDlg(); toast("Đã tạo — hãy thêm hạng vé"); go("event", e); S.tab = "tickets"; reload(); }),
  editEvent: () => openDialog("Sửa sự kiện", eventForm(S.ev), async b => { await api.put(`/api/admin/events/${S.ev.eventId}`, b); closeDlg(); reload(); }),
  delEvent: async () => { if (!confirm("Xoá sự kiện này? (chỉ xoá được khi chưa có người đăng ký)")) return; await api.del(`/api/admin/events/${S.ev.eventId}`); go("events"); },
  newCat: () => openDialog("Thêm hạng vé", catForm({}), async b => { await api.post(`/api/admin/events/${S.ev.eventId}/categories`, b); closeDlg(); reload(); }),
  editCat: el => { const c = S.ev.ticketCategories.find(x => x.ticketTypeId === el.dataset.id);
    openDialog("Sửa hạng vé", catForm(c), async b => { await api.put(`/api/admin/events/${S.ev.eventId}/categories/${c.ticketTypeId}`, b); closeDlg(); reload(); }); },
  delCat: async el => { if (!confirm("Xoá hạng vé này?")) return; await api.del(`/api/admin/categories/${el.dataset.id}`); reload(); },
  export: el => api.download(`/api/admin/events/${S.ev.eventId}/export.${el.dataset.fmt}`, `${S.ev.uniqueUrl}.${el.dataset.fmt}`),
  resend: async el => { const r = await api.post(`/api/admin/tickets/${el.dataset.id}/resend-email`); toast(r.emailStatus === "SENT" ? "Đã gửi lại email" : "Gửi email thất bại – kiểm tra cấu hình SMTP"); tabPeople(); },
  newStaff: () => openDialog("Tạo tài khoản nhân viên", `<label>Họ tên<input name="fullName"></label><label>Email đăng nhập<input name="email" type="email"></label>
    <label>Số điện thoại<input name="phoneNumber" placeholder="0901234567"></label><label>Mật khẩu (để trống = hệ thống tự sinh)<input name="password" type="text" autocomplete="off"></label>`,
    async b => { if (!b.password) delete b.password; const s = await api.post("/api/admin/staff", b);
      openDialog("Đã tạo tài khoản", `<p>Gửi thông tin này cho nhân viên (mật khẩu chỉ hiển thị một lần):</p><div class="card"><b>${esc(s.email)}</b><br>Mật khẩu: <b>${esc(s.temporaryPassword || "(do bạn đặt)")}</b></div>`, null); viewStaff(); }),
  toggleStaff: async el => { await api.patch(`/api/admin/staff/${el.dataset.id}`, { staffStatus: el.dataset.to }); viewStaff(); },
  newAssign: () => { const used = new Set(S.assign.map(a => a.staffId)); const opts = S.staff.filter(s => s.staffStatus === "ACTIVE" && !used.has(s.userId));
    if (!opts.length) return toast("Không còn nhân viên khả dụng. Hãy tạo tài khoản ở mục “Nhân viên”.");
    openDialog("Phân công nhân viên", `<label>Nhân viên<select name="staffId">${opts.map(s => `<option value="${s.userId}">${esc(s.fullName)} — ${esc(s.email)}</option>`).join("")}</select></label>${shiftFields({})}`,
      async b => { await api.post(`/api/admin/events/${S.ev.eventId}/assignments`, b); closeDlg(); tabStaff(); }); },
  editAssign: el => { const a = S.assign.find(x => x.assignmentId === el.dataset.id);
    openDialog(`Sửa phân công – ${a.fullName}`, shiftFields(a), async b => { await api.patch(`/api/admin/assignments/${a.assignmentId}`, b); closeDlg(); tabStaff(); }); },
  delAssign: async el => { if (!confirm("Gỡ phân công này?")) return; await api.del(`/api/admin/assignments/${el.dataset.id}`); tabStaff(); },
});
boot();
