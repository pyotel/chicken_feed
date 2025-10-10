#!/usr/bin/env python3
"""
클라이언트 서버 연동 테스트 스크립트
서버 없이 클라이언트 기능을 테스트합니다.
"""

import json
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 한국 시간대 설정
KST = timezone(timedelta(hours=9))

def load_config():
    """설정 파일 로드"""
    config_path = Path('config.json')
    if not config_path.exists():
        print("설정 파일이 없습니다!")
        return None

    with open(config_path, 'r') as f:
        return json.load(f)

def test_server_connection(config):
    """서버 연결 테스트"""
    server_url = config.get('server_url', 'http://localhost:3001')

    print(f"서버 연결 테스트: {server_url}")
    print("-" * 40)

    try:
        # Health check
        response = requests.get(f"{server_url}/api/health", timeout=5)
        if response.status_code == 200:
            print("✓ 서버 상태: 정상")
            print(f"  응답: {response.json()}")
        else:
            print(f"✗ 서버 상태: 오류 ({response.status_code})")
            return False

    except requests.exceptions.RequestException as e:
        print(f"✗ 서버 연결 실패: {e}")
        return False

    return True

def test_device_registration(config):
    """장치 등록 테스트"""
    server_url = config.get('server_url', 'http://localhost:3001')
    device_id = config.get('device_id', 'raspberry-pi-001')

    print("\n장치 등록 테스트")
    print("-" * 40)

    data = {
        "device_id": device_id,
        "feeding_times": config.get('feeding_times', ["07:00", "12:00", "18:00"]),
        "duration_minutes": config.get('feeding_duration_minutes', 30)
    }

    try:
        response = requests.post(
            f"{server_url}/api/device/config",
            json=data,
            timeout=5
        )

        if response.status_code == 200:
            print(f"✓ 장치 등록 성공: {device_id}")
            print(f"  설정: {json.dumps(data, indent=2)}")
        else:
            print(f"✗ 장치 등록 실패: {response.status_code}")
            print(f"  응답: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"✗ 요청 실패: {e}")
        return False

    return True

def test_log_sending(config):
    """로그 전송 테스트"""
    server_url = config.get('server_url', 'http://localhost:3001')
    device_id = config.get('device_id', 'raspberry-pi-001')

    print("\n로그 전송 테스트")
    print("-" * 40)

    # 테스트 로그 데이터
    test_logs = [
        {"action": "startup", "details": {"test": True}},
        {"action": "open", "details": {"angle": 90}},
        {"action": "close", "details": {"angle": 0}},
    ]

    for log in test_logs:
        data = {
            "device_id": device_id,
            "action": log["action"],
            "timestamp": datetime.now(KST).isoformat(),
            "details": log["details"]
        }

        try:
            response = requests.post(
                f"{server_url}/api/feeding/log",
                json=data,
                timeout=5
            )

            if response.status_code == 200:
                print(f"✓ 로그 전송 성공: {log['action']}")
            else:
                print(f"✗ 로그 전송 실패: {log['action']} ({response.status_code})")

        except requests.exceptions.RequestException as e:
            print(f"✗ 요청 실패: {e}")
            return False

    return True

def test_log_retrieval(config):
    """로그 조회 테스트"""
    server_url = config.get('server_url', 'http://localhost:3001')
    device_id = config.get('device_id', 'raspberry-pi-001')

    print("\n로그 조회 테스트")
    print("-" * 40)

    try:
        response = requests.get(
            f"{server_url}/api/feeding/logs/{device_id}?limit=5",
            timeout=5
        )

        if response.status_code == 200:
            logs = response.json()
            print(f"✓ 로그 조회 성공: {len(logs)}개 로그")
            for log in logs[:3]:  # 최근 3개만 표시
                print(f"  - {log['action']}: {log['timestamp']}")
        else:
            print(f"✗ 로그 조회 실패: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"✗ 요청 실패: {e}")
        return False

    return True

def main():
    """메인 테스트 함수"""
    print("닭 먹이 급여 시스템 - 클라이언트 서버 연동 테스트")
    print("=" * 50)

    # 설정 로드
    config = load_config()
    if not config:
        return

    print(f"서버 URL: {config.get('server_url')}")
    print(f"장치 ID: {config.get('device_id')}")

    # 테스트 실행
    tests = [
        ("서버 연결", test_server_connection),
        ("장치 등록", test_device_registration),
        ("로그 전송", test_log_sending),
        ("로그 조회", test_log_retrieval),
    ]

    results = []
    for name, test_func in tests:
        success = test_func(config)
        results.append((name, success))

    # 결과 요약
    print("\n" + "=" * 50)
    print("테스트 결과 요약")
    print("-" * 40)

    for name, success in results:
        status = "✓ 성공" if success else "✗ 실패"
        print(f"{name}: {status}")

    total = len(results)
    passed = sum(1 for _, success in results if success)
    print(f"\n전체: {passed}/{total} 테스트 통과")

    if passed == total:
        print("\n모든 테스트가 성공했습니다! 서비스를 시작할 준비가 되었습니다.")
        print("서비스 시작: sudo systemctl start chicken-feeder")
    else:
        print("\n일부 테스트가 실패했습니다. 서버 설정을 확인해주세요.")

if __name__ == "__main__":
    main()