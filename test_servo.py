#!/usr/bin/env python3
"""
서보모터 테스트 스크립트
먹이통 개폐 동작을 테스트합니다.
"""

import RPi.GPIO as GPIO
import time
import sys

SERVO_PIN = 12
SERVO_MAX_DUTY = 12
SERVO_MIN_DUTY = 3

def setup_gpio():
    """GPIO 설정"""
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(SERVO_PIN, GPIO.OUT)
    servo = GPIO.PWM(SERVO_PIN, 50)
    servo.start(0)
    return servo

def set_servo_position(servo, degree):
    """서보 위치 설정"""
    if degree > 180:
        degree = 180
    elif degree < 0:
        degree = 0

    duty = SERVO_MIN_DUTY + (degree * (SERVO_MAX_DUTY - SERVO_MIN_DUTY) / 180.0)
    print(f"각도: {degree}도 (Duty: {duty:.2f})")

    servo.ChangeDutyCycle(duty)
    time.sleep(0.5)
    servo.ChangeDutyCycle(0)  # 떨림 방지

def main():
    """메인 테스트 함수"""
    print("서보모터 테스트 프로그램")
    print("========================")
    print("명령어:")
    print("  0-180: 해당 각도로 이동")
    print("  open: 90도로 열기")
    print("  close: 0도로 닫기")
    print("  test: 전체 동작 테스트")
    print("  quit: 종료")
    print()

    servo = setup_gpio()

    try:
        while True:
            cmd = input("명령 입력> ").strip().lower()

            if cmd == 'quit' or cmd == 'q':
                break
            elif cmd == 'open':
                print("먹이통 열기 (90도)")
                set_servo_position(servo, 90)
            elif cmd == 'close':
                print("먹이통 닫기 (0도)")
                set_servo_position(servo, 0)
            elif cmd == 'test':
                print("전체 동작 테스트 시작...")
                print("1. 초기 위치 (0도)")
                set_servo_position(servo, 0)
                time.sleep(1)

                print("2. 먹이통 열기 (90도)")
                set_servo_position(servo, 90)
                time.sleep(2)

                print("3. 부분 열기 (45도)")
                set_servo_position(servo, 45)
                time.sleep(1)

                print("4. 완전 열기 (180도)")
                set_servo_position(servo, 180)
                time.sleep(2)

                print("5. 먹이통 닫기 (0도)")
                set_servo_position(servo, 0)
                print("테스트 완료!")
            else:
                try:
                    angle = int(cmd)
                    if 0 <= angle <= 180:
                        set_servo_position(servo, angle)
                    else:
                        print("각도는 0-180 사이여야 합니다.")
                except ValueError:
                    print("올바른 명령어를 입력하세요.")

    except KeyboardInterrupt:
        print("\n프로그램 종료...")
    finally:
        servo.stop()
        GPIO.cleanup()
        print("GPIO 정리 완료")

if __name__ == "__main__":
    main()