FROM python:3.12-alpine

# add additional packages which are not in alpine
RUN apk add --no-cache gcc musl-dev libffi-dev tzdata gettext

# Set timezone
ENV TZ=Europe/Vienna

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /usr/src/app

# Install dependencies
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
#COPY ./app/ .