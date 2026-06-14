#!/bin/bash
# build-deb.sh — 构建 Ubuntu .deb 安装包
#
# 前置条件：
#   1. 已完成 PyInstaller onedir 构建（dist/KindergartenManager/）
#   2. 已安装 dpkg-deb（通常随 Ubuntu 预装）
#
# 使用方式：
#   bash packaging/debian/build-deb.sh 3.0.0-beta.1
#
# 产物：dist/kindergarten-manager_3.0.0-beta.1_amd64.deb

set -e

VERSION="${1:-3.0.0-beta.1}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$REPO_ROOT/dist/deb-build"
PKG_NAME="kindergarten-manager"
OUTPUT_DEB="$REPO_ROOT/dist/${PKG_NAME}_${VERSION}_amd64.deb"

echo "==> 清理旧构建目录..."
rm -rf "$BUILD_DIR"

# ── 1. 创建目录结构 ──────────────────────────────────────────────────────────
echo "==> 创建包目录结构..."
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/opt/kindergarten-manager"
mkdir -p "$BUILD_DIR/lib/systemd/system"
mkdir -p "$BUILD_DIR/var/lib/kindergarten-manager/exports"
mkdir -p "$BUILD_DIR/etc/kindergarten-manager"

# ── 2. 拷贝 PyInstaller onedir 产物 ─────────────────────────────────────────
ONEDIR="$REPO_ROOT/dist/KindergartenManager"
if [ ! -d "$ONEDIR" ]; then
    echo "ERROR: PyInstaller 产物不存在：$ONEDIR"
    echo "       请先运行 pyinstaller kindergartenManager.spec"
    exit 1
fi
echo "==> 拷贝二进制到 /opt/kindergarten-manager/..."
cp -r "$ONEDIR/." "$BUILD_DIR/opt/kindergarten-manager/"
chmod +x "$BUILD_DIR/opt/kindergarten-manager/KindergartenManager"

# ── 3. 拷贝 DEBIAN 控制文件 ─────────────────────────────────────────────────
echo "==> 拷贝控制文件..."
cp "$SCRIPT_DIR/DEBIAN/control"  "$BUILD_DIR/DEBIAN/control"
cp "$SCRIPT_DIR/DEBIAN/postinst" "$BUILD_DIR/DEBIAN/postinst"
cp "$SCRIPT_DIR/DEBIAN/prerm"    "$BUILD_DIR/DEBIAN/prerm"
cp "$SCRIPT_DIR/DEBIAN/postrm"   "$BUILD_DIR/DEBIAN/postrm"

# 更新版本号
sed -i "s/^Version:.*/Version: $VERSION/" "$BUILD_DIR/DEBIAN/control"

# 赋予脚本执行权限（dpkg 要求）
chmod 755 "$BUILD_DIR/DEBIAN/postinst"
chmod 755 "$BUILD_DIR/DEBIAN/prerm"
chmod 755 "$BUILD_DIR/DEBIAN/postrm"

# ── 4. 拷贝 systemd 服务文件 ─────────────────────────────────────────────────
echo "==> 拷贝 systemd 服务文件..."
cp "$SCRIPT_DIR/lib/systemd/system/kindergarten-manager.service" \
   "$BUILD_DIR/lib/systemd/system/kindergarten-manager.service"

# ── 5. 计算安装体积（dpkg-deb 需要 Installed-Size 字段） ─────────────────────
INSTALLED_SIZE_KB=$(du -sk "$BUILD_DIR/opt" | awk '{print $1}')
sed -i "/^Installed-Size:/d" "$BUILD_DIR/DEBIAN/control"
echo "Installed-Size: $INSTALLED_SIZE_KB" >> "$BUILD_DIR/DEBIAN/control"

# ── 6. 构建 .deb ─────────────────────────────────────────────────────────────
echo "==> 构建 .deb 包..."
dpkg-deb --build --root-owner-group "$BUILD_DIR" "$OUTPUT_DEB"

echo ""
echo "=========================================="
echo "  .deb 包构建完成"
echo "  输出：$OUTPUT_DEB"
echo ""
echo "  安装命令："
echo "    sudo dpkg -i $OUTPUT_DEB"
echo ""
echo "  卸载命令（保留配置）："
echo "    sudo dpkg -r $PKG_NAME"
echo "  彻底清除命令："
echo "    sudo dpkg -P $PKG_NAME"
echo "=========================================="
