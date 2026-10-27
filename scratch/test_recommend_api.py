import sys
import os
sys.path.insert(0, os.path.abspath("."))
import requests
import json
from app import app

client = app.test_client()

target = "Avengers: Endgame"
print(f"=== TESTING RECOMMENDATION API FOR: '{target}' ===\n")

for alpha in [0.0, 0.6, 1.0]:
    resp = client.get(f"/api/recommend?movie={target}&alpha={alpha}&n=10")
    assert resp.status_code == 200, f"Error {resp.status_code}: {resp.data}"
    data = json.loads(resp.data)
    
    print(f"--- ALPHA = {alpha} ({int((1-alpha)*100)}% Collab / {int(alpha*100)}% Content) ---")
    recs = data.get("recommendations", [])
    for i, r in enumerate(recs, 1):
        score = r.get("score")
        c_score = r.get("content_score")
        cl_score = r.get("collab_score")
        title = r.get("title")
        year = r.get("year")
        why = r.get("why_recommended")
        print(f"{i:2d}. {title} ({year}) | Match: {round(score*100)}% | Content: {round(c_score*100)}% | Collab: {round(cl_score*100)}% | Reason: {why}")
    print()

def test_movie(title):
    print(f"\n=================== TESTING '{title}' ===================")
    for alpha in [0.0, 0.6, 1.0]:
        resp = client.get(f"/api/recommend?movie={title}&alpha={alpha}&n=5")
        data = json.loads(resp.data)
        print(f"--- ALPHA = {alpha} ---")
        for r in data.get("recommendations", []):
            print(f" - {r['title']} ({r['year']}) | Match: {round(r['score']*100)}% | Content: {round(r['content_score']*100)}% | Collab: {round(r['collab_score']*100)}%")

test_movie("The Dark Knight")
test_movie("Inception")

