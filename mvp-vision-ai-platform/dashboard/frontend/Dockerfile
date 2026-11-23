ARG REGISTRY_MIRROR=
FROM ${REGISTRY_MIRROR}node:20-alpine AS deps

WORKDIR /app
COPY dashboard/frontend/package.json dashboard/frontend/package-lock.json ./
RUN npm ci

FROM ${REGISTRY_MIRROR}node:20-alpine AS builder

WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
ARG NEXT_PUBLIC_BASE_PATH=/dashboard
ARG NEXT_PUBLIC_AUTH_BASE_URL=
ARG NEXT_PUBLIC_ACTIVATION_API_URL=/activation/dashboard
ARG NEXT_PUBLIC_USER_API_URL=/user/api/v1
ARG NEXT_PUBLIC_PLATFORM_API_URL=/platform/api/v1
ARG NEXT_PUBLIC_LABELER_API_URL=/labeler/api/v1
ARG NEXT_PUBLIC_DASHBOARD_API_URL=/dashboard/api/v1
ARG NEXT_PUBLIC_SITE_URL=
ARG NEXT_PUBLIC_LABELER_URL=
ARG NEXT_PUBLIC_TRAINER_URL=
ARG NEXT_PUBLIC_RUNNER_URL=
ARG NEXT_PUBLIC_DEFECT_URL=
ARG NEXT_PUBLIC_DOCS_URL=
ARG NEXT_PUBLIC_DOWNLOAD_URL=
ARG BUILD_DATE
ARG VERSION
ENV NEXT_PUBLIC_BASE_PATH=${NEXT_PUBLIC_BASE_PATH} \
    NEXT_PUBLIC_AUTH_BASE_URL=${NEXT_PUBLIC_AUTH_BASE_URL} \
    NEXT_PUBLIC_ACTIVATION_API_URL=${NEXT_PUBLIC_ACTIVATION_API_URL} \
    NEXT_PUBLIC_USER_API_URL=${NEXT_PUBLIC_USER_API_URL} \
    NEXT_PUBLIC_PLATFORM_API_URL=${NEXT_PUBLIC_PLATFORM_API_URL} \
    NEXT_PUBLIC_LABELER_API_URL=${NEXT_PUBLIC_LABELER_API_URL} \
    NEXT_PUBLIC_DASHBOARD_API_URL=${NEXT_PUBLIC_DASHBOARD_API_URL} \
    NEXT_PUBLIC_SITE_URL=${NEXT_PUBLIC_SITE_URL} \
    NEXT_PUBLIC_LABELER_URL=${NEXT_PUBLIC_LABELER_URL} \
    NEXT_PUBLIC_TRAINER_URL=${NEXT_PUBLIC_TRAINER_URL} \
    NEXT_PUBLIC_RUNNER_URL=${NEXT_PUBLIC_RUNNER_URL} \
    NEXT_PUBLIC_DEFECT_URL=${NEXT_PUBLIC_DEFECT_URL} \
    NEXT_PUBLIC_DOCS_URL=${NEXT_PUBLIC_DOCS_URL} \
    NEXT_PUBLIC_DOWNLOAD_URL=${NEXT_PUBLIC_DOWNLOAD_URL}
COPY --from=deps /app/node_modules ./node_modules
COPY dashboard/frontend/package.json dashboard/frontend/tsconfig.json dashboard/frontend/next.config.mjs ./
COPY dashboard/frontend/tailwind.config.ts dashboard/frontend/postcss.config.js ./
COPY dashboard/frontend/app ./app
COPY dashboard/frontend/components ./components
COPY dashboard/frontend/lib ./lib
COPY dashboard/frontend/public ./public
RUN npm run build

FROM ${REGISTRY_MIRROR}node:20-alpine AS runner

ARG BUILD_DATE
ARG VERSION
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3021 \
    HOSTNAME=0.0.0.0
LABEL org.opencontainers.image.created=${BUILD_DATE} \
      org.opencontainers.image.version=${VERSION}

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3021
CMD ["node", "server.js"]
