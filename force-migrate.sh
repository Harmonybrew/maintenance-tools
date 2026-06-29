#!/bin/bash
set -e

# ================= 参数校验 =================
if [ $# -lt 1 ]; then
    echo "[ERROR] 用法: $0 <formula-name>"
    echo ""
    echo "示例:"
    echo "  $0 hello"
    echo "  $0 python@3.12"
    echo ""
    echo "说明: 强制迁移指定的 Formula 到 Harmonybrew/homebrew-core。"
    echo "      该操作会跳过“是否已迁移”和“PR 是否已存在”等校验，"
    echo "      直接重新构建并提交 PR。"
    exit 1
fi

FORMULA="$1"
echo "[INFO] 目标 Formula: [ ${FORMULA} ]"

# ================= 克隆迁移工具 =================
rm -rf formula-migration-tool
git clone https://atomgit.com/Harmonybrew/formula-migration-tool.git

# ================= 执行 Docker 强制迁移 =================
echo "[INFO] 正在启动 Docker 容器进行强制迁移..."
echo "      使用 --force 模式，跳过已有迁移/PR 检查..."

docker run \
  --rm \
  -v "$PWD"/formula-migration-tool:/workdir \
  -w /workdir \
  -e ATOMGIT_TOKEN="$ATOMGIT_TOKEN" \
  -e ATOMGIT_USER="$ATOMGIT_USER" \
  -e ATOMGIT_EMAIL="$ATOMGIT_EMAIL" \
  swr.cn-north-4.myhuaweicloud.com/harmonybrew/ci-runner:latest \
  python3 auto-migrate.py --force "$FORMULA"

echo "[INFO] Formula [ ${FORMULA} ] 强制迁移流程结束。"
