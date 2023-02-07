FROM public.ecr.aws/lambda/python:3.8
COPY requirements.txt ./
RUN yum update -y && \
  pip install -r requirements.txt
COPY app.py ${LAMBDA_TASK_ROOT}
CMD [ "app.lambda_handler" ]