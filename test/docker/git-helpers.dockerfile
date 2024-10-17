FROM ubuntu:22.04

RUN apt-get update -y \
 && apt-get install -y git wget

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
