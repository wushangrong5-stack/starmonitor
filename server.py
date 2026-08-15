import os,re,hashlib,sqlite3
from datetime import datetime,timezone
from urllib.parse import quote_plus
from flask import Flask,jsonify,send_from_directory
import feedparser

app=Flask(__name__,static_folder=".",static_url_path="")
DB="news.db"
KEYWORDS=["Taylor Swift","Sabrina Carpenter"]
SOURCES={
"Billboard":"billboard.com","People":"people.com","Variety":"variety.com",
"Rolling Stone":"rollingstone.com","Entertainment Weekly":"ew.com",
"NME":"nme.com","The Hollywood Reporter":"hollywoodreporter.com"
}
def init():
 c=sqlite3.connect(DB);c.execute("""create table if not exists news(
 id text primary key,artist text,title text,source text,summary text,
 link text,time text,hot integer default 0)""");c.commit();c.close()
def clean(x):
 return re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",x or "")).strip()
def fetch():
 out=[];seen=set()
 for artist in KEYWORDS:
  searches=[("Google News",None)]+list(SOURCES.items())
  for source,domain in searches:
   q=f'"{artist}"'+(f" site:{domain}" if domain else "")
   url="https://news.google.com/rss/search?q="+quote_plus(q)+"&hl=en-US&gl=US&ceid=US:en"
   feed=feedparser.parse(url)
   for e in feed.entries[:12]:
    title=clean(e.get("title"));link=e.get("link","")
    if not title or not link: continue
    uid=hashlib.sha256((title+"|"+link).encode()).hexdigest()
    if uid in seen: continue
    seen.add(uid)
    out.append({"id":uid,"artist":artist,"title":title,"source":source,
                "summary":clean(e.get("summary"))[:500],"link":link,
                "time":e.get("published",""),"hot":0})
 return out
def save(items):
 c=sqlite3.connect(DB)
 for x in items:
  c.execute("insert or ignore into news values(?,?,?,?,?,?,?,?)",
   (x["id"],x["artist"],x["title"],x["source"],x["summary"],x["link"],x["time"],x["hot"]))
 c.commit();c.close()
@app.route("/")
def home(): return send_from_directory(".","index.html")
@app.route("/api/news")
def api():
 save(fetch())
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row
 rows=c.execute("select * from news order by rowid desc limit 80").fetchall();c.close()
 return jsonify([dict(x) for x in rows])
init()
if __name__=="__main__":
 app.run(host="0.0.0.0",port=int(os.getenv("PORT","8080")))
