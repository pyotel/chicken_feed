#!/bin/bash

echo "닭 먹이 급여 시스템 재시작 중..."

# 서비스 중지
sudo systemctl stop chicken-feeder
echo "서비스 중지됨"

# 잠시 대기
sleep 2

# 서비스 시작
sudo systemctl start chicken-feeder
echo "서비스 시작됨"

# 상태 확인
echo ""
echo "서비스 상태:"
sudo systemctl status chicken-feeder --no-pager

echo ""
echo "최근 로그:"
sudo journalctl -u chicken-feeder -n 10 --no-pager