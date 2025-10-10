#!/usr/bin/env python3
"""
라즈베리파이 서보모터를 활용한 닭 먹이 자동 급여 시스템
KST 시간 기준으로 설정된 시간에 서보모터를 동작시켜 먹이통 개폐
"""

import RPi.GPIO as GPIO
import schedule
import time
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
import signal
import sys

# 서보모터 설정
SERVO_PIN = 12  # 서보 핀
SERVO_MAX_DUTY = 12  # 서보의 최대(180도) 위치의 주기
SERVO_MIN_DUTY = 3  # 서보의 최소(0도) 위치의 주기

# 한국 시간대 설정
KST = timezone(timedelta(hours=9))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/chicken_feeder.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ChickenFeeder:
    def __init__(self, config_path='config.json'):
        """닭 먹이 급여기 초기화"""
        self.config_path = Path(config_path)
        self.config = self.load_config()
        self.servo = None
        self.is_open = False
        self.setup_gpio()

    def load_config(self):
        """설정 파일 로드"""
        if not self.config_path.exists():
            # 기본 설정 생성
            default_config = {
                "feeding_times": ["07:00", "12:00", "18:00"],
                "feeding_duration_minutes": 30,
                "open_angle": 90,
                "close_angle": 0
            }
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            logger.info(f"기본 설정 파일 생성됨: {self.config_path}")
            return default_config

        with open(self.config_path, 'r') as f:
            config = json.load(f)
            logger.info(f"설정 파일 로드됨: {config}")
            return config

    def setup_gpio(self):
        """GPIO 초기 설정"""
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(SERVO_PIN, GPIO.OUT)
        self.servo = GPIO.PWM(SERVO_PIN, 50)  # 50Hz PWM
        self.servo.start(0)
        logger.info("GPIO 설정 완료")

    def set_servo_position(self, degree):
        """서보모터 위치 설정"""
        if degree > 180:
            degree = 180
        elif degree < 0:
            degree = 0

        duty = SERVO_MIN_DUTY + (degree * (SERVO_MAX_DUTY - SERVO_MIN_DUTY) / 180.0)
        logger.debug(f"서보 위치: {degree}도 (Duty: {duty:.2f})")

        self.servo.ChangeDutyCycle(duty)
        time.sleep(0.5)  # 서보가 위치에 도달할 시간
        self.servo.ChangeDutyCycle(0)  # 서보 떨림 방지

    def open_feeder(self):
        """먹이통 열기"""
        if not self.is_open:
            open_angle = self.config.get('open_angle', 90)
            logger.info(f"먹이통 열기 - {open_angle}도")
            self.set_servo_position(open_angle)
            self.is_open = True

            # 설정된 시간 후 자동으로 닫기
            duration = self.config.get('feeding_duration_minutes', 30)
            schedule.enter(duration * 60, 1, self.close_feeder)

    def close_feeder(self):
        """먹이통 닫기"""
        if self.is_open:
            close_angle = self.config.get('close_angle', 0)
            logger.info(f"먹이통 닫기 - {close_angle}도")
            self.set_servo_position(close_angle)
            self.is_open = False

    def feeding_job(self):
        """급여 작업 실행"""
        now = datetime.now(KST)
        logger.info(f"급여 시작 - {now.strftime('%Y-%m-%d %H:%M:%S KST')}")
        self.open_feeder()

        # 지정된 시간 후 닫기 예약
        duration = self.config.get('feeding_duration_minutes', 30)
        schedule.enter(duration * 60, 1, self.close_feeding_job)

    def close_feeding_job(self):
        """급여 종료 작업"""
        now = datetime.now(KST)
        logger.info(f"급여 종료 - {now.strftime('%Y-%m-%d %H:%M:%S KST')}")
        self.close_feeder()

    def schedule_feedings(self):
        """급여 스케줄 설정"""
        schedule.clear()  # 기존 스케줄 삭제

        for feeding_time in self.config.get('feeding_times', []):
            schedule.every().day.at(feeding_time).do(self.feeding_job)
            logger.info(f"급여 시간 등록: {feeding_time} KST")

    def reload_config(self):
        """설정 파일 다시 로드"""
        logger.info("설정 파일 재로드 중...")
        self.config = self.load_config()
        self.schedule_feedings()
        logger.info("설정 파일 재로드 완료")

    def run(self):
        """메인 실행 루프"""
        logger.info("닭 먹이 자동 급여 시스템 시작")
        logger.info(f"현재 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')}")

        # 초기 스케줄 설정
        self.schedule_feedings()

        # 시작 시 먹이통 닫기 (초기 상태 보장)
        self.close_feeder()

        try:
            while True:
                schedule.run_pending()
                time.sleep(10)  # 10초마다 스케줄 체크

        except KeyboardInterrupt:
            logger.info("프로그램 종료 신호 받음")
        finally:
            self.cleanup()

    def cleanup(self):
        """GPIO 정리"""
        logger.info("시스템 종료 중...")
        self.close_feeder()  # 종료 전 먹이통 닫기
        time.sleep(1)
        self.servo.stop()
        GPIO.cleanup()
        logger.info("GPIO 정리 완료. 프로그램 종료.")


def signal_handler(sig, frame):
    """시그널 핸들러"""
    logger.info("종료 신호 받음")
    sys.exit(0)


if __name__ == "__main__":
    # SIGTERM 시그널 핸들러 등록 (systemd 종료 시)
    signal.signal(signal.SIGTERM, signal_handler)

    # 먹이 급여기 실행
    feeder = ChickenFeeder()
    feeder.run()