FROM jenkins/jenkins:lts-jdk17

USER root

# Docker CLI + compose plugin 설치 (공식 스크립트)
RUN apt-get update \
 && apt-get install -y ca-certificates curl gnupg \
 && rm -rf /var/lib/apt/lists/*

# Docker 공식 설치 스크립트로 docker-ce-cli만 설치
RUN curl -fsSL https://get.docker.com -o /tmp/get-docker.sh \
 && sh /tmp/get-docker.sh --version \
 && rm -f /tmp/get-docker.sh

# docker 데몬까지는 필요없고(호스트 sock 사용), CLI만 쓰면 되므로 docker-ce-cli만 남겨도 되지만
# get.docker.com은 보통 docker-ce-cli 포함으로 설치됩니다.

# Jenkins도 docker 그룹 사용 가능하게(권장)
RUN groupadd -f docker && usermod -aG docker jenkins

COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

USER jenkins
