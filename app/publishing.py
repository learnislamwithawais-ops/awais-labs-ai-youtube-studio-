import os
from pathlib import Path
def upload(path,title,description="",tags=None,privacy="private"):
 if os.getenv("ENABLE_YOUTUBE_UPLOAD","false").lower()!="true":raise RuntimeError("YouTube uploads disabled. Configure OAuth then enable ENABLE_YOUTUBE_UPLOAD.")
 token=os.getenv("YOUTUBE_TOKEN_FILE","/app/secrets/youtube-token.json")
 if not Path(token).exists():raise RuntimeError("OAuth token file missing at configured path.")
 from google.oauth2.credentials import Credentials
 from googleapiclient.discovery import build
 from googleapiclient.http import MediaFileUpload
 creds=Credentials.from_authorized_user_file(token,["https://www.googleapis.com/auth/youtube.upload"])
 yt=build("youtube","v3",credentials=creds,cache_discovery=False)
 body={"snippet":{"title":title[:100],"description":description[:5000],"tags":(tags or [])[:500],"categoryId":"20"},"status":{"privacyStatus":privacy,"selfDeclaredMadeForKids":False}}
 result=yt.videos().insert(part="snippet,status",body=body,media_body=MediaFileUpload(str(path),chunksize=-1,resumable=True)).execute()
 return {"video_id":result["id"],"url":"https://youtube.com/watch?v="+result["id"]}
