---
id: HX-001
title: 프런트엔드 Tailwind CSS 및 Pretendard 폰트 미적용 개선
priority: P1
status: todo
area: frontend
stages: [pm, design, dev, qa]
acceptance:
  - frontend/styles.css 파일 내 기존 CSS 변수와 스타일을 Tailwind CSS 유틸리티 클래스로 점진적 마이그레이션한다.
  - Pretendard Variable 폰트를 적용하고 font-family 설정을 Tailwind 설정(theme.extend) 또는 --font-sans로 변경한다.
  - frontend/index.html에서 Google Fonts Noto Sans KR와 FontAwesome CDN 제거하고, Tailwind CSS 및 Pretendard CDN을 정확한 버전으로 고정해 적용한다.
  - 변경된 스타일과 폰트가 기존 UI와 동일하거나 개선됨을 확인한다.
---
## 배경

[{'frontend/index.html': '7~9, 11 (Noto Sans KR, FontAwesome CDN 사용)'}, {'frontend/styles.css': '전체 (기존 CSS 변수와 Noto Sans KR 폰트 사용)'}, '프런트엔드 가이드에 따라 Tailwind CSS와 Pretendard Variable 폰트를 반드시 사용해야 하나, 현재 Noto Sans KR과 별도 CSS 파일(styles.css)로 스타일링되어 있음.']

## 범위

- frontend/index.html에서 Google Fonts Noto Sans KR, FontAwesome CDN 제거 및 Tailwind CSS, Pretendard CDN 추가
- frontend/styles.css 내 기존 폰트 및 색상 변수 Tailwind 설정으로 이전 준비
- Tailwind 설정에 Pretendard 폰트 추가 및 fontFamily.sans 설정
- 주요 UI 컴포넌트에 Tailwind 유틸리티 클래스 적용 테스트 및 조정

## 참고 파일

- frontend/index.html
- frontend/styles.css

## 출처

Tech Lead 에이전트 제안. 사람이 검토 후 `hermes-fleet approve <repo> <ID>`로 승인한다.
