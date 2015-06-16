FROM ubuntu:14.04.1
RUN apt-get update && apt-get -y upgrade 
RUN apt-get -y install python3.4 git python3-setuptools python3.4-dev openssh-server
RUN easy_install3 pip && pip3.4 install Flask pycrypto
RUN git clone https://github.com/x4dr/NossiNet.git
RUN cp id_rsa.pub /root/.ssh/authorized_keys
WORKDIR /NossiNet
EXPOSE 5000 
EXPOSE 22
ENTRYPOINT /bin/bash
