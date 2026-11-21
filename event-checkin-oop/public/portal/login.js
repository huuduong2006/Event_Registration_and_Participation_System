renderTopbar();
const next = new URLSearchParams(location.search).get("next");
const dest = next && next.startsWith("/") && !next.startsWith("//") ? next : "/account/";
$$("[data-tab]").forEach(b => b.onclick = () => { $$("[data-tab]").forEach(x => x.classList.toggle("on", x === b));
  $("#login").hidden = b.dataset.tab !== "login"; $("#register").hidden = b.dataset.tab !== "register"; hide($("#msg")); });
for (const [id, url, extra] of [["login", "/api/auth/login", { portal: "attendee" }], ["register", "/api/auth/register", {}]]) {
  $("#" + id).addEventListener("submit", async ev => {
    ev.preventDefault(); hide($("#msg"));
    try { const r = await att.post(url, { ...Object.fromEntries(new FormData(ev.target)), ...extra }, true);
      att.store.set(r.token, r.user); location.href = dest; }
    catch (e) { showErr($("#msg"), e); }
  });
}
