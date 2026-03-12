"""
H-Chat API 연동 테스트 스크립트
"""

import requests
import json

# API 설정
API_CONFIG = {
    "base_url": "https://internal-apigw-kr.hmg-corp.io/hchat-in/api/v3/claude/messages",
    "api_key": "483ac21c0fbad595d4e7e1c2517a1bae845b098c5252c98bd50f4355b0a01f2e",
    "model": "claude-sonnet-4-5"  # 지원되는 모델로 수정
}

def test_api_connection():
    """API 연결 테스트"""
    
    payload = {
        "max_tokens": 100,
        "model": API_CONFIG["model"],
        "stream": False,
        "system": "You are a helpful assistant.",
        "messages": [
            {
                "role": "user",
                "content": "Hello! Please respond with 'API connection successful' if you can see this message."
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": API_CONFIG["api_key"]
    }
    
    try:
        print("H-Chat API 연결 테스트 중...")
        
        response = requests.post(
            API_CONFIG["base_url"],
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"응답 상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API 연결 성공!")
            print(f"응답: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return True
        else:
            print(f"❌ API 호출 실패: {response.status_code}")
            print(f"오류 내용: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 연결 오류: {str(e)}")
        return False

if __name__ == "__main__":
    test_api_connection()
