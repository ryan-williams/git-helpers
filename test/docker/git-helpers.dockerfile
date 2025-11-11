FROM ubuntu:22.04

RUN apt-get update -y \
 && apt-get install -y bzip2 git man-db parallel wget python3 python3-pip \
 && yes | unminimize \
 && pip3 install ghpr-py==0.1.3 git-didi==0.1.1 dffs==0.1.0

WORKDIR /root
SHELL ["/bin/bash", "-ic"]

WORKDIR before
RUN compgen -c | sort > compgen-c

WORKDIR ..
COPY . git-helpers
RUN echo 'source ~/git-helpers/.git-rc' >> .bashrc

WORKDIR after
RUN compgen -c | sort > compgen-c

WORKDIR ..

ENTRYPOINT [ "git-helpers/test/docker/diff-compgens" ]
