import requests
import time
import sys

def test_generation(topic, lang_code, lang_name):
    print(f"\n--- Testing {lang_name} ({lang_code}) ---")
    res = requests.post("http://localhost:8000/api/video/generate", json={
        "topic": topic,
        "language_code": lang_code,
        "language_name": lang_name
    })
    
    if res.status_code != 200:
        print(f"Failed to submit. Status {res.status_code}: {res.text}")
        return False
        
    job_id = res.json()["job_id"]
    print(f"Job queued: {job_id}")
    
    time.sleep(2)
    while True:
        status_res = requests.get(f"http://localhost:8000/api/video/status/{job_id}")
        if status_res.status_code == 404:
            print("Job not registered in Redis yet, waiting...")
            time.sleep(2)
            continue
        if status_res.status_code != 200:
            print(f"Failed to get status. {status_res.text}")
            return False
            
        data = status_res.json()
        status = data["status"]
        print(f"[{status}] {data.get('message', '')} ({data.get('progress', 0)*100:.1f}%)")
        
        if status == "completed":
            print(f"Success! Video URL: {data.get('video_url')}")
            return True
        elif status == "failed":
            print(f"Failed! Error: {data.get('error')}")
            return False
            
        time.sleep(3)

if __name__ == "__main__":
    if not test_generation("Sensex hits 75000 points today", "hi", "Hindi"):
        sys.exit(1)
    if not test_generation("ISRO launches new weather satellite", "ta", "Tamil"):
        sys.exit(1)
    print("All tests passed!")
