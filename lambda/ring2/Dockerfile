FROM public.ecr.aws/lambda/python:3.12

# Install dependencies (lighter than Ring 1 — no image processing)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy arbiter modules from mcp_server
COPY mcp_server/verification/ ${LAMBDA_TASK_ROOT}/verification/
COPY mcp_server/supabase_client.py ${LAMBDA_TASK_ROOT}/
COPY mcp_server/config/ ${LAMBDA_TASK_ROOT}/config/

# Copy Lambda handler
COPY lambda/ring2/handler.py ${LAMBDA_TASK_ROOT}/

CMD ["handler.lambda_handler"]
