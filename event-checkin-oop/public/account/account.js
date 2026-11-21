if (!att.store.token) location.href = "/portal/login.html?next=/account/";
renderTopbar();
(async () => {
  try {
    const [me, rows] = await Promise.all([att.get("/api/auth/me"), att.get("/api/attendee/registrations")]);
    if (me.role !== "ATTENDEE") { att.store.clear(); location.href = "/portal/login.html"; return; }
    const f = $("#profile"); f.fullName.value = me.fullName; f.phoneNumber.value = me.phoneNumber || ""; $("#email").value = me.email;
    $("#list").innerHTML = rows.length ? rows.map(r => `<article class="card"><div class="row"><h2 class="grow">${esc(r.eventName)}</h2>
      <span class="tag ${r.checkInStatus === "CHECKED_IN" ? "ok" : "info"}">${r.checkInStatus === "CHECKED_IN" ? "Đã check-in" : "Chưa check-in"}</span></div>
      <p class="mute small">${esc(r.ticketType)} · ${money(r.price)} · 🕒 ${fmtDT(r.startTime)} · 📍 ${esc(r.location || "—")}<br>Đăng ký lúc ${fmtDT(r.registrationDate)} · Mã ${esc(r.registrationId)}</p>
      <a class="btn primary" href="/account/ticket.html?id=${encodeURIComponent(r.registrationId)}">Xem mã QR</a></article>`).join("")
      : `<div class="card mute">Bạn chưa đăng ký sự kiện nào. <a href="/">Xem sự kiện</a></div>`;
  } catch (e) { $("#list").innerHTML = `<div class="alert err">${esc(e.message)}</div>`; }
})();
$("#profile").addEventListener("submit", async ev => {
  ev.preventDefault(); const m = $("#msg"); hide(m);
  const b = Object.fromEntries(new FormData(ev.target)); if (!b.newPassword) { delete b.newPassword; delete b.currentPassword; }
  try { const u = await att.patch("/api/auth/me", b); att.store.set(att.store.token, u); renderTopbar();
    m.className = "alert ok"; m.textContent = "Đã lưu"; m.hidden = false; } catch (e) { showErr(m, e); }
});
