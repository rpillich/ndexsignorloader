# Use an official Python runtime as a parent image
FROM continuumio/miniconda3

RUN apt-get update
RUN apt-get install -y build-essential 

RUN mkdir /tmp/ndexsignorloader
COPY ./ /tmp/ndexsignorloader/
RUN pip install /tmp/ndexsignorloader

RUN rm -rf /tmp/ndexsignorloader

RUN mkdir /ndexsignorloader
WORKDIR /ndexsignorloader

CMD /bin/echo "To use run: ndexloadsignor.py"
