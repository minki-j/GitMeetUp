FROM quay.io/astronomer/astro-runtime:11.5.0
USER root
RUN apt-get update 
RUN apt-get -y install git python3-pip
RUN pip3 install pipreqs