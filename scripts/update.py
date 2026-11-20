#!/usr/bin/env python3
"""Actualización horaria de fuentes públicas para Doomsday Watch."""
import datetime as dt, json, re, unicodedata, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"site/data/feed.json"
NOW=dt.datetime.now(dt.timezone.utc);CUTOFF=NOW-dt.timedelta(hours=72)
CH={"UCvC4D8onUfXzvjTOM-dBfEA":"Marvel Entertainment","UC8LEXZO4hjzVk6wO3G9pJyQ":"Marvel Latinoamérica"}
NS={"a":"http://www.w3.org/2005/Atom","yt":"http://www.youtube.com/xml/schemas/2015"}
def get(url):
 r=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (DoomsdayWatch RSS)"})
 with urllib.request.urlopen(r,timeout=20) as x:return x.read(2000000)
def norm(x):return unicodedata.normalize("NFKD",str(x)).encode("ascii","ignore").decode().lower()
def match(x):return "doomsday" in norm(x) and ("avengers" in norm(x) or "vengadores" in norm(x))
def date(x):
 try:
  y=dt.datetime.fromisoformat(str(x).replace("Z","+00:00")) if "T" in str(x) else parsedate_to_datetime(x)
  return y if y.tzinfo else y.replace(tzinfo=dt.timezone.utc)
 except Exception:return None
def recent(x):
 t=date(x);return bool(t and CUTOFF<=t<=NOW+dt.timedelta(minutes=10))
def videos(cid,source):
 root=ET.fromstring(get("https://www.youtube.com/feeds/videos.xml?channel_id="+cid));out=[]
 for e in root.findall("a:entry",NS):
  title=e.findtext("a:title","",NS);when=e.findtext("a:published","",NS);vid=e.findtext("yt:videoId","",NS)
  if not match(title) or not recent(when) or not re.fullmatch("[A-Za-z0-9_-]{11}",vid):continue
  kind="AVANCE OFICIAL" if any(t in norm(title) for t in ("trailer","avance")) else "VIDEO OFICIAL"
  out.append(dict(id="yt-"+vid,title=title,description="Publicado por el canal oficial "+source+". No se considera tráiler final sin verificación adicional.",kind=kind,published=when,url="https://www.youtube.com/watch?v="+vid,image="https://i.ytimg.com/vi/"+vid+"/hqdefault.jpg",channel=cid))
 return out
def trailer(x):
 title=norm(x["title"])
 if not match(title) or x.get("channel") not in CH or not any(y in title for y in ("trailer","avance")):return False
 if any(y in title for y in ("teaser","spot","promo","featurette","reaction","fan","concept","recap","short","behind")):return False
 if date(x.get("published"))<dt.datetime(2026,11,19,tzinfo=dt.timezone.utc):return False
 try:
  o=json.loads(get("https://www.youtube.com/oembed?format=json&url="+urllib.parse.quote(x["url"],safe="")))
  return "marvel" in norm(o.get("author_name",""))
 except Exception:return False
def articles(query,rumor):
 query=urllib.parse.urlencode({"q":query,"hl":"es-419","gl":"MX","ceid":"MX:es-419"})
 root=ET.fromstring(get("https://news.google.com/rss/search?"+query));out=[]
 for e in root.findall("./channel/item"):
  title=e.findtext("title","");when=e.findtext("pubDate","");link=e.findtext("link","")
  if not match(title) or not recent(when) or not link.startswith("https://"):continue
  source=e.find("source");source=(source.text or "Prensa") if source is not None else "Prensa"
  if not rumor and not any(x in norm(source) for x in ("marvel","disney")):continue
  out.append(dict(id="news-"+str(abs(hash(link))),title=title,description=("Información reportada por "+source+". No confirmada oficialmente por Marvel." if rumor else "Publicación atribuida a "+source+". Comprueba la fuente."),kind=("RUMOR · MEDIOS" if rumor else "COMUNICADO"),published=when,url=link))
 return out
def uniq(items,n):
 seen=set();out=[]
 for x in sorted(items,key=lambda v:date(v.get("published")) or NOW,reverse=True):
  k=norm(x.get("title",""))
  if k in seen:continue
  seen.add(k);out.append(x)
  if len(out)==n:break
 return out
def run():
 old=json.loads(P.read_text("utf-8"));official=[];rumors=[];ok=0
 for cid,name in CH.items():
  try:official+=videos(cid,name);ok+=1
  except Exception as err:print("Could not reach",name,err)
 try:official+=articles('site:marvel.com "Avengers Doomsday" when:3d',False)
 except Exception as err:print("Official news source failed:",err)
 try:rumors+=articles('"Avengers Doomsday" (rumor OR filtracion OR leak OR trailer) when:3d',True)
 except Exception as err:print("Rumor source failed:",err)
 official+= [x for x in old.get("official",[]) if str(x.get("id","")).startswith(("seed-","yt-")) and recent(x.get("published"))]
 rumors+= [x for x in old.get("rumors",[]) if str(x.get("id","")).startswith("seed-") and recent(x.get("published"))]
 official=uniq(official,15);rumors=uniq(rumors,8)
 found=next((x for x in official if x.get("channel") in CH and trailer(x)),None)
 if not found and old.get("monitor",{}).get("released"):found=old["monitor"]["trailer"]
 gallery=[x for x in official if x.get("image")]+[x for x in old.get("gallery",[]) if str(x.get("id","")).startswith("seed-") and recent(x.get("published"))]
 out={"checkedAt":NOW.isoformat() if ok else old.get("checkedAt"),"official":official,"rumors":rumors,"gallery":uniq(gallery,15),"monitor":{"released":bool(found),"trailer":found}}
 P.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n","utf-8")
 print("Sources",ok,"official",len(official),"rumors",len(rumors),"trailer",bool(found))
if __name__=="__main__":run()
