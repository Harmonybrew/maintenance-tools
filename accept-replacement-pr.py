#!/usr/bin/env python3
import os
import sys
import requests

# ==================== 配置区域 ====================
OWNER = "Harmonybrew"  # 根据实际仓库所有者修改
REPO = "homebrew-core"  # 根据实际仓库名修改
TARGET_STRING = "replacement for"
ADD_LABEL = "request-ci"
MAX_PROCESS_LIMIT = 50  # 每次最多处理的 PR 数量上限
# ==================================================

# 检查环境变量
ATOMGIT_TOKEN = os.getenv("ATOMGIT_TOKEN")
if not ATOMGIT_TOKEN:
    sys.exit("Error: Environment variable ATOMGIT_TOKEN is missing.")


def get_open_prs(page, per_page=100):
    """分页获取所有开启状态的 PR"""
    url = f"https://api.atomgit.com/api/v5/repos/{OWNER}/{REPO}/pulls"
    params = {"access_token": ATOMGIT_TOKEN, "state": "open", "per_page": per_page, "page": page}
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()  # 状态码不是 2xx 时抛出异常
        return response.json()  # 直接返回解析后的 JSON 数据
    except requests.exceptions.RequestException as e:
        print(f"[!] Request failed: {e}")
        return []


def add_label_to_pr(number, labels):
    """给 PR 添加标签"""
    url = f"https://api.atomgit.com/api/v5/repos/{OWNER}/{REPO}/pulls/{number}/labels"
    params = {"access_token": ATOMGIT_TOKEN}
    try:
        response = requests.post(url, params=params, json=labels, timeout=15)
        response.raise_for_status()
        print(f"[SUCCESS] Successfully added label to PR #{number}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to add label to PR #{number}: {e}")
        return False


def main():
    print(f"[*] Starting scan for {OWNER}/{REPO} (Using requests)...")
    print(f"[*] Target condition: Title contains '{TARGET_STRING}' and has NO labels.")
    print(f"[*] Max process limit set to: {MAX_PROCESS_LIMIT}")
    print("--------------------------------------------------")

    page = 1
    per_page = 100
    processed_count = 0

    while True:
        print(f"[*] Fetching page {page} of open PRs...")
        prs = get_open_prs(page, per_page)

        if not prs:
            print("[*] No more open PRs found or error occurred.")
            break

        for pr in prs:
            title = pr.get("title", "")
            labels = pr.get("labels", [])
            pr_number = pr.get("number")

            # 条件判断：标题包含目标字符串，且 label 数量为 0
            if TARGET_STRING in title and len(labels) == 0:
                print(f"[+ ] Found matching PR #{pr_number}: '{title}'")

                # 执行打标签操作
                success = add_label_to_pr(pr_number, [ADD_LABEL])
                if success:
                    processed_count += 1
                    print(f"    -> Progress: {processed_count}/{MAX_PROCESS_LIMIT}")

                # 检查是否达到上限
                if processed_count >= MAX_PROCESS_LIMIT:
                    print(f"\n[!] Reached the maximum process limit of {MAX_PROCESS_LIMIT}. Stopping.")
                    return

        # 如果当前页返回的 PR 数量少于单页最大值，说明已经是最后一页了
        if len(prs) < per_page:
            break
        else:
            page += 1

    print(f"\n[OK] Scan finished. Total PRs processed this run: {processed_count}")


if __name__ == "__main__":
    main()
