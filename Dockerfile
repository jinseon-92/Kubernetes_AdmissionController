FROM python:3.8

COPY requirements.txt /
RUN pip install -r requirements.txt

ADD test.py .
ADD server.key .
ADD server.crt .
ADD ca.crt .


CMD ["python", "-u", "test.py"]
