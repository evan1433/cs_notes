#!/usr/bin/env bash
# ============================================================
# CS Notes - 一键部署脚本
# 功能：本地构建 Quartz 静态站点 + rsync 推送到服务器
# 用法：
#   ./deploy.sh                          # 使用默认配置
#   ./deploy.sh --skip-build             # 跳过构建，只同步
#   ./deploy.sh --subpath                # 子路径部署模式
#   ./deploy.sh --dry-run                # 预览同步内容，不实际传输
#   DEPLOY_HOST=1.2.3.4 ./deploy.sh      # 指定服务器地址
# ============================================================

set -euo pipefail

# -------------------- 颜色输出 --------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# -------------------- 配置（可通过环境变量覆盖） --------------------
# 服务器地址（必填）
DEPLOY_HOST="${DEPLOY_HOST:-}"
# SSH 端口
DEPLOY_PORT="${DEPLOY_PORT:-22}"
# SSH 用户名
DEPLOY_USER="${DEPLOY_USER:-root}"
# 服务器上的部署目录
# 根路径部署：/var/www/cs-notes
# 子路径部署：/var/www/cs-notes（内容会放在其下的 cs_notes/ 子目录）
DEPLOY_DIR="${DEPLOY_DIR:-/var/www/cs-notes}"
# 部署模式：root 或 subpath
DEPLOY_MODE="${DEPLOY_MODE:-root}"
# 本地构建输出目录
BUILD_DIR="${BUILD_DIR:-public}"
# rsync 排除文件
RSYNC_EXCLUDE="${RSYNC_EXCLUDE:-.rsync-exclude}"

# -------------------- 解析参数 --------------------
SKIP_BUILD=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --subpath)
            DEPLOY_MODE="subpath"
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-build    Skip build, only sync files"
            echo "  --subpath       Deploy to /cs_notes/ subpath"
            echo "  --dry-run       Preview sync without transferring"
            echo "  --help          Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  DEPLOY_HOST     Server hostname or IP (required)"
            echo "  DEPLOY_PORT     SSH port (default: 22)"
            echo "  DEPLOY_USER     SSH user (default: root)"
            echo "  DEPLOY_DIR      Remote deploy directory (default: /var/www/cs-notes)"
            echo "  DEPLOY_MODE     root or subpath (default: root)"
            exit 0
            ;;
        *)
            error "Unknown option: $1. Use --help for usage."
            ;;
    esac
done

# -------------------- 前置检查 --------------------
info "Running pre-flight checks..."

# 检查服务器地址
if [[ -z "$DEPLOY_HOST" ]]; then
    error "DEPLOY_HOST is not set. Usage: DEPLOY_HOST=your-server ./deploy.sh"
fi

# 检查 Node.js 版本
if ! command -v node &>/dev/null; then
    error "Node.js is not installed. Quartz 4.0 requires Node.js 22+."
fi

NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
if [[ "$NODE_VERSION" -lt 22 ]]; then
    error "Node.js $NODE_VERSION is too old. Quartz 4.0 requires Node.js 22+."
fi

# 检查包管理器
if [[ "$SKIP_BUILD" != true ]] && ! command -v pnpm &>/dev/null; then
    error "pnpm is not installed. Run: corepack enable"
fi

# 检查 rsync
if ! command -v rsync &>/dev/null; then
    error "rsync is not installed. Install it with: brew install rsync (macOS) or apt install rsync (Linux)"
fi

# 检查 SSH 连接
info "Testing SSH connection to ${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PORT}..."
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes -p "$DEPLOY_PORT" "${DEPLOY_USER}@${DEPLOY_HOST}" "echo ok" &>/dev/null; then
    error "Cannot connect to ${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PORT}. Check SSH key or network."
fi
ok "SSH connection successful"

# 检查项目根目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ ! -f "$PROJECT_DIR/package.json" ]]; then
    error "package.json not found in $PROJECT_DIR. Are you in the right project?"
fi

ok "Pre-flight checks passed"

# -------------------- 构建站点 --------------------
if [[ "$SKIP_BUILD" == true ]]; then
    warn "Skipping build (--skip-build)"
else
    info "Building Quartz site..."
    cd "$PROJECT_DIR"

    # 安装依赖（如需要）
    if [[ ! -d "node_modules" ]]; then
        info "Installing dependencies..."
        pnpm install --frozen-lockfile
    fi

    # 执行构建
    pnpm build

    # 验证构建输出
    if [[ ! -d "$BUILD_DIR" ]]; then
        error "Build directory '$BUILD_DIR' not found. Build may have failed."
    fi

    # 检查关键文件
    if [[ ! -f "$BUILD_DIR/index.html" ]]; then
        error "index.html not found in $BUILD_DIR. Build may have failed."
    fi

    BUILD_SIZE=$(du -sh "$BUILD_DIR" | cut -f1)
    FILE_COUNT=$(find "$BUILD_DIR" -type f | wc -l | tr -d ' ')
    ok "Build completed: $FILE_COUNT files, $BUILD_SIZE total"
