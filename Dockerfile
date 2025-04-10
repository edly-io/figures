FROM circleci/python:3.8
ENV BASH_ENV=~/.bashrc

WORKDIR ~/circleci-figures
COPY . ./

RUN pip install --upgrade pip
RUN pip install virtualenv

RUN virtualenv venv
RUN . venv/bin/activate
RUN pip install -r devsite/requirements/py35_juniper.txt

ENTRYPOINT ["/bin/bash"]
