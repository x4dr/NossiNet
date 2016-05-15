FROM ubuntu:16.04.1
RUN apt-get update && apt-get -y upgrade 
RUN apt-get -y install python3.5 git python3-setuptools python3.5-dev openssh-server
RUN easy_install3 pip && pip3.4 install Flask pycrypto flask-socketio
RUN git clone https://github.com/x4dr/NossiNet.git
RUN cp id_rsa.pub /root/.ssh/authorized_keys
WORKDIR /NossiNet
EXPOSE 5000 
EXPOSE 22
ENTRYPOINT /bin/bash
