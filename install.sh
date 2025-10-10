#!/bin/bash

echo "닭 먹이 자동 급여 시스템 설치 스크립트 (서버 연동 버전)"
echo "======================================================="

# 필요한 패키지 설치
echo "필수 패키지 설치 중..."
pip3 install RPi.GPIO schedule requests

# 로그 디렉토리 생성
sudo mkdir -p /var/log
sudo touch /var/log/chicken_feeder.log
sudo chown $USER:$USER /var/log/chicken_feeder.log

# systemd 서비스 설치
echo "systemd 서비스 설치 중..."
sudo cp chicken-feeder.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable chicken-feeder.service

echo ""
echo "설치 완료!"
echo ""
echo "사용 가능한 명령어:"
echo "  서비스 시작: sudo systemctl start chicken-feeder"
echo "  서비스 중지: sudo systemctl stop chicken-feeder"
echo "  서비스 상태: sudo systemctl status chicken-feeder"
echo "  로그 확인: sudo journalctl -u chicken-feeder -f"
echo ""
echo "config.json 파일을 수정하여 급여 시간과 서버 설정을 변경할 수 있습니다."
echo ""
echo "서버 연동 기능:"
echo "  - 모든 급여 이벤트가 원격 서버로 전송됩니다"
echo "  - 웹 대시보드: http://서버주소:37210"
echo "  - API 서버: http://서버주소:3001"