#!/usr/bin/env python3
"""BlackHost 续期前置窗口预检：窗口没开 + 进程真在跑 → skip=1，整轮空跳过。

为什么要有这一步：续期是「重置成 续期时刻 + 8h」，窗口只有到期前 2h。靠哪吒掉线告警
触发会先掉线一段时间（2026-11-12 实测 17:13 到期、18:14 才跑，机器躺了一小时）。
所以 workflow 改成每小时摸一次，没到窗口的二十几次靠这里 5 秒跳过：不装依赖、不起浏览器。

判活只认内层 stats.status == running 且 uptime > 0：外层 serverState 在解除暂停那刻
就是 ready，会把「没开机」当成「已在运行」。

只用标准库；任何异常都 fail-open（skip=0），让主流程自己去判断。
"""
import json
import os
import sys
import urllib.request

BASE = "https://dash.blackhost.pl"
PAT_FILE = os.path.join("private-repo", "scripts", "blackhost", "apikey.txt")


def out(key, val):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{key}={val}\n")


def mask_name(name):
    text = str(name or "").strip()
    return (text[:2] + "***") if text else "***"


def load_pat():
    with open(PAT_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                return line
    raise RuntimeError("apikey.txt 为空")


def get(path, pat):
    req = urllib.request.Request(
        BASE + path,
        headers={
            "Authorization": f"Bearer {pat}",
            "Accept": "application/json",
            # 面板在 Cloudflare 后面，python-urllib 的默认 UA 会被 403
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) blackhost-gate/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode())


def main():
    try:
        pat = load_pat()
        free = get("/api/v1/servers/game/free/status", pat).get("freeServer") or {}
        servers = get("/api/v1/servers", pat).get("pterodactyl_servers") or []
        if not servers:
            print("gate: 账号下没有服务器，交回主流程")
            out("skip", 0)
            return 0
        key = servers[0].get("unique_id") or ""
        stats = get(f"/api/v1/servers/game/{key}/stats", pat) if key else {}
        inner = stats.get("stats") or {}
        cur = str(inner.get("status") or "").strip().lower()
        try:
            uptime = int(inner.get("uptime") or 0)
        except (TypeError, ValueError):
            uptime = 0
        running = cur == "running" and uptime > 0
        can_renew = bool(free.get("canRenew"))
        expired = bool(free.get("isExpired"))
        print(
            f"gate: {mask_name(servers[0].get('name'))}｜可续期 {can_renew}｜已过期 {expired}｜"
            f"进程 {cur or 'unknown'} uptime {uptime}s｜到期 {free.get('activeUntil')}"
        )
        skip = (not can_renew) and (not expired) and running
        out("skip", 1 if skip else 0)
        print("gate: " + ("窗口没开且进程在跑 → 跳过整轮" if skip else "要续期或要开机 → 走全流程"))
        return 0
    except Exception as e:  # fail-open：预检本身出问题不能拦住续期
        print(f"gate: 预检失败（{str(e)[:120]}），按需走全流程")
        out("skip", 0)
        return 0


if __name__ == "__main__":
    sys.exit(main())
