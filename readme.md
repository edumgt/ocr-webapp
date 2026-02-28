# Docker Compose Tesseract OCR + GitLab + Jenkins (WSL2 통합 가이드)

이 저장소는 **WSL2 + Docker Desktop** 환경에서 아래 서비스를 한 번에 운영할 수 있도록 구성되어 있습니다.

- OCR Runtime: `ocr-service`, `backend`, `frontend(nginx)`
- CI/CD: `gitlab`, `jenkins`
- 자동화: `Ansible playbook` 기반 일괄 설치/기동

---

## 1) 전체 아키텍처

```text
┌────────────────────────────── User/Developer PC (Windows + WSL2) ──────────────────────────────┐
│                                                                                                   │
│  Browser                                                                                          │
│   ├─ http://localhost:5173  → Frontend (Nginx, Vanilla JS)                                       │
│   ├─ http://localhost:8088  → GitLab CE                                                          │
│   └─ http://localhost:8080  → Jenkins                                                            │
│                                                                                                   │
│  Frontend (5173)                                                                                  │
│      └─ POST /api/ocr                                                                            │
│          → Backend FastAPI (8000)                                                                 │
│              └─ POST /ocr?lang=kor+eng                                                            │
│                  → OCR FastAPI wrapper (8001, internal)                                            │
│                      └─ Tesseract CLI 실행                                                         │
│                                                                                                   │
│  GitLab (8088/2222)                                                                               │
│      └─ Webhook / SCM                                                                             │
│          → Jenkins Pipeline (8080/50000)                                                          │
│              └─ docker.sock 사용해 이미지 빌드/배포                                                │
│                                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2) 서비스 구성 파일

- OCR 서비스 스택: `docker-compose.yml`
- CI/CD 스택: `docker-compose.cicd.yml`
- Jenkins 이미지 빌드 정의: `jenkins/Dockerfile`
- Jenkins 초기 관리자 자동 생성: `jenkins/init.groovy.d/01-admin.groovy`
- Jenkins 플러그인 목록: `jenkins/plugins.txt`
- Ansible 자동화: `ansible/site.yml`

---

## 3) WSL2 + Docker 사전 준비

1. Windows에 Docker Desktop 설치
2. Docker Desktop 설정에서 **Use WSL 2 based engine** 활성화
3. Docker Desktop > Resources > WSL Integration 에서 사용 배포판(예: Ubuntu) 활성화

확인:

```bash
docker --version
docker compose version
ansible --version
```

---

## 4) 수동 실행 방법 (docker compose)

### 4-1. OCR 스택 실행

```bash
cd /workspace/Docker-compose-Tesseract-OCR
docker compose -f docker-compose.yml up --build -d
docker compose -f docker-compose.yml ps
```

접속:
- Frontend: http://localhost:5173
- Backend docs: http://localhost:8000/docs

### 4-2. GitLab + Jenkins 실행

```bash
cd /workspace/Docker-compose-Tesseract-OCR
cp -n .env.cicd.example .env.cicd 2>/dev/null || true
# .env.cicd가 없으면 아래 값으로 직접 생성
# JENKINS_ADMIN_ID=admin
# JENKINS_ADMIN_PASSWORD=admin1234
# GITLAB_EXTERNAL_URL=http://localhost:8088

docker compose --env-file .env.cicd -f docker-compose.cicd.yml up --build -d
docker compose -f docker-compose.cicd.yml ps
```

접속:
- GitLab: http://localhost:8088
- Jenkins: http://localhost:8080

> GitLab 초기 root 비밀번호 확인:

```bash
docker exec -it gitlab bash -lc "cat /etc/gitlab/initial_root_password"
```

---

## 5) Ansible Playbook 기반 일괄 셋팅

다음 1회 명령으로 패키지 준비 + `.env.cicd` 렌더링 + OCR/CI 스택 기동까지 수행합니다.

```bash
cd /workspace/Docker-compose-Tesseract-OCR
ansible-playbook -i ansible/inventory.ini ansible/site.yml
```

주요 변수 파일:
- `ansible/group_vars/all.yml`
  - `project_root`
  - `jenkins_admin_id`
  - `jenkins_admin_password`
  - `gitlab_external_url`

실행 시 생성 파일:
- `.env.cicd` (민감정보 포함 가능, 기본 권한 0600)

---

## 6) GitLab 운영/사용 가이드

### 6-1. 최초 로그인
1. `root` 계정으로 로그인
2. 초기 비밀번호는 컨테이너 내부 파일에서 조회
3. 로그인 후 즉시 비밀번호 변경 권장

### 6-2. 프로젝트 생성 및 Push
1. 새 프로젝트 생성 (`docker-sample` 예제로 사용 가능)
2. WSL 터미널에서 remote 등록 후 push

```bash
cd /workspace/Docker-compose-Tesseract-OCR/docker-sample
git init
git remote add origin http://localhost:8088/<group>/<project>.git
git add .
git commit -m "init"
git push -u origin main
```

### 6-3. Webhook 설정
- GitLab Project > Settings > Webhooks
- Jenkins용 URL 등록(예: Generic webhook trigger 또는 GitLab plugin endpoint)
- Push events 활성화

---

## 7) Jenkins 운영/사용 가이드

### 7-1. 최초 로그인
- URL: http://localhost:8080
- 기본 관리자 계정은 `.env.cicd` 또는 compose 환경변수 기준
  - ID: `JENKINS_ADMIN_ID`
  - PW: `JENKINS_ADMIN_PASSWORD`

### 7-2. 권장 플러그인
`jenkins/plugins.txt`에 정의된 플러그인이 이미지 빌드 시 자동 설치됩니다.
- pipeline, git, gitlab-plugin, docker-workflow 등

### 7-3. GitLab 연동 파이프라인
1. Jenkins에서 Pipeline job 생성
2. SCM을 GitLab repo로 지정
3. 저장소의 `Jenkinsfile` 사용
4. Credential(사용자/토큰) 등록
5. Webhook 트리거와 연동

예제 Jenkinsfile은 `docker-sample/Jenkinsfile` 참고:
- checkout
- docker build
- container run
- smoke test

---

## 8) OCR API 사용법

### Backend API
- `GET /health`
- `POST /api/ocr?lang=kor+eng`
  - form-data: `file`

응답 예시:

```json
{
  "text": "인식된 텍스트",
  "lang": "kor+eng",
  "filename": "sample.png"
}
```

---

## 9) 트러블슈팅

### GitLab 접속/인증 이슈
- HTTP 환경에서 Git credential 관련 정책에 막히는 경우 `gitlab_config.md` 참고

### Jenkins가 Docker 명령 실패
- `jenkins` 컨테이너에 `/var/run/docker.sock` 마운트 여부 확인
- Jenkins 컨테이너 내부에서 `docker --version` 확인

### OCR 연결 실패 (502 등)
- `docker compose -f docker-compose.yml logs -f backend`
- `docker compose -f docker-compose.yml logs -f ocr-service`

---

## 10) 주요 명령어 모음

```bash
# 전체 상태 확인
cd /workspace/Docker-compose-Tesseract-OCR
docker compose -f docker-compose.yml ps
docker compose -f docker-compose.cicd.yml ps

# 로그 확인
docker compose -f docker-compose.yml logs -f backend
docker compose -f docker-compose.cicd.yml logs -f jenkins

# 종료
docker compose -f docker-compose.yml down
docker compose -f docker-compose.cicd.yml down
```
