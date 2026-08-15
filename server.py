import json
import os
import hashlib
import re
import sqlite3
import urllib.parse
import feedparser

# 监控的明星关键字
KEYWORDS = ["Taylor Swift", "Sabrina Carpenter"]

# 新闻来源配置
SOURCES = {
    "Google News": None,
    "Billboard": "billboard.com",
    "Rolling Stone": "rollingstone.com"
}

DB = "news.db"

def clean(text):
    if not text:
        return ""
    # 清理 HTML 标签
    return re.sub(r'<[^>]+>', '', text).strip()

def init():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id TEXT PRIMARY KEY,
            artist TEXT,
            title TEXT,
            source TEXT,
            summary TEXT,
            link TEXT,
            published TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def fetch():
    out = []
    seen = set()
    
    for artist in KEYWORDS:
        searches = [("Google News", None)] + list(SOURCES.items())
        for source, domain in searches:
            q = f'"{artist}"' + (f" site:{domain}" if domain else "")
            encoded_q = urllib.parse.quote(q)
            url = f"https://news.google.com/rss/search?q={encoded_q}&hl=en-US&gl=US&ceid=US:en"
            
            try:
                feed = feedparser.parse(url)
                for e in feed.entries[:12]:
                    title = clean(e.get("title", ""))
                    link = e.get("link", "")
                    if not title or not link:
                        continue
                    
                    uid = hashlib.sha256((title + "|" + link).encode("utf-8")).hexdigest()
                    if uid in seen:
                        continue
                    seen.add(uid)
                    
                    out.append({
                        "id": uid,
                        "artist": artist,
                        "title": title,
                        "summary": clean(e.get("summary", "")),
                        "time": e.get("published", ""),
                        "source": source,
                        "url": link
                    })
            except Exception as err:
                print(f"Fetch error for {artist} via {source}: {err}")
                
    return out

def save(items):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    for x in items:
        c.execute(
            "INSERT OR IGNORE INTO news (id, artist, title, source, summary, link, published) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (x["id"], x["artist"], x["title"], x["source"], x["summary"], x["url"], x["time"])
        )
    conn.commit()
    conn.close()

def export_json():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    rows = c.execute("SELECT id, artist, title, source, summary, link as url, published as time FROM news ORDER BY created_at DESC LIMIT 50").fetchall()
    data = [dict(x) for x in rows]
    conn.close()
    
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("成功导出了", len(data), "条新闻到 news.json")

if __name__ == "__main__":
    print("开始初始化数据库...")
    init()
    print("开始抓取最新新闻...")
    items = fetch()
    print(f"共抓取到 {len(items)} 条新闻数据")
    save(items)
    print("保存到数据库完成，导出 JSON 数据文件...")
    export_json()
    print("全套流程完毕，脚本正常退出！")
