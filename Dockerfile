FROM docker-remote.bart.sec.samsung.net/python:3.13.13

COPY ./cosmo-da-backend /home/work/cosmo-da-backend
COPY ./config.yaml /home/work/cosmo-da-backend/config.yaml

WORKDIR /home/work/cosmo-da-backend
RUN python -m pip install -r requirements_py313_prod.txt --no-cache-dir

CMD ["python", "-m", "data_agent", "-c", "/home/work/cosmo-da-backend/config.yaml"]




FROM docker-remote.bart.sec.samsung.net/python:3.13.13

COPY ./cosmo-milvus-mcp-server /home/work/cosmo-milvus-mcp-server
COPY ./config.yaml /home/work/cosmo-milvus-mcp-server/config.yaml

WORKDIR /home/work/cosmo-milvus-mcp-server
RUN python -m pip install -r requirements_py313_prod.txt --no-cache-dir

CMD ["python", "-m", "milvus_mcp", "-c", "/home/work/cosmo-milvus-mcp-server/config.yaml"]

