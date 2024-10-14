# Use the official Python 3.11 image as the base image
FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu20.04

ENV DEBIAN_FRONTEND=noninteractive

# Add the deadsnakes PPA and install Python 3.11
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && add-apt-repository -y ppa:savoury1/ffmpeg4 \
    && apt-get update && apt-get install -y \
    python3.11 \
    python3.11-distutils \
    libgl1-mesa-dev \
    libglib2.0-0 \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install pip for Python 3.11
# TODO: Specify which version of pip we are going to use
RUN wget https://bootstrap.pypa.io/get-pip.py \
    && python3.11 get-pip.py \
    && rm get-pip.py

RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Install ffmpeg for whisper_timestamped
RUN apt-get update && apt-get install -y ffmpeg

# Set the working directory to /app
WORKDIR /app

COPY src/requirements.txt .

# Install the Python dependencies
RUN python3.11 -m pip install -r requirements.txt

# Intergate shared dependencies
COPY shared .

# Copy the source code into the container
COPY src .

# Load the whisper models
RUN python3.11 src/models_loader.py

CMD ["python3.11", "src/main.py"]