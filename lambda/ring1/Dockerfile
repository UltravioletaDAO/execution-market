FROM public.ecr.aws/lambda/python:3.12

# Build-time version metadata (injected by CI)
ARG GIT_SHA=unknown
ARG BUILD_TIMESTAMP=unknown
ENV GIT_SHA=${GIT_SHA} \
    BUILD_TIMESTAMP=${BUILD_TIMESTAMP}

# Install dependencies
COPY lambda/ring1/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy verification modules from mcp_server
COPY mcp_server/verification/ ${LAMBDA_TASK_ROOT}/verification/
COPY mcp_server/supabase_client.py ${LAMBDA_TASK_ROOT}/
COPY mcp_server/config/ ${LAMBDA_TASK_ROOT}/config/

# Copy Lambda handler + helpers
COPY lambda/ring1/handler.py ${LAMBDA_TASK_ROOT}/
COPY lambda/ring1/supabase_helper.py ${LAMBDA_TASK_ROOT}/

CMD ["handler.lambda_handler"]
