import os
import sys
import requests
import json
import time

# 设置 API 地址
BASE_URL = "http://127.0.0.1:8000"

def test_hitl_feedback_loop():
    print("🚀 Starting HITL Feedback Loop Test")
    print("-------------------------------------------------------")
    
    # 1. 检查服务状态
    try:
        resp = requests.get(f"{BASE_URL}/status")
        if resp.status_code != 200:
            print("❌ Server not running or error")
            return
        print("✅ Server is running")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    # 2. 确保已加载数据
    print("📂 Loading Excel file...")
    requests.post(f"{BASE_URL}/load", json={"file_path": r"D:\AI_Python\AI2\AI2\back_end_code\Data\Function cost allocation analysis to IT 20260104.xlsx"})
    
    # 3. 发起提问
    query = "IT cost 有哪些服务"
    print(f"\n🗣️ Asking: {query}")
    
    start_time = time.time()
    resp = requests.post(f"{BASE_URL}/chat", json={"message": query})
    if resp.status_code != 200:
        print(f"❌ Chat failed: {resp.text}")
        return
    
    data = resp.json()
    trace_id = data.get("trace_id")
    response_text = data.get("response")
    
    print(f"🤖 Answer: {response_text[:100]}...")
    print(f"🆔 Trace ID: {trace_id}")
    
    if not trace_id:
        print("❌ Trace ID missing in response")
        return

    # 4. 模拟人工确认 (反馈 Correct)
    print("\n👍 Submitting Positive Feedback...")
    feedback_payload = {
        "trace_id": trace_id,
        "is_correct": True,
        "user_comment": "This answer is correct and logic is perfect."
    }
    
    resp = requests.post(f"{BASE_URL}/feedback", json=feedback_payload)
    if resp.status_code == 200:
        print(f"✅ Feedback result: {resp.json().get('message')}")
    else:
        print(f"❌ Feedback failed: {resp.text}")
        return
        
    # 5. 验证知识库是否生成
    print("\n📚 Verifying Knowledge Base...")
    # 等待索引更新（如果是异步的，可能需要一点时间，但目前是同步写入）
    time.sleep(1) 
    
    resp = requests.post(f"{BASE_URL}/knowledge/search", json={"query": query})
    results = resp.json().get("results", [])
    
    found = False
    for item in results:
        if "human-verified" in item.get("tags", []):
            print(f"✅ Found HITL Knowledge: {item['title']}")
            print(f"   Tags: {item['tags']}")
            found = True
            break
            
    if not found:
        print("❌ Failed to find generated HITL knowledge")
    else:
        print("\n🎉 HITL Feedback Loop Verified Successfully!")

if __name__ == "__main__":
    test_hitl_feedback_loop()
