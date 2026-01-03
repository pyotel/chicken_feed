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

# 서보모터 기본 설정 (각도 제어 서보)
SERVO_PIN = 12
DEFAULT_MIN_DUTY = 2.5       # 0도 (500us/20ms)
DEFAULT_MAX_DUTY = 12.5      # 180도 (2500us/20ms)
DEFAULT_OPEN_ANGLE = 120     # 열기 각도
DEFAULT_CLOSE_ANGLE = 0      # 닫기 각도
DEFAULT_SERVO_MOVE_TIME = 0.5  # 서보 이동 시간 (초)

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
                "open_angle": DEFAULT_OPEN_ANGLE,
                "close_angle": DEFAULT_CLOSE_ANGLE,
                "servo_min_duty": DEFAULT_MIN_DUTY,
                "servo_max_duty": DEFAULT_MAX_DUTY,
                "servo_move_time": DEFAULT_SERVO_MOVE_TIME,
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

    def set_servo_angle(self, angle):
        """서보 모터 각도 설정

        Args:
            angle: 목표 각도 (0~180)
        """
        min_duty = self.config.get('servo_min_duty', DEFAULT_MIN_DUTY)
        max_duty = self.config.get('servo_max_duty', DEFAULT_MAX_DUTY)
        move_time = self.config.get('servo_move_time', DEFAULT_SERVO_MOVE_TIME)

        # 각도를 duty cycle로 변환 (0도=min_duty, 180도=max_duty)
        duty = min_duty + (angle / 180.0) * (max_duty - min_duty)

        logger.debug(f"서보 각도: {angle}도, Duty: {duty:.2f}, 이동시간: {move_time}초")

        self.servo.ChangeDutyCycle(duty)
        time.sleep(move_time)  # 서보가 위치에 도달할 시간
        self.servo.ChangeDutyCycle(0)  # PWM 신호 끄기 (떨림 방지)

    def open_feeder(self):
        """먹이통 열기"""
        if not self.is_open:
            open_angle = self.config.get('open_angle', DEFAULT_OPEN_ANGLE)
            logger.info(f"먹이통 열기 - {open_angle}도")

            try:
                self.set_servo_angle(open_angle)
                self.is_open = True
                self.send_log_to_server("open", {"angle": open_angle})
            except Exception as e:
                logger.error(f"먹이통 열기 실패: {e}")
                self.send_log_to_server("error", {"message": str(e)})

    def close_feeder(self):
        """먹이통 닫기"""
        if self.is_open:
            close_angle = self.config.get('close_angle', DEFAULT_CLOSE_ANGLE)
            logger.info(f"먹이통 닫기 - {close_angle}도")

            try:
                self.set_servo_angle(close_angle)
                self.is_open = False
                self.send_log_to_server("close", {"angle": close_angle})
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

    def check_server_command(self):
        """서버에서 원격 명령 확인 및 실행"""
        try:
            server_url = self.config.get('server_url', SERVER_URL)
            device_id = self.config.get('device_id', DEVICE_ID)

            response = requests.get(
                f"{server_url}/api/device/command/{device_id}",
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('has_command'):
                    command = data.get('command')
                    logger.info(f"서버 명령 수신: {command}")

                    if command == 'open':
                        # 강제로 열기 (is_open 상태 무시)
                        self.is_open = False
                        self.open_feeder()
                    elif command == 'close':
                        # 강제로 닫기 (is_open 상태 무시)
                        self.is_open = True
                        self.close_feeder()

        except Exception as e:
            logger.debug(f"서버 명령 확인 중 오류 (무시): {e}")

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
                self.check_server_command()  # 서버 명령 확인
                time.sleep(5)  # 5초마다 확인

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