renderTopbar();
const ref = decodeURIComponent(location.pathname.split("/").filter(Boolean).pop());
const me = att.store.token ? att.store.user : null;
(async () => {
  let e;
  try { e = await att.get(`/api/public/events/${encodeURIComponent(ref)}`); }
  catch (err) { $("#ev").innerHTML = `<div class="alert err">${esc(err.message)}</div>`; return; }
  document.title = e.eventName;
  $("#ev").innerHTML = `<div class="card"><h1>${esc(e.eventName)}</h1>
    <p class="mute">🕒 ${fmtDT(e.startTime)} → ${fmtDT(e.endTime)}<br>📍 ${esc(e.location || "Sẽ thông báo")}</p>
    ${e.description ? `<p>${esc(e.description)}</p>` : ""}
    <p><span class="tag info">${STATUS_VN[e.status]}</span> <span class="tag">Còn ${e.availableCapacity}/${e.maxCapacity} chỗ</span></p></div>`;
  if (e.closedReason) { $("#ev").insertAdjacentHTML("beforeend", `<div class="alert err">${esc(e.closedReason)}</div>`); return; }
  $("#formcard").hidden = false;
  $("select[name=ticketTypeId]").innerHTML = e.ticketCategories.map(c =>
    `<option value="${c.ticketTypeId}" ${c.remaining <= 0 ? "disabled" : ""}>${esc(c.typeName)} — ${money(c.price)} ${c.remaining <= 0 ? "(hết vé)" : `(còn ${c.remaining})`}</option>`).join("");
  if (me && me.role === "ATTENDEE") { $("#guestFields").hidden = true; $$("#guestFields input").forEach(i => i.required = false);
    $("#formcard h2").textContent = `Đăng ký với tài khoản ${me.fullName}`; }
  $("#form").addEventListener("submit", async ev => {
    ev.preventDefault(); const msg = $("#msg"); hide(msg); const btn = $("#submit"); btn.disabled = true;
    const f = Object.fromEntries(new FormData(ev.target));
    try {
      const url = me && me.role === "ATTENDEE" ? `/api/attendee/events/${e.eventId}/register` : `/api/public/events/${e.eventId}/register`;
      const t = await (me && me.role === "ATTENDEE" ? att.post(url, { ticketTypeId: f.ticketTypeId }) : att.post(url, f, true));
      $("#formcard").hidden = true; $("#done").hidden = false; $("#qr").src = t.qrImage;
      $("#doneInfo").textContent = `${t.event.eventName} · ${t.ticketType} · Mã đăng ký ${t.registrationId}`;
      if (me) $("#myTickets").hidden = false;
      scrollTo(0, 0);
    } catch (err) {
      showErr(msg, err); btn.disabled = false;
      if (err.code === "LOGIN_REQUIRED") msg.innerHTML += ` <a href="/portal/login.html?next=${encodeURIComponent(location.pathname)}">Đăng nhập</a>`;
    }
  });
})();
