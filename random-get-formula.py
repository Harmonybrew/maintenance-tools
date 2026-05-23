#!/usr/bin/env python3
import os
import sys
import json
import random
import requests

UPSTREAM_API = "https://formulae.brew.sh/api/formula.jws.json"
DOWNSTREAM_API = "https://harmonybrew.atomgit.com/api/formula.jws.json"
CACHE_FILE = "formula.jws.json"


def fetch_upstream_payload():
    """获取上游数据（优先读取本地缓存）"""
    # 1. 尝试从本地缓存读取
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                payload_str = data.get("payload", "[]")
                return json.loads(payload_str)
        except Exception as e:
            print(f"[!] Read cache error: {e}", file=sys.stderr)

    # 2. 缓存不存在或解析失败，则发起下载
    try:
        resp = requests.get(UPSTREAM_API, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # 写入本地缓存
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        payload_str = data.get("payload", "[]")
        return json.loads(payload_str)
    except Exception as e:
        print(f"[!] Fetch upstream error: {e}", file=sys.stderr)
        return []


def fetch_downstream_payload():
    """获取下游数据（每次强制实时下载）"""
    try:
        resp = requests.get(DOWNSTREAM_API, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        payload_str = data.get("payload", "[]")
        return json.loads(payload_str)
    except Exception as e:
        print(f"[!] Fetch downstream error: {e}", file=sys.stderr)
        return []


def get_linux_deps(formula_info):
    """提取第一层级联依赖（保持原脚本逻辑：基础依赖 + Linux变体 + MacOS移入项）"""
    deps = set()
    deps.update(formula_info.get("dependencies", []))
    deps.update(formula_info.get("build_dependencies", []))

    variations = formula_info.get("variations", {})
    linux_var = variations.get("arm64_linux") or variations.get("x86_64_linux")
    if linux_var:
        linux_var = linux_var or {}
        deps.update(linux_var.get("dependencies", []))
        deps.update(linux_var.get("build_dependencies", []))

    for item in formula_info.get("uses_from_macos", []):
        deps.add(item if isinstance(item, str) else list(item.keys())[0])

    return {d for d in deps if d}


def main():
    # 1. 加载数据
    upstream_data = fetch_upstream_payload()
    downstream_data = fetch_downstream_payload()

    if not upstream_data or not downstream_data:
        print("[!] Error: Empty data from upstream or downstream.", file=sys.stderr)
        sys.exit(1)

    # 2. 构建下游集合与上游别名映射
    downstream_names = {item["name"] for item in downstream_data}

    alias_map = {}
    upstream_map = {}
    for item in upstream_data:
        real_name = item["name"]
        upstream_map[real_name] = item
        for alias in item.get("aliases", []):
            alias_map[alias] = real_name

    def resolve_name(name):
        return alias_map.get(name, name)

    # 3. 筛选候选集
    candidates = []
    for real_name, info in upstream_map.items():
        # 条件 1：上游存在（已在循环中），下游不存在
        if real_name in downstream_names:
            continue

        # 获取第一层所有依赖，并解析为真实名称
        raw_deps = get_linux_deps(info)
        real_deps = {resolve_name(d) for d in raw_deps}

        # 条件 2：第一层级联依赖必须全部在下游中存在
        # 如果某依赖既不在下游，又不在上游（死依赖），也会被过滤掉
        if real_deps.issubset(downstream_names):
            candidates.append(real_name)

    # 4. 随机挑选并输出到 stdout
    if candidates:
        selected = random.choice(candidates)
        print(selected)
    else:
        print("[!] No available formula matches the criteria.", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
