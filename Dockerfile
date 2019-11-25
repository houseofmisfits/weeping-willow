FROM python:3

WORKDIR /usr/src/app

ENV TZ='America/New_York'

COPY . .
RUN ["python", "setup.py", "build"]
RUN ["python", "setup.py", "install"]
RUN ["python", "setup.py", "test"]

ENTRYPOINT ["python", "willow.py"]
CMD "run"