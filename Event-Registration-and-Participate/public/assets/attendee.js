/* Phiên + thanh điều hướng của Cổng Attendee. */
const att = makeApi("att_token", () => { att.store.clear(); });

function renderTopbar() {
  const u = att.store.token ? att.store.user : null;
  $("#topbar").innerHTML = `<a class="brand" href="/">🎟️ Sự kiện</a>` + (u
    ? `<a class="btn sm" href="/account/">Vé của tôi</a><span class="small mute">${esc(u.fullName)}</span><button class="btn sm" id="logout">Đăng xuất</button>`
    : `<a class="btn sm" href="/portal/login.html?next=${encodeURIComponent(location.pathname + location.search)}">Đăng nhập / Đăng ký</a>`)
    + `<a class="small mute" href="/staff/">Dành cho BTC</a>`;
  const lo = $("#logout");
  if (lo) lo.onclick = async () => { try { await att.post("/api/auth/logout"); } catch { } att.store.clear(); location.href = "/"; };
}
