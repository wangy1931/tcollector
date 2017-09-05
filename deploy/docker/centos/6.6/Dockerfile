FROM centos:6.6

MAINTAINER Yongtao You <yongtao.you@cloudwiz.cn>

# Install necessary packages
RUN yum update -y && yum install -y \
    gcc \
    git \
    sudo \
    tar \
    wget \
    which \
    postgresql-devel \
    zlib-devel

# Clone tcollector repo from github.com
RUN mkdir -p /root/src
WORKDIR /root/src
RUN git clone  --depth=1 https://github.com/wangy1931/tcollector.git