ARG REGISTRY_MIRROR=
FROM ${REGISTRY_MIRROR}node:20-alpine AS deps

# Runtime timestamps stay UTC; the frontend applies the selected display timezone.
ENV TZ=UTC

WORKDIR /app
COPY web-auth/package.json web-auth/package-lock.json* ./
RUN npm install

FROM ${REGISTRY_MIRROR}node:20-alpine AS builder

# Runtime timestamps stay UTC; the frontend applies the selected display timezone.
ENV TZ=UTC

WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY web-auth/ ./
RUN npm run build

FROM ${REGISTRY_MIRROR}node:20-alpine AS runner

# Runtime timestamps stay UTC; the frontend applies the selected display timezone.
ENV TZ=UTC

WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3020
ENV HOSTNAME=0.0.0.0
ENV NEXT_PUBLIC_BASE_PATH=/auth

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3020

CMD ["node", "server.js"]
