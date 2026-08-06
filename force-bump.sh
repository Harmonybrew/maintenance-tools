#!/bin/bash
set -e

# ================= 参数校验 =================
if [ $# -lt 2 ]; then
    echo "[ERROR] 用法: $0 <formula-name> <branch>"
    echo ""
    echo "示例:"
    echo "  $0 hello bump-hello"
    echo "  $0 python@3.12 bump-python"
    echo ""
    echo "说明: 强制 bump 指定的 Formula 到 Harmonybrew/homebrew-core 的指定分支。"
    echo "      会使用最新的上游 Formula 重新构建，并把修改后的代码用 push -f"
    echo "      强制推送到目标分支，但不会生成 PR。"
    exit 1
fi

FORMULA="$1"
BRANCH="$2"
echo "[INFO] 目标 Formula: [ ${FORMULA} ]"
echo "[INFO] 目标分支: [ ${BRANCH} ]"

# ================= 克隆迁移工具 =================
rm -rf formula-migration-tool
git clone https://atomgit.com/Harmonybrew/formula-migration-tool.git

# ================= 执行 Docker 强制 bump =================
echo "[INFO] 正在启动 Docker 容器进行强制 bump..."
echo "      使用 --bump 模式，跳过已有迁移/PR 检查，"
echo "      使用最新上游 Formula 重新构建，并将改动 push -f 到指定分支..."

docker run \
  --rm \
  -v "$PWD"/formula-migration-tool:/workdir \
  -w /workdir \
  -e ATOMGIT_TOKEN="$ATOMGIT_TOKEN" \
  -e ATOMGIT_USER="$ATOMGIT_USER" \
  -e ATOMGIT_EMAIL="$ATOMGIT_EMAIL" \
  swr.cn-north-4.myhuaweicloud.com/harmonybrew/ci-runner:latest \
  python3 auto-migrate.py --bump "$FORMULA" --branch "$BRANCH"

echo "[INFO] Formula [ ${FORMULA} ] 强制 bump 流程结束。"
