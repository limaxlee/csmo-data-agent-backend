# Production static server for the Defect Studio SPA.
#
# VITE_* values are baked into the bundle at build time — build the image for
# the target environment with:
#   --build-arg VITE_BASE_PATH=/defect/
#   --build-arg VITE_AGENT_API_URL=/defect
#   --build-arg VITE_AUTH_BASE_URL=/auth
ARG NODE_IMAGE=node:22-slim
ARG NGINX_IMAGE=nginx:1.27-alpine

FROM ${NODE_IMAGE} AS build

WORKDIR /repo

# Trust the Samsung corporate CA chain (proxy-internal registries).
COPY build-ca/*.crt /usr/local/share/ca-certificates/
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && update-ca-certificates

ENV NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt

# Optional internal npm registry (build-time only credentials, e.g. the
# corporate desktop network where registry.npmjs.org is proxied/blocked).
# Leave empty on CI runners with normal npm access.
ARG NPM_REGISTRY=
ARG NPM_AUTH=
ENV COREPACK_NPM_REGISTRY=${NPM_REGISTRY}
RUN if [ -n "$NPM_REGISTRY" ]; then \
      npm config set registry "$NPM_REGISTRY"; \
      echo "_auth=$NPM_AUTH" >> ~/.npmrc; \
    fi

RUN corepack enable

COPY pnpm-lock.yaml pnpm-workspace.yaml package.json ./
COPY packages ./packages
COPY web/frontend/package.json web/frontend/package.json

# Install only what the frontend build needs (frontend + its workspace deps).
RUN pnpm install --frozen-lockfile --filter defect-studio-frontend...

COPY packages ./packages
COPY web/frontend ./web/frontend

ARG VITE_BASE_PATH=/defect/
ARG VITE_AGENT_API_URL=/defect
ARG VITE_AUTH_BASE_URL=/auth
# Deployment identity selects production automatic SSO, not feature availability.
ARG VITE_DEPLOYMENT_ENV=production

ENV VITE_BASE_PATH=${VITE_BASE_PATH} \
    VITE_AGENT_API_URL=${VITE_AGENT_API_URL} \
    VITE_AUTH_BASE_URL=${VITE_AUTH_BASE_URL} \
    VITE_DEPLOYMENT_ENV=${VITE_DEPLOYMENT_ENV}

RUN pnpm --filter defect-studio-frontend build

ARG NGINX_IMAGE=nginx:1.27-alpine
FROM ${NGINX_IMAGE}

COPY --from=build /repo/web/frontend/dist /usr/share/nginx/html/defect
COPY web/frontend/nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
