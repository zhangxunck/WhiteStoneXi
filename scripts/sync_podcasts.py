import os, sys, json, re, urllib.request, time
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(ROOT, "podcasts_data.json")

CATEGORIES = {
    "投资 · 商业": ["起朱楼宴宾客", "面基", "知行小酒馆", "不可思议Bookish", "請聽，哈佛管理學！"],
    "认知 · 科技": ["The a16z Show", "管理派", "Infinite Loops"],
    "人文 · 阅读": ["史蒂夫说", "907编辑部", "电影巨辩"],
    "思想 · 历史": ["不明白播客", "剧谈社"]
}

def get_token():
    """复用 pocketcast_starred_sync 的完整认证链（过期检查 → cookie 提取 → .env 账密登录）
    避免读到过期 JWT（PC token 寿命 ~1h，凌晨 cron 场景必过期）"""
    sys.path.insert(0, os.path.expanduser("~/.hermes/scripts"))
    import pocketcast_starred_sync as pss
    try:
        tok, _how = pss.get_token()
        return tok
    except SystemExit:
        # pss.get_token 失败时 sys.exit（输出诊断）→ 包一层让调用方拿到明确错误
        raise RuntimeError("Pocket Casts token 获取失败（过期且 .env 无凭证）")

def fetch_starred():
    tok = get_token()
    req = urllib.request.Request(
        "https://api.pocketcasts.com/user/starred",
        data=json.dumps({"v": 1}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok}"}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    eps = [e for e in data.get("episodes", []) if not e.get("isDeleted")]
    return eps

def get_category(pod_title):
    for cat, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw.lower() in pod_title.lower():
                return cat
    return "特选 · 杂谈"

def format_duration(sec):
    if not sec: return ""
    m = sec // 60
    h = m // 60
    rem_m = m % 60
    return f"{h}小时{rem_m}分" if h > 0 else f"{m}分钟"

def build_data(eps):
    """加星单集 → 数据 JSON（页面骨架由 build_site.py 统一生成，本脚本只负责数据）。"""
    # 分类归档
    categorized = {}
    for e in eps:
        pod = e.get("podcastTitle", "未知播客").strip()
        cat = get_category(pod)
        categorized.setdefault(cat, []).append(e)

    # 排序
    for cat in categorized:
        categorized[cat].sort(key=lambda x: x.get("published", ""), reverse=True)

    cats = []
    for cat in ["投资 · 商业", "认知 · 科技", "人文 · 阅读", "思想 · 历史", "特选 · 杂谈"]:
        items = []
        for item in categorized.get(cat, []):
            title = item.get("title", "").strip()
            # 清理标题冗余（Vol.1 / EP2 / E1. 等期数前缀）
            clean_title = re.sub(r'^(Vol\.\s*\d+|EP\.\s*\d+|E\d+[\.、\s]|\#\d+[-\d]*\s*)', '', title, flags=re.I).strip()
            dur = format_duration(item.get("duration", 0))
            audio_url = item.get("url", "")
            actions = []
            if audio_url:
                actions.append({"href": audio_url, "label": "音频直链 ↗"})
            items.append({
                "name": item.get("podcastTitle", "").strip(),
                "date": (item.get("published") or "")[:10],
                "duration": dur,
                "title": clean_title if clean_title else title,
                "actions": actions,
            })
        if items:
            cats.append({"category": cat, "items": items})

    data = {
        "updated": datetime.now().astimezone().isoformat(timespec="seconds"),
        "total": len(eps),
        "categories": cats,
    }
    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ podcasts_data.json 更新：{len(eps)} 单集 / {len(cats)} 分类")

def rebuild_page():
    """页面骨架走 build_site.py（共享导航/汉堡/繁简按钮/共享页脚/同版 CSS），
    本脚本不再自产 HTML，杜绝导航与全站漂移。"""
    import subprocess
    r = subprocess.run([os.path.join(ROOT, ".venv/bin/python"), "build_site.py"],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr)
        raise RuntimeError("build_site.py 构建失败")
    print(r.stdout.strip().splitlines()[-1])

if __name__ == "__main__":
    eps = fetch_starred()
    build_data(eps)
    rebuild_page()
