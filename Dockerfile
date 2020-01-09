FROM python:3.8-alpine

WORKDIR /usr/src/app

RUN ["apk", "update"]
RUN ["apk", "add", "--no-cache", "--virtual", ".pynacl_deps", "build-base", "python3-dev", "libffi-dev"]

ENV TZ='America/New_York'

COPY . .
RUN ["python", "setup.py", "build"]
RUN ["python", "setup.py", "install"]
RUN ["python", "setup.py", "test"]

RUN ["apk", "del", ".pynacl_deps"]

ENTRYPOINT ["python", "-m", "houseofmisfits.weeping_willow"]
CMD "run"