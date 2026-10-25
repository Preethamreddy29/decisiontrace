FROM python:3.12-slim

WORKDIR /workspace
COPY api/requirements.txt /workspace/api/requirements.txt
RUN pip install --no-cache-dir -r /workspace/api/requirements.txt \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home app

COPY api /workspace/api
COPY corpus /workspace/corpus
COPY tools/eval_demo.py /workspace/tools/eval_demo.py
COPY tools/eval_v02.py /workspace/tools/eval_v02.py
COPY tools/eval_v03.py /workspace/tools/eval_v03.py
COPY tools/eval_v04.py /workspace/tools/eval_v04.py
USER app

CMD ["uvicorn", "api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
