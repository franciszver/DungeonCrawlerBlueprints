# Dockerfile for RefineFunction with OpenCV support
# This is an optional upgrade for maximum edge detection accuracy
# Default deployment uses PIL-based lightweight solution (no container needed)

FROM public.ecr.aws/lambda/python:3.13

# Install system dependencies for OpenCV
RUN yum install -y gcc gcc-c++ && \
    yum clean all && \
    rm -rf /var/cache/yum

# Install Python dependencies for edge detection
RUN pip install --no-cache-dir \
    opencv-python-headless>=4.12.0 \
    numpy>=2.2.6 \
    Pillow>=12.0.0

# Copy handler code
COPY functions/refine/ ${LAMBDA_TASK_ROOT}/functions/refine/
COPY shared/ ${LAMBDA_TASK_ROOT}/shared/

# Set handler function
CMD [ "functions.refine.handler.lambda_handler" ]

