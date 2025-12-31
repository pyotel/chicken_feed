#!/usr/bin/env python3
"""
연속 회전 서보모터 테스트 스크립트
먹이통 개폐 동작을 테스트합니다.
config.json에서 설정을 읽어옵니다.
"""

import RPi.GPIO as GPIO
import time
import sys
import json
from pathlib import Path

SERVO_PIN = 12

# 기본값
DEFAULT_STOP_DUTY = 7.5
DEFAULT_CW_DUTY = 9.75
DEFAULT_CCW_DUTY = 5.25
DEFAULT_ROTATION_TIME = 10

def load_config():
    """config.json에서 설정 로드"""
    config_path = Path(__file__).parent / 'config.json'
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
            print(f"설정 파일 로드됨: {config_path}")
            return config
    print("설정 파일이 없어 기본값 사용")
    return {}

def setup_gpio():
    """GPIO 설정"""
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(SERVO_PIN, GPIO.OUT)
    servo = GPIO.PWM(SERVO_PIN, 50)
    servo.start(0)
    return servo

def rotate_servo(servo, direction, duration, config):
    """연속 회전 서보 제어

    Args:
        servo: PWM 객체
        direction: 'cw' (시계방향), 'ccw' (반시계방향), 'stop' (정지)
        duration: 회전 시간 (초)
        config: 설정 딕셔너리
    """
    stop_duty = config.get('servo_stop_duty', DEFAULT_STOP_DUTY)
    cw_duty = config.get('servo_cw_duty', DEFAULT_CW_DUTY)
    ccw_duty = config.get('servo_ccw_duty', DEFAULT_CCW_DUTY)

    if direction == 'cw':
        duty = cw_duty
        print(f"시계방향 회전 (Duty: {duty}) - {duration}초")
    elif direction == 'ccw':
        duty = ccw_duty
        print(f"반시계방향 회전 (Duty: {duty}) - {duration}초")
    else:
        duty = stop_duty
        print(f"정지 (Duty: {duty})")

    servo.ChangeDutyCycle(duty)
    time.sleep(duration)
    servo.ChangeDutyCycle(stop_duty)  # 정지
    time.sleep(0.1)
    servo.ChangeDutyCycle(0)  # PWM 신호 끄기

def main():
    """메인 테스트 함수"""
    config = load_config()
    rotation_time = config.get('rotation_time', DEFAULT_ROTATION_TIME)
    stop_duty = config.get('servo_stop_duty', DEFAULT_STOP_DUTY)

    print()
    print("연속 회전 서보모터 테스트 프로그램")
    print("==================================")
    print(f"현재 설정: rotation_time={rotation_time}초, "
          f"cw_duty={config.get('servo_cw_duty', DEFAULT_CW_DUTY)}, "
          f"ccw_duty={config.get('servo_ccw_duty', DEFAULT_CCW_DUTY)}")
    print()
    print("명령어:")
    print(f"  open: 시계방향 {rotation_time}초 회전 (먹이통 열기)")
    print(f"  close: 반시계방향 {rotation_time}초 회전 (먹이통 닫기)")
    print("  cw [초]: 시계방향으로 지정 시간 회전")
    print("  ccw [초]: 반시계방향으로 지정 시간 회전")
    print("  stop: 모터 정지")
    print("  test: 전체 동작 테스트")
    print("  reload: 설정 다시 로드")
    print("  quit: 종료")
    print()

    servo = setup_gpio()

    try:
        while True:
            cmd = input("명령 입력> ").strip().lower()
            parts = cmd.split()

            if not parts:
                continue

            command = parts[0]

            if command == 'quit' or command == 'q':
                break
            elif command == 'reload':
                config = load_config()
                rotation_time = config.get('rotation_time', DEFAULT_ROTATION_TIME)
                print(f"설정 다시 로드됨: rotation_time={rotation_time}초")
            elif command == 'open':
                print(f"먹이통 열기 (시계방향 {rotation_time}초)")
                rotate_servo(servo, 'cw', rotation_time, config)
            elif command == 'close':
                print(f"먹이통 닫기 (반시계방향 {rotation_time}초)")
                rotate_servo(servo, 'ccw', rotation_time, config)
            elif command == 'cw':
                duration = float(parts[1]) if len(parts) > 1 else 1
                rotate_servo(servo, 'cw', duration, config)
            elif command == 'ccw':
                duration = float(parts[1]) if len(parts) > 1 else 1
                rotate_servo(servo, 'ccw', duration, config)
            elif command == 'stop':
                servo.ChangeDutyCycle(stop_duty)
                time.sleep(0.1)
                servo.ChangeDutyCycle(0)
                print("모터 정지")
            elif command == 'test':
                print("전체 동작 테스트 시작...")
                print("1. 시계방향 3초 회전")
                rotate_servo(servo, 'cw', 3, config)
                time.sleep(1)

                print("2. 반시계방향 3초 회전")
                rotate_servo(servo, 'ccw', 3, config)
                time.sleep(1)

                print(f"3. 먹이통 열기 ({rotation_time}초)")
                rotate_servo(servo, 'cw', rotation_time, config)
                time.sleep(2)

                print(f"4. 먹이통 닫기 ({rotation_time}초)")
                rotate_servo(servo, 'ccw', rotation_time, config)
                print("테스트 완료!")
            else:
                print("올바른 명령어를 입력하세요.")

    except KeyboardInterrupt:
        print("\n프로그램 종료...")
    finally:
        servo.ChangeDutyCycle(0)
        servo.stop()
        GPIO.cleanup()
        print("GPIO 정리 완료")

if __name__ == "__main__":
    main()