fi

# -------------------- 创建 rsync 排除文件 --------------------
cat > "$PROJECT_DIR/$RSYNC_EXCLUDE" <<'EOF'
.git/
.obsidian/
.node_modules/
.DS_Store
Thumbs.db
*.map
EOF

# -------------------- 确定远程目标路径 --------------------
if [[ "$DEPLOY_MODE" == "subpath" ]]; then
    # 子路径模式：public/ 内容放到 /var/www/cs-notes/cs_notes/
    REMOTE_PATH="${DEPLOY_DIR}/cs_notes/"
    info "Deploy mode: SUBPATH → https://${DEPLOY_HOST}/cs_notes/"
else
    # 根路径模式：public/ 内容直接放到 /var/www/cs-notes/
    REMOTE_PATH="${DEPLOY_DIR}/"
    info "Deploy mode: ROOT → https://${DEPLOY_HOST}/"
fi

# -------------------- 同步文件 --------------------
RSYNC_CMD="rsync -avz --delete \
    --exclude-from='$PROJECT_DIR/$RSYNC_EXCLUDE' \
    -e 'ssh -p $DEPLOY_PORT' \
    '$PROJECT_DIR/$BUILD_DIR/' \
    '${DEPLOY_USER}@${DEPLOY_HOST}:${REMOTE_PATH}'"

if [[ "$DRY_RUN" == true ]]; then
    RSYNC_CMD="rsync -avzn --delete \
        --exclude-from='$PROJECT_DIR/$RSYNC_EXCLUDE' \
        -e 'ssh -p $DEPLOY_PORT' \
        '$PROJECT_DIR/$BUILD_DIR/' \
        '${DEPLOY_USER}@${DEPLOY_HOST}:${REMOTE_PATH}'"
    warn "DRY RUN - no files will be transferred"
fi

info "Syncing files to ${DEPLOY_USER}@${DEPLOY_HOST}:${REMOTE_PATH}..."

# 使用 eval 展开变量
eval "$RSYNC_CMD"

if [[ "$DRY_RUN" == true ]]; then
    warn "Dry run completed. Remove --dry-run to actually deploy."
    exit 0
fi

ok "Files synced successfully"

# -------------------- 上传 robots.txt --------------------
ROBOTS_SRC="$SCRIPT_DIR/robots.txt"
if [[ -f "$ROBOTS_SRC" ]]; then
    if [[ "$DEPLOY_MODE" == "subpath" ]]; then
        ROBOTS_REMOTE="${DEPLOY_DIR}/cs_notes/robots.txt"
    else
        ROBOTS_REMOTE="${DEPLOY_DIR}/robots.txt"
    fi

    if [[ "$DRY_RUN" == false ]]; then
        info "Uploading robots.txt to ${ROBOTS_REMOTE}..."
        scp -P "$DEPLOY_PORT" "$ROBOTS_SRC" "${DEPLOY_USER}@${DEPLOY_HOST}:${ROBOTS_REMOTE}"
        ok "robots.txt uploaded"
    fi
else
    warn "robots.txt not found at $ROBOTS_SRC, skipping"
fi

# -------------------- 服务器端后处理 --------------------
info "Running post-deploy tasks on server..."

ssh -p "$DEPLOY_PORT" "${DEPLOY_USER}@${DEPLOY_HOST}" bash -s <<REMOTE_SCRIPT
set -e

DEPLOY_DIR="${DEPLOY_DIR}"

# 确保目录权限正确
chown -R www-data:www-data "\$DEPLOY_DIR" 2>/dev/null || chown -R nginx:nginx "\$DEPLOY_DIR" 2>/dev/null || true
chmod -R 755 "\$DEPLOY_DIR"

# 测试 Nginx 配置
if command -v nginx &>/dev/null; then
    echo "Testing Nginx configuration..."
    nginx -t 2>&1

    # 重载 Nginx（如果配置有变更）
    echo "Reloading Nginx..."
    systemctl reload nginx 2>/dev/null || service nginx reload 2>/dev/null || true
fi

echo "Post-deploy tasks completed"
REMOTE_SCRIPT

ok "Post-deploy tasks completed"

# -------------------- 完成 --------------------
echo ""
echo "========================================="
ok "Deployment completed!"
echo "========================================="
echo ""
if [[ "$DEPLOY_MODE" == "subpath" ]]; then
    echo "  Site URL: https://${DEPLOY_HOST}/cs_notes/"
else
    echo "  Site URL: https://${DEPLOY_HOST}/"
fi
echo ""
echo "  Next steps:"
echo "  1. Verify the site is accessible at the URL above"
echo "  2. If SSL is not configured yet, run: ./setup-ssl.sh"
echo "  3. Check Nginx config: deploy/nginx.conf or deploy/nginx-subpath.conf"
echo ""
