FROM debian:7

MAINTAINER Yongtao You <yongtao.you@cloudwiz.cn>

# Install necessary packages
RUN apt-get update -y && apt-get install -y \
    curl \
    gcc \
    git-core \
    make \
    openssh-client \
    sudo \
    wget \
    libpq-dev \
    zlib1g-dev

# Clone tcollector repo from github.com
RUN mkdir -p /root/src
WORKDIR /root/src
RUN git clone  --depth=1 https://github.com/wangy1931/tcollector.git