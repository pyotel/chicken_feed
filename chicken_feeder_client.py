#!/usr/bin/env python3
"""
라즈베리파이 서보모터를 활용한 닭 먹이 자동 급여 시스템 (서버 연동 버전)
KST 시간 기준으로 설정된 시간에 서보모터를 동작시켜 먹이통 개폐
모든 이벤트를 원격 서버로 전송
"""

import RPi.GPIO as GPIO
import schedule
import time
import json
import logging
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
import signal
import sys

# 서보모터 기본 설정 (연속 회전 서보)
SERVO_PIN = 12
DEFAULT_STOP_DUTY = 7.5      # 정지
DEFAULT_CW_DUTY = 9.75       # 시계방향 (열기) - 절반 속도
DEFAULT_CCW_DUTY = 5.25      # 반시계방향 (닫기) - 절반 속도
DEFAULT_ROTATION_TIME = 10   # 10바퀴 회전에 필요한 시간 (초)

# 한국 시간대 설정
KST = timezone(timedelta(hours=9))

# 서버 설정
SERVER_URL = "http://ketiict.com:37211"  # 서버 주소
DEVICE_ID = "raspberry-pi-001"

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


class ChickenFeederClient:
    def __init__(self, config_path='config.json'):
        """닭 먹이 급여기 클라이언트 초기화"""
        self.config_path = Path(config_path)
        self.config = self.load_config()
        self.servo = None
        self.is_open = False
        self.setup_gpio()
        self.register_with_server()

    def load_config(self):
        """설정 파일 로드"""
        if not self.config_path.exists():
            default_config = {
                "feeding_times": ["07:00", "12:00", "18:00"],
                "feeding_duration_minutes": 30,
                "rotation_time": DEFAULT_ROTATION_TIME,
                "servo_stop_duty": DEFAULT_STOP_DUTY,
                "servo_cw_duty": DEFAULT_CW_DUTY,
                "servo_ccw_duty": DEFAULT_CCW_DUTY,
                "server_url": SERVER_URL,
                "device_id": DEVICE_ID
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
        self.servo = GPIO.PWM(SERVO_PIN, 50)
        self.servo.start(0)
        logger.info("GPIO 설정 완료")

    def register_with_server(self):
        """서버에 장치 등록 및 설정 업데이트"""
        try:
            server_url = self.config.get('server_url', SERVER_URL)
            device_id = self.config.get('device_id', DEVICE_ID)

            data = {
                "device_id": device_id,
                "feeding_times": self.config.get('feeding_times', ["07:00", "12:00", "18:00"]),
                "duration_minutes": self.config.get('feeding_duration_minutes', 30)
            }

            response = requests.post(
                f"{server_url}/api/device/config",
                json=data,
                timeout=5
            )

            if response.status_code == 200:
                logger.info(f"서버에 장치 등록 완료: {device_id}")
            else:
                logger.warning(f"서버 등록 실패: {response.status_code}")

        except Exception as e:
            logger.error(f"서버 등록 중 오류: {e}")

    def send_log_to_server(self, action, details=None):
        """서버로 로그 전송"""
        try:
            server_url = self.config.get('server_url', SERVER_URL)
            device_id = self.config.get('device_id', DEVICE_ID)

            data = {
                "device_id": device_id,
                "action": action,
                "timestamp": datetime.now(KST).isoformat(),
                "details": details or {}
            }

            response = requests.post(
                f"{server_url}/api/feeding/log",
                json=data,
                timeout=5
            )

            if response.status_code != 200:
                logger.warning(f"로그 전송 실패: {response.status_code}")

        except Exception as e:
            logger.error(f"로그 전송 중 오류: {e}")

    def rotate_servo(self, direction, duration):
        """연속 회전 서보 모터 제어

        Args:
            direction: 'cw' (시계방향/열기) 또는 'ccw' (반시계방향/닫기)
            duration: 회전 시간 (초)
        """
        stop_duty = self.config.get('servo_stop_duty', DEFAULT_STOP_DUTY)
        cw_duty = self.config.get('servo_cw_duty', DEFAULT_CW_DUTY)
        ccw_duty = self.config.get('servo_ccw_duty', DEFAULT_CCW_DUTY)

        if direction == 'cw':
            duty = cw_duty
        elif direction == 'ccw':
            duty = ccw_duty
        else:
            duty = stop_duty

        logger.debug(f"서보 회전: {direction}, Duty: {duty}, 시간: {duration}초")

        self.servo.ChangeDutyCycle(duty)
        time.sleep(duration)
        self.servo.ChangeDutyCycle(stop_duty)  # 정지
        time.sleep(0.1)
        self.servo.ChangeDutyCycle(0)  # PWM 신호 끄기 (떨림 방지)

    def open_feeder(self):
        """먹이통 열기 - 시계방향으로 10바퀴 회전"""
        if not self.is_open:
            rotation_time = self.config.get('rotation_time', DEFAULT_ROTATION_TIME)
            logger.info(f"먹이통 열기 - 시계방향 {rotation_time}초 회전")

            try:
                self.rotate_servo('cw', rotation_time)
                self.is_open = True
                self.send_log_to_server("open", {"rotation_time": rotation_time})
            except Exception as e:
                logger.error(f"먹이통 열기 실패: {e}")
                self.send_log_to_server("error", {"message": str(e)})

    def close_feeder(self):
        """먹이통 닫기 - 반시계방향으로 10바퀴 회전"""
        if self.is_open:
            rotation_time = self.config.get('rotation_time', DEFAULT_ROTATION_TIME)
            logger.info(f"먹이통 닫기 - 반시계방향 {rotation_time}초 회전")

            try:
                self.rotate_servo('ccw', rotation_time)
                self.is_open = False
                self.send_log_to_server("close", {"rotation_time": rotation_time})
            except Exception as e:
                logger.error(f"먹이통 닫기 실패: {e}")
                self.send_log_to_server("error", {"message": str(e)})

    def feeding_job(self):
        """급여 작업 실행"""
        now = datetime.now(KST)
        logger.info(f"급여 시작 - {now.strftime('%Y-%m-%d %H:%M:%S KST')}")
        self.open_feeder()

        duration = self.config.get('feeding_duration_minutes', 30)
        schedule.enter(duration * 60, 1, self.close_feeding_job)

    def close_feeding_job(self):
        """급여 종료 작업"""
        now = datetime.now(KST)
        logger.info(f"급여 종료 - {now.strftime('%Y-%m-%d %H:%M:%S KST')}")
        self.close_feeder()

    def schedule_feedings(self):
        """급여 스케줄 설정"""
        schedule.clear()

        for feeding_time in self.config.get('feeding_times', []):
            schedule.every().day.at(feeding_time).do(self.feeding_job)
            logger.info(f"급여 시간 등록: {feeding_time} KST")

    def reload_config(self):
        """설정 파일 다시 로드"""
        logger.info("설정 파일 재로드 중...")
        self.config = self.load_config()
        self.schedule_feedings()
        self.register_with_server()
        logger.info("설정 파일 재로드 완료")

    def run(self):
        """메인 실행 루프"""
        logger.info("닭 먹이 자동 급여 시스템 시작 (서버 연동 모드)")
        logger.info(f"현재 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')}")
        logger.info(f"서버 URL: {self.config.get('server_url', SERVER_URL)}")
        logger.info(f"장치 ID: {self.config.get('device_id', DEVICE_ID)}")

        # 시작 로그 전송
        self.send_log_to_server("startup", {
            "config": {
                "feeding_times": self.config.get('feeding_times'),
                "duration_minutes": self.config.get('feeding_duration_minutes')
            }
        })

        # 초기 스케줄 설정
        self.schedule_feedings()

        # 시작 시 먹이통 닫기
        self.close_feeder()

        try:
            while True:
                schedule.run_pending()
                time.sleep(10)

        except KeyboardInterrupt:
            logger.info("프로그램 종료 신호 받음")
        finally:
            self.cleanup()

    def cleanup(self):
        """GPIO 정리"""
        logger.info("시스템 종료 중...")

        # 종료 로그 전송
        self.send_log_to_server("shutdown", {})

        self.close_feeder()
        time.sleep(1)
        self.servo.stop()
        GPIO.cleanup()
        logger.info("GPIO 정리 완료. 프로그램 종료.")


def signal_handler(sig, frame):
    """시그널 핸들러"""
    logger.info("종료 신호 받음")
    sys.exit(0)


if __name__ == "__main__":
    # SIGTERM 시그널 핸들러 등록
    signal.signal(signal.SIGTERM, signal_handler)

    # 먹이 급여기 클라이언트 실행
    feeder = ChickenFeederClient()
    feeder.run()