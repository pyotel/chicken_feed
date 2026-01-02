#!/usr/bin/env python3
"""
각도 제어 서보모터 테스트 스크립트
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
DEFAULT_MIN_DUTY = 2.5       # 0도
DEFAULT_MAX_DUTY = 12.5      # 180도
DEFAULT_OPEN_ANGLE = 120
DEFAULT_CLOSE_ANGLE = 0
DEFAULT_SERVO_MOVE_TIME = 0.5  # 서보 이동 시간

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

def set_servo_angle(servo, angle, config):
    """서보 각도 설정

    Args:
        servo: PWM 객체
        angle: 목표 각도 (0~180)
        config: 설정 딕셔너리
    """
    min_duty = config.get('servo_min_duty', DEFAULT_MIN_DUTY)
    max_duty = config.get('servo_max_duty', DEFAULT_MAX_DUTY)
    move_time = config.get('servo_move_time', DEFAULT_SERVO_MOVE_TIME)

    # 각도를 duty cycle로 변환
    duty = min_duty + (angle / 180.0) * (max_duty - min_duty)

    print(f"각도: {angle}도 (Duty: {duty:.2f}, 이동시간: {move_time}초)")

    servo.ChangeDutyCycle(duty)
    time.sleep(move_time)
    servo.ChangeDutyCycle(0)  # 떨림 방지

def main():
    """메인 테스트 함수"""
    config = load_config()
    open_angle = config.get('open_angle', DEFAULT_OPEN_ANGLE)
    close_angle = config.get('close_angle', DEFAULT_CLOSE_ANGLE)

    print()
    print("각도 제어 서보모터 테스트 프로그램")
    print("==================================")
    print(f"현재 설정: open_angle={open_angle}도, close_angle={close_angle}도")
    print(f"duty 범위: {config.get('servo_min_duty', DEFAULT_MIN_DUTY)} ~ {config.get('servo_max_duty', DEFAULT_MAX_DUTY)}")
    print()
    print("명령어:")
    print(f"  open: {open_angle}도로 열기")
    print(f"  close: {close_angle}도로 닫기")
    print("  0-180: 해당 각도로 이동")
    print("  test: 전체 동작 테스트")
    print("  reload: 설정 다시 로드")
    print("  quit: 종료")
    print()

    servo = setup_gpio()

    try:
        while True:
            cmd = input("명령 입력> ").strip().lower()

            if not cmd:
                continue

            if cmd == 'quit' or cmd == 'q':
                break
            elif cmd == 'reload':
                config = load_config()
                open_angle = config.get('open_angle', DEFAULT_OPEN_ANGLE)
                close_angle = config.get('close_angle', DEFAULT_CLOSE_ANGLE)
                print(f"설정 다시 로드됨: open={open_angle}도, close={close_angle}도")
            elif cmd == 'open':
                print(f"먹이통 열기 ({open_angle}도)")
                set_servo_angle(servo, open_angle, config)
            elif cmd == 'close':
                print(f"먹이통 닫기 ({close_angle}도)")
                set_servo_angle(servo, close_angle, config)
            elif cmd == 'test':
                print("전체 동작 테스트 시작...")
                print(f"1. 닫기 위치 ({close_angle}도)")
                set_servo_angle(servo, close_angle, config)
                time.sleep(1)

                print(f"2. 열기 위치 ({open_angle}도)")
                set_servo_angle(servo, open_angle, config)
                time.sleep(2)

                print("3. 중간 위치 (60도)")
                set_servo_angle(servo, 60, config)
                time.sleep(1)

                print(f"4. 닫기 위치 ({close_angle}도)")
                set_servo_angle(servo, close_angle, config)
                print("테스트 완료!")
            else:
                try:
                    angle = int(cmd)
                    if 0 <= angle <= 180:
                        set_servo_angle(servo, angle, config)
                    else:
                        print("각도는 0-180 사이여야 합니다.")
                except ValueError:
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
