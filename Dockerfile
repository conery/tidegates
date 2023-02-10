#
#  Dockerfile for the Tide Gate Optimization Tool
#
#  John Conery (conery@uoregon.edu) 
#
#  Using Ubuntu 18.04 as the base image, in order to support Wine and the
#  packages it needs, then install Python and its libraries
#

FROM ubuntu:22.04

# Define the user name and group ID for non-root user
ARG USERNAME=alignak
ARG USER_UID=1001
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME

# 32-bit support needed by wine
RUN dpkg --add-architecture i386

# Install wget
RUN apt-get update
RUN apt-get install -y wget

# Install Wine
RUN apt-get install -y software-properties-common gnupg2
RUN wget -nc https://dl.winehq.org/wine-builds/winehq.key
RUN apt-key add winehq.key
RUN apt-add-repository 'deb https://dl.winehq.org/wine-builds/ubuntu/ jammy main'
RUN apt-get install -y --install-recommends winehq-stable winbind

ENV WINEDEBUG=fixme-all
ENV WINEARCH=win64
RUN winecfg

# Install Xvfb
RUN apt-get install -y xvfb 

# Install Winetricks
RUN apt-get install -y cabextract
RUN wget https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks
RUN chmod +x winetricks
RUN cp winetricks /usr/local/bin

# Install Visual C++ Redistributable 
RUN wineboot -u && xvfb-run winetricks -q vcrun2015

# Install pip
RUN apt-get install -y python3-pip

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install Panel and other libraries used by the TideGates app
COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt

# COPY . /home/$USERNAME
# RUN chown -R $USERNAME /home/$USERNAME

USER $USERNAME
WORKDIR /home/$USERNAME/tidegates

CMD ["python3", "tidegates/main.py"]
