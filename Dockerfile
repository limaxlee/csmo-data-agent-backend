FROM docker-remote.bart.sec.samsung.net/python:3.13.13

COPY ./cosmo-data-agent-backend /home/work/cosmo-data-agent-backend
COPY ./config.yaml /home/work/cosmo-data-agent-backend/config.yaml

WORKDIR /home/work/cosmo-data-agent-backend
RUN python -m pip install -r requirements_py313_prod.txt --no-cache-dir

CMD ["python", "-m", "data_agent", "-c", "/home/work/cosmo-data-agent-backend/config.yaml"]
