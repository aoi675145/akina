#!/usr/bin/env bash
# ensure-deb.sh —— apt 源不可达时，从本仓库 release 的 deb 资产兜底安装（不碰 apt）。
#
# 背景（2026-11-11 icehost run 43037814085）：runner 上 archive.ubuntu.com 解析失败，
# ensure-apt.sh 两轮换源都救不回来，xdotool 装不上 → 自检 exit 1，后续代理/脚本全 skipped。
# github.com 在这台 runner 上是通的（checkout / raw / releases 都能下），所以把需要的 deb
# 传到 releases/download/debs/，用 dpkg -x 解包到 /usr，完全绕开 apt 的源与 DNS。
#
# 用法：
#   bash ensure-deb.sh --need "xdotool" --pkgs "libxdo3 xdotool"
#
#   --need   装完后用 command -v 校验的二进制名（多个用空格）
#   --pkgs   要解包的 deb 名（= releases/download/debs/<name>.deb）
set -uo pipefail

BASE="${DEB_BASE:-https://github.com/aoi675145/akina/releases/download/debs}"
NEED=""; PKGS=""

while [ $# -gt 0 ]; do
  case "$1" in
    --need) NEED="${2:-}"; shift 2 ;;
    --pkgs) PKGS="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
    *) echo "::error::ensure-deb.sh 未知参数: $1"; exit 2 ;;
  esac
done

[ -n "$(echo ${PKGS:-})" ] || { echo "::error::ensure-deb.sh 需要 --pkgs"; exit 2; }

unpack() {  # $1=deb 路径  $2=目标根（必须先存在，dpkg-deb -x 不会自己建父目录）
  mkdir -p "$2"
  if command -v dpkg-deb >/dev/null 2>&1; then
    dpkg-deb -x "$1" "$2"
  else
    dpkg -x "$1" "$2"
  fi
}

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fail=0
for p in $PKGS; do
  if ! curl -fL --retry 3 --retry-delay 2 --max-time 120 -o "$TMP/$p.deb" "$BASE/$p.deb"; then
    echo "::warning::deb 下载失败: $p（$BASE/$p.deb）"
    fail=1; continue
  fi
  unpack "$TMP/$p.deb" "$TMP/x/$p" || { echo "::warning::deb 解包失败: $p"; fail=1; continue; }
  sudo cp -a "$TMP/x/$p/usr/." /usr/ || fail=1
done

sudo ldconfig 2>/dev/null || true

miss=""
for b in $NEED; do
  command -v "$b" >/dev/null 2>&1 || miss="$miss $b"
done
if [ -n "$miss" ]; then
  echo "::error::release deb 兜底后仍缺:${miss}（检查 debs release 资产）"
  exit 1
fi
if [ "$fail" -ne 0 ]; then
  echo "::warning::部分 deb 没装上，但自检已通过: $PKGS"
else
  echo "[INFO] release deb 兜底完成: ${PKGS}（未使用 apt）"
fi
