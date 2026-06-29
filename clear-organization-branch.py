#!/usr/bin/env python3

import os
import sys
import time
import requests

# ================= 动态读取环境变量 =================
ACCESS_TOKEN = os.environ.get("ATOMGIT_TOKEN")

# 安全校验：确保环境变量已正确加载
if not ACCESS_TOKEN:
    print("[-] 错误：未检测到必要的系统环境变量！")
    print("    请确保已正确设置 `ATOMGIT_TOKEN`。")
    sys.exit(1)

# ================= 仓库配置区域 =================
# 组织仓库（需要管理员权限）
ORG_OWNER = "Harmonybrew"
ORG_REPO = "homebrew-core"

# 绝对不能删除的默认主分支
PROTECTED_BASE_BRANCHES = {"main", "master", "develop"}

# 是否开启模拟运行 (True: 仅打印结果不执行删除, False: 真正发送 DELETE 请求)
DRY_RUN = False
# ================================================

# 通用 Header 配置
HEADERS = {"Accept": "application/json", "Authorization": f"Bearer {ACCESS_TOKEN}"}


def list_all_branches(owner, repo):
    """
    获取项目所有分支
    URL: https://api.atomgit.com/api/v5/repos/:owner/:repo/branches
    """
    url = f"https://api.atomgit.com/api/v5/repos/{owner}/{repo}/branches"
    branches = []
    page = 1
    per_page = 100

    while True:
        params = {"access_token": ACCESS_TOKEN, "page": page, "per_page": per_page}

        try:
            response = requests.get(url, headers=HEADERS, params=params)
            if response.status_code != 200:
                print(f"[-] 获取分支列表失败，状态码: {response.status_code}, 原因: {response.text}")
                break

            data = response.json()
            if not data or len(data) == 0:
                break

            for b in data:
                if isinstance(b, dict) and "name" in b:
                    branches.append(b["name"])

            if len(data) < per_page:
                break
            page += 1
            time.sleep(0.1)
        except Exception as e:
            print(f"[-] 请求分支列表发生异常: {e}")
            break

    return branches


def get_active_pr_branches(owner, repo):
    """
    获取组织仓库中当前所有 Open 状态的 PR 所使用的源分支，
    这些分支正在参与 PR 流程，不应被删除。
    不再关注 PR 提交者是谁，只要分支上有活跃 PR 就受保护。
    """
    url = f"https://api.atomgit.com/api/v5/repos/{owner}/{repo}/pulls"
    active_branches = set()
    page = 1
    per_page = 100

    while True:
        params = {"access_token": ACCESS_TOKEN, "state": "open", "page": page, "per_page": per_page}
        try:
            response = requests.get(url, headers=HEADERS, params=params)
            if response.status_code != 200:
                print(f"[-] 获取 PR 列表失败，状态码: {response.status_code}")
                break

            prs = response.json()
            if not prs or len(prs) == 0:
                break

            for pr in prs:
                # 获取源分支名称（兼容不同字段名）
                branch_name = pr.get("source_branch")
                if not branch_name:
                    branch_name = pr.get("head", {}).get("ref")

                # 只要分支上有活跃 PR，无论由谁创建，都加入保护名单
                if branch_name:
                    active_branches.add(branch_name)
                    print(
                        f"    [检测到活跃PR] PR #{pr.get('number')}: 分支 '{branch_name}' 正在使用中，已加入保护名单。"
                    )

            if len(prs) < per_page:
                break
            page += 1
            time.sleep(0.1)
        except Exception as e:
            print(f"[-] 请求 PR 列表发生异常: {e}")
            break

    return active_branches


def delete_single_branch(owner, repo, name):
    """
    删除分支
    URL: https://api.atomgit.com/api/v5/repos/:owner/:repo/branches/:name
    """
    url = f"https://api.atomgit.com/api/v5/repos/{owner}/{repo}/branches/{name}"
    params = {"access_token": ACCESS_TOKEN}
    response = requests.delete(url, headers=HEADERS, params=params)
    return response


def main():
    print("====== 欢迎使用 AtomGit 组织仓库分支清理工具 ======")
    print(f"[目标仓库] {ORG_OWNER}/{ORG_REPO}")
    if DRY_RUN:
        print("【安全提示】当前处于 [Dry-Run 模拟模式]，只会打印结果，不会执行任何删除！\n")
    else:
        print("【高危警告】当前处于 [实战模式]，符合条件的无效分支将被直接执行 DELETE！\n")

    # 1. 获取组织仓库中当前所有 Open PR 所使用的分支
    print(f"[1/3] 正在从组织仓库 {ORG_OWNER}/{ORG_REPO} 获取所有活跃 PR 列表...")
    pr_protected_branches = get_active_pr_branches(ORG_OWNER, ORG_REPO)
    print(f"-> 成功识别活跃 PR 的保护分支共 {len(pr_protected_branches)} 个: {list(pr_protected_branches)}")

    # 2. 获取组织仓库的全部分支
    print(f"\n[2/3] 正在从组织仓库 {ORG_OWNER}/{ORG_REPO} 分页下载所有分支...")
    all_org_branches = list_all_branches(ORG_OWNER, ORG_REPO)
    print(f"-> 组织仓库当前共有 {len(all_org_branches)} 个分支。")

    # 3. 过滤并执行清理
    print("\n[3/3] 开始分析分支状态并执行策略:")
    deleted_count = 0
    skipped_count = 0

    for branch in all_org_branches:
        # 拦截一：保护默认主分支
        if branch in PROTECTED_BASE_BRANCHES:
            print(f"  [-] [跳过] 主分支不受影响: {branch}")
            skipped_count += 1
            continue

        # 拦截二：保护有活跃 PR 的分支
        if branch in pr_protected_branches:
            print(f"  [★] [保护] 该分支有正在进行的 PR: {branch}")
            skipped_count += 1
            continue

        # 满足删除条件
        if DRY_RUN:
            print(f"  [模拟删除] 发现无效分支: {branch}")
            deleted_count += 1
        else:
            res = delete_single_branch(ORG_OWNER, ORG_REPO, branch)
            if res.status_code in [200, 204]:
                print(f"  [成功删除] 分支: {branch}")
                deleted_count += 1
            else:
                print(f"  [删除失败] 分支: {branch}，响应代码: {res.status_code}，原因: {res.text}")
            time.sleep(0.3)  # 限制删除频率，防止触发服务商的频控

    print("\n====== 执行报告 ======")
    if DRY_RUN:
        print(f"【模拟统计】评估完毕。预估将删除 {deleted_count} 个无效分支，完整保留 {skipped_count} 个关键分支。")
        print("请检查上方输出的“模拟删除”名单是否完全符合你的心理预期。")
        print("确认完全无误后，只需将脚本中的 `DRY_RUN = True` 修改为 `DRY_RUN = False` 即可真正释放清理。")
    else:
        print(f"【实战统计】清理完毕！本次实际成功删除了 {deleted_count} 个无效分支，安全保留 {skipped_count} 个分支。")


if __name__ == "__main__":
    main()
