FROM ubuntu:22.04

RUN apt-get update -y \
 && apt-get install -y git wget

WORKDIR /root
SHELL ["/bin/bash", "-ic"]

WORKDIR before
RUN compgen -c | sort > compgen-c

WORKDIR ..
RUN git clone https://github.com/ryan-williams/git-helpers \
 && echo 'source ~/git-helpers/.git-rc' >> .bashrc

WORKDIR after
RUN compgen -c | sort > compgen-c

WORKDIR ..
COPY diff-compgens ./

ENTRYPOINT [ "./diff-compgens" ]
