---
id: HX-002
title: 백엔드 주요 OCR 처리 예외 및 로깅 테스트 추가
priority: P2
status: todo
area: backend
stages: [pm, dev, qa]
acceptance:
  - backend/main.py 내 OCR 처리 함수에서 발생 가능한 TimeoutError, ContainerError, 일반 Exception에 대한 예외 처리 경로를 테스트하는 단위 테스트 추가
  - 예외 발생 시 적절한 HTTP 상태 코드와 메시지가 반환되는지 검증
  - 예외 처리 시 로깅이 정상적으로 수행되는지 확인
---
## 배경

[{'backend/main.py': '150~180 (OCR 처리 및 예외 처리 코드)'}, '현재 자동 실행 가능한 테스트가 없으며, 예외 처리 구간에 대한 테스트 부재로 운영 중 예외 상황 대응 리스크 존재']

## 범위

- backend/main.py OCR 처리 함수 예외 처리 경로 단위 테스트 작성
- 테스트 실행 명령어로 정상 동작 확인

## 참고 파일

- backend/main.py

## 출처

Tech Lead 에이전트 제안. 사람이 검토 후 `hermes-fleet approve <repo> <ID>`로 승인한다.
