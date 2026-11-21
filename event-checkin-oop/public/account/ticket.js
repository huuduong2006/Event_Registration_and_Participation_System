if (!att.store.token) location.href = "/portal/login.html?next=" + encodeURIComponent(location.pathname + location.search);
renderTopbar();
(async () => {
  try {
    const t = await att.get(`/api/attendee/registrations/${encodeURIComponent(new URLSearchParams(location.search).get("id") || "")}/ticket`);
    $("#box").innerHTML = `<h1>${esc(t.event.eventName)}</h1><p class="mute">🕒 ${fmtDT(t.event.startTime)} · 📍 ${esc(t.event.location || "—")}</p>
      <div class="qrbox"><img src="${t.qrImage}" alt="Mã QR"></div>
      <p style="text-align:center"><span class="tag info">${esc(t.ticketType)}</span> <span class="tag ${t.checkInStatus === "CHECKED_IN" ? "ok" : "warn"}">${t.checkInStatus === "CHECKED_IN" ? "Đã check-in " + fmtDT(t.checkedInAt) : "Chưa check-in"}</span></p>
      <p class="small mute" style="text-align:center">Mã đăng ký: ${esc(t.registrationId)} (đọc mã này nếu bạn quên vé và cần check-in thủ công)</p>`;
  } catch (e) { $("#box").innerHTML = `<div class="alert err">${esc(e.message)}</div>`; }
})();
