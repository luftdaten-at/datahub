FROM python:3-alpine

# add additional packages which are not in alpine
RUN apk add gcc musl-dev libffi-dev

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PIP_DISABLE_PIP_VERSION_CHECK 1

# Set work directory
WORKDIR /code

# Install dependencies
COPY ./code/requirements.txt .
RUN pip install -r requirements.txt

# Copy project
#COPY ./code/ .