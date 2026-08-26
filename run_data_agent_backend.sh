docker run --name da_backend -d --rm --network da_backend -p 18080:18080 -v /home/cosmo/projects/da-backend/logs:/home/work/cosmo-da-backend/logs da-backend:0.0.1

docker run --name milvus_mcp_server -d --rm --network milvus_mcp_server -p 10422:10422 -v /home/cosmo/projects/milvus-mcp-server/logs:/home/work/cosmo-milvus-mcp-server/logs milvus-mcp-server:0.0.1
