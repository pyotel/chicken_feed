#!/usr/bin/env python3
"""
연속 회전 서보모터 테스트 스크립트
먹이통 개폐 동작을 테스트합니다.
"""

import RPi.GPIO as GPIO
import time
import sys

SERVO_PIN = 12
SERVO_STOP_DUTY = 7.5      # 정지
SERVO_CW_DUTY = 12         # 시계방향 (열기)
SERVO_CCW_DUTY = 3         # 반시계방향 (닫기)
DEFAULT_ROTATION_TIME = 10  # 10바퀴 회전 시간 (초)

def setup_gpio():
    """GPIO 설정"""
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(SERVO_PIN, GPIO.OUT)
    servo = GPIO.PWM(SERVO_PIN, 50)
    servo.start(0)
    return servo

def rotate_servo(servo, direction, duration):
    """연속 회전 서보 제어

    Args:
        servo: PWM 객체
        direction: 'cw' (시계방향), 'ccw' (반시계방향), 'stop' (정지)
        duration: 회전 시간 (초)
    """
    if direction == 'cw':
        duty = SERVO_CW_DUTY
        print(f"시계방향 회전 (Duty: {duty}) - {duration}초")
    elif direction == 'ccw':
        duty = SERVO_CCW_DUTY
        print(f"반시계방향 회전 (Duty: {duty}) - {duration}초")
    else:
        duty = SERVO_STOP_DUTY
        print(f"정지 (Duty: {duty})")

    servo.ChangeDutyCycle(duty)
    time.sleep(duration)
    servo.ChangeDutyCycle(SERVO_STOP_DUTY)  # 정지
    time.sleep(0.1)
    servo.ChangeDutyCycle(0)  # PWM 신호 끄기

def main():
    """메인 테스트 함수"""
    print("연속 회전 서보모터 테스트 프로그램")
    print("==================================")
    print("명령어:")
    print("  open: 시계방향 10바퀴 회전 (먹이통 열기)")
    print("  close: 반시계방향 10바퀴 회전 (먹이통 닫기)")
    print("  cw [초]: 시계방향으로 지정 시간 회전")
    print("  ccw [초]: 반시계방향으로 지정 시간 회전")
    print("  stop: 모터 정지")
    print("  test: 전체 동작 테스트")
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
            elif command == 'open':
                print(f"먹이통 열기 (시계방향 {DEFAULT_ROTATION_TIME}초)")
                rotate_servo(servo, 'cw', DEFAULT_ROTATION_TIME)
            elif command == 'close':
                print(f"먹이통 닫기 (반시계방향 {DEFAULT_ROTATION_TIME}초)")
                rotate_servo(servo, 'ccw', DEFAULT_ROTATION_TIME)
            elif command == 'cw':
                duration = float(parts[1]) if len(parts) > 1 else 1
                rotate_servo(servo, 'cw', duration)
            elif command == 'ccw':
                duration = float(parts[1]) if len(parts) > 1 else 1
                rotate_servo(servo, 'ccw', duration)
            elif command == 'stop':
                servo.ChangeDutyCycle(SERVO_STOP_DUTY)
                time.sleep(0.1)
                servo.ChangeDutyCycle(0)
                print("모터 정지")
            elif command == 'test':
                print("전체 동작 테스트 시작...")
                print("1. 시계방향 3초 회전")
                rotate_servo(servo, 'cw', 3)
                time.sleep(1)

                print("2. 반시계방향 3초 회전")
                rotate_servo(servo, 'ccw', 3)
                time.sleep(1)

                print("3. 먹이통 열기 (10바퀴)")
                rotate_servo(servo, 'cw', DEFAULT_ROTATION_TIME)
                time.sleep(2)

                print("4. 먹이통 닫기 (10바퀴)")
                rotate_servo(servo, 'ccw', DEFAULT_ROTATION_TIME)
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
