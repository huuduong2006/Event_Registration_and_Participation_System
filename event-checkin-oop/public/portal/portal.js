renderTopbar();
(async () => {
  const box = $("#list");
  try {
    const events = await att.get("/api/public/events");
    box.innerHTML = events.length ? events.map(e => `
      <article class="card"><div class="row"><h2 class="grow">${esc(e.eventName)}</h2>
        <span class="tag ${e.closedReason ? "bad" : "ok"}">${e.closedReason ? "Đã đóng" : "Đang mở"}</span></div>
        <p class="mute small">🕒 ${fmtDT(e.startTime)} &nbsp; 📍 ${esc(e.location || "Sẽ thông báo")}</p>
        <p class="small">${e.ticketCategories.map(c => `${esc(c.typeName)}: <b>${money(c.price)}</b>`).join(" · ") || "Chưa có loại vé"}
        &nbsp;·&nbsp; còn <b>${e.availableCapacity}</b> chỗ</p>
        <a class="btn primary" href="/e/${esc(e.uniqueUrl)}">Xem chi tiết &amp; đăng ký</a></article>`).join("")
      : `<div class="card mute">Hiện chưa có sự kiện nào đang mở.</div>`;
  } catch (e) { box.innerHTML = `<div class="alert err">${esc(e.message)}</div>`; }
})();
