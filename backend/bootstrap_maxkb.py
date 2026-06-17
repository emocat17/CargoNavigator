#!/usr/bin/env python3
"""
MaxKB 自动配置引导脚本

用法:
  1. 确保 MaxKB 容器已启动: docker compose --profile kb up -d
  2. 编辑 .env 填写 MAXKB_USERNAME 和 MAXKB_PASSWORD
  3. 运行: python bootstrap_maxkb.py          （本地）
            docker exec cargo-backend python bootstrap_maxkb.py  （Docker）

脚本会自动:
  - 登录 MaxKB 获取 session token
  - 发现已有的 Application 和 Dataset（或新建）
  - 生成 API Key
  - 将配置写入 .env
"""
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

# ── 读取环境变量 ──
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
MAXKB_PORT = int(os.getenv("MAXKB_PORT", "18090"))
MAXKB_BASE_URL = os.getenv("MAXKB_BASE_URL", f"http://localhost:{MAXKB_PORT}")
MAXKB_USERNAME = os.getenv("MAXKB_USERNAME", "admin")
MAXKB_PASSWORD = os.getenv("MAXKB_PASSWORD", "")

# Docker 内部网络优先
if not os.getenv("MAXKB_BASE_URL"):
    # 检测是否在 Docker 内运行
    import socket
    try:
        socket.gethostbyname("cargo-maxkb")
        MAXKB_BASE_URL = "http://cargo-maxkb:8080"
    except socket.gaierror:
        pass

API_PREFIX = f"{MAXKB_BASE_URL.rstrip('/')}/admin/api"


def _post(path: str, data: dict) -> dict:
    """POST JSON 请求"""
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{API_PREFIX}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=10)
    return json.loads(resp.read().decode())


def _get(path: str, token: str) -> dict:
    """GET JSON 请求（带认证）"""
    req = urllib.request.Request(
        f"{API_PREFIX}{path}",
        headers={"Authorization": token},
    )
    resp = urllib.request.urlopen(req, timeout=10)
    return json.loads(resp.read().decode())


def login() -> str:
    """登录 MaxKB，返回 session token"""
    if not MAXKB_PASSWORD:
        print("[ERROR] MAXKB_PASSWORD 未设置，请在 .env 中填写")
        sys.exit(1)

    print(f"[*] 登录 MaxKB: {MAXKB_BASE_URL} (用户: {MAXKB_USERNAME})")
    try:
        result = _post("/user/login", {
            "username": MAXKB_USERNAME,
            "password": MAXKB_PASSWORD,
        })
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"[ERROR] 登录失败: {e.code} {body[:300]}")
        sys.exit(1)

    if result.get("code") != 200:
        print(f"[ERROR] 登录失败: {result.get('message', '未知错误')}")
        sys.exit(1)

    token = result["data"]["token"]
    print(f"[✓] 登录成功, token: {token[:40]}...")
    return f"Bearer {token}"


def get_workspace_id(token: str) -> str:
    """获取默认 workspace ID"""
    # MaxKB 默认 workspace 由后端确定，尝试 profile 接口
    try:
        result = _get("/user/profile", token)
        return result.get("data", {}).get("workspace_id", "default")
    except Exception:
        pass
    # Fallback: 尝试从 application 列表拿
    try:
        result = _get("/user/profile", token)
        ws_id = result.get("data", {}).get("active_workspace_id", "")
        if ws_id:
            return ws_id
    except Exception:
        pass
    return "default"


def list_applications(token: str, workspace_id: str) -> list:
    """列出所有应用"""
    try:
        result = _get(
            f"/workspace/{workspace_id}/application/1/100", token
        )
        apps = result.get("data", {}).get("records", [])
        print(f"[*] 发现 {len(apps)} 个应用:")
        for a in apps:
            print(f"    - {a.get('name')} (id={a.get('id')})")
        return apps
    except Exception as e:
        print(f"[WARN] 获取应用列表失败: {e}")
        return []


def list_datasets(token: str, workspace_id: str) -> list:
    """列出所有知识库"""
    try:
        result = _get(
            f"/workspace/{workspace_id}/knowledge/1/100", token
        )
        datasets = result.get("data", {}).get("records", [])
        print(f"[*] 发现 {len(datasets)} 个知识库:")
        for d in datasets:
            print(f"    - {d.get('name')} (id={d.get('id')})")
        return datasets
    except Exception as e:
        print(f"[WARN] 获取知识库列表失败: {e}")
        return []


