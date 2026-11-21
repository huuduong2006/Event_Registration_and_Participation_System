/* Tiện ích dùng chung cho mọi trang (không dùng inline script do CSP). */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const money = n => (Number(n) === 0 ? "Miễn phí" : new Intl.NumberFormat("vi-VN").format(n) + " ₫");
const fmtDT = s => { if (!s) return "—"; const d = String(s).replace("T", " "); const [dt, tm] = d.split(" "); const [y, m, day] = dt.split("-"); return `${(tm || "").slice(0, 5)} ${day}/${m}/${y}`.trim(); };
const STATUS_VN = { UPCOMING: "Sắp diễn ra", ONGOING: "Đang diễn ra", COMPLETED: "Đã kết thúc" };
const SHIFT_VN = { ON_SHIFT: "Đang trong ca", NOT_STARTED: "Chưa đến ca", ENDED: "Đã hết ca" };

function toast(msg) {
  const t = document.createElement("div"); t.className = "toast"; t.textContent = msg; document.body.appendChild(t);
  setTimeout(() => t.remove(), 3200);
}

/** Tạo client gọi API gắn token từ localStorage[key]. */
function makeApi(key, onUnauthorized) {
  const store = {
    get token() { try { return localStorage.getItem(key); } catch { return null; } },
    set(t, u) { try { localStorage.setItem(key, t); localStorage.setItem(key + "_user", JSON.stringify(u)); } catch { } },
    get user() { try { return JSON.parse(localStorage.getItem(key + "_user")); } catch { return null; } },
    clear() { try { localStorage.removeItem(key); localStorage.removeItem(key + "_user"); } catch { } },
  };
  async function raw(method, url, body, anon) {
    const h = {}; if (body !== undefined) h["Content-Type"] = "application/json";
    if (!anon && store.token) h.Authorization = "Bearer " + store.token;
    let r;
    try { r = await fetch(url, { method, headers: h, body: body === undefined ? undefined : JSON.stringify(body) }); }
    catch { throw Object.assign(new Error("Không kết nối được máy chủ"), { code: "NETWORK" }); }
    return r;
  }
  async function req(method, url, body, anon) {
    const r = await raw(method, url, body, anon);
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      if (r.status === 401 && !anon && onUnauthorized) onUnauthorized();
      throw Object.assign(new Error(data.error || "Có lỗi xảy ra"), { code: data.code, status: r.status });
    }
    return data;
  }
  async function download(url, filename) {
    const r = await raw("GET", url);
    if (!r.ok) throw new Error("Không tải được tệp");
    const a = document.createElement("a"); a.href = URL.createObjectURL(await r.blob()); a.download = filename; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }
  return { store, get: u => req("GET", u), post: (u, b, anon) => req("POST", u, b ?? {}, anon), put: (u, b) => req("PUT", u, b),
    patch: (u, b) => req("PATCH", u, b), del: u => req("DELETE", u), download };
}

/** Gắn xử lý sự kiện uỷ quyền: <button data-act="tên"> → handlers.tên(el, event) */
function delegate(root, handlers) {
  root.addEventListener("click", e => {
    const el = e.target.closest("[data-act]"); if (!el || !root.contains(el)) return;
    const fn = handlers[el.dataset.act]; if (fn) { e.preventDefault(); Promise.resolve(fn(el, e)).catch(err => toast(err.message)); }
  });
}
const showErr = (el, e) => { el.className = "alert err"; el.textContent = e.message || String(e); el.hidden = false; };
const hide = el => { el.hidden = true; };