def get_or_create_api_key(token: str, workspace_id: str, app_id: str) -> str:
    """获取或创建应用的 API Key"""
    try:
        result = _get(
            f"/workspace/{workspace_id}/application/{app_id}/application_key/1/100",
            token,
        )
        keys = result.get("data", {}).get("records", [])
        # 返回第一个 active 的 key
        for k in keys:
            if k.get("is_active", True):
                print(f"[✓] 已有 API Key: {k.get('secret_key', '***')[:30]}...")
                return k.get("secret_key", "")
        # 没有 active key，创建新的
        if not keys:
            print("[*] 创建新的 API Key...")
            create_result = _post(
                f"/workspace/{workspace_id}/application/{app_id}/application_key",
                {"name": "auto-generated"},
            )
            # 注意: 创建后需要从列表重新获取（API 可能不返回 secret）
    except Exception as e:
        print(f"[WARN] API Key 操作失败: {e}")
    return ""


def update_env_file(updates: dict):
    """更新 .env 文件"""
    if not ENV_FILE.exists():
        print(f"[WARN] .env 文件不存在: {ENV_FILE}")
        return

    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    updated_keys = set()

    new_lines = []
    for line in lines:
        stripped = line.strip()
        # 跳过注释和空行
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        # 检查是否是需要更新的 key
        if "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}")
                updated_keys.add(key)
                continue
        new_lines.append(line)

    # 追加未更新的 key
    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"# Auto-detected by bootstrap_maxkb.py")
            new_lines.append(f"{key}={value}")

    ENV_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"[✓] .env 已更新: {', '.join(updates.keys())}")


def main():
    print("=" * 50)
    print("  MaxKB 自动配置引导")
    print("=" * 50)

    # 1. 登录
    token = login()

    # 2. 获取 workspace
    workspace_id = get_workspace_id(token)
    print(f"[*] Workspace: {workspace_id}")

    # 3. 发现应用
    apps = list_applications(token, workspace_id)
    app_id = ""
    app_name = ""
    if apps:
        # 优先选包含 "cargo" 或 "大件" 的应用
        for a in apps:
            name = a.get("name", "")
            if "cargo" in name.lower() or "大件" in name:
                app_id = a["id"]
                app_name = name
                break
        # 否则用第一个
        if not app_id and apps:
            app_id = apps[0]["id"]
            app_name = apps[0].get("name", "")

    # 4. 发现知识库
    datasets = list_datasets(token, workspace_id)

    # 5. 获取 API Key
    api_key = ""
    if app_id:
        api_key = get_or_create_api_key(token, workspace_id, app_id)

    # 6. 生成配置
    print("\n" + "=" * 50)
    print("  自动检测结果")
    print("=" * 50)

    updates = {}
    updates["MAXKB_SESSION_TOKEN"] = token

    if app_id:
        chat_url = f"{MAXKB_BASE_URL.rstrip('/')}/chat/api/{app_id}"
        updates["MAXKB_CHAT_API_URL"] = chat_url
        print(f"  Application: {app_name} ({app_id})")
        print(f"  Chat API:    {chat_url}")

    if datasets:
        ds = datasets[0]
        updates["MAXKB_DATASET_ID"] = ds["id"]
        print(f"  Dataset:     {ds.get('name')} ({ds['id']})")

    if api_key:
        updates["MAXKB_API_KEY"] = api_key
        print(f"  API Key:     {api_key[:30]}...")

    # 7. 写入 .env
    if updates:
        print(f"\n[*] 以下配置将写入 .env:")
        for k, v in updates.items():
            display = v[:50] + "..." if len(str(v)) > 50 else v
            print(f"    {k}={display}")

        try:
            update_env_file(updates)
            print(f"\n[✓] 完成! 重启后端使配置生效:")
            print(f"    docker restart cargo-backend")
        except Exception as e:
            print(f"\n[!] 写入失败: {e}")
            print(f"请手动将以上配置复制到 .env 文件")
    else:
        print("[!] 未能检测到任何配置，请检查 MaxKB 是否已初始化")


if __name__ == "__main__":
    main()
