# syntax=docker/dockerfile:1.6

# ─── deps stage ────────────────────────────────────────────────────────────────
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
# Dùng `npm install` vì lockfile có thể chưa tồn tại lần đầu;
# CI sẽ commit lockfile sau lần build đầu tiên.
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# ─── build stage ───────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ─── runtime stage (standalone output) ─────────────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
 && adduser  --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
# Tạo public/ rỗng để Next.js standalone server không fail nếu chưa có asset.
RUN mkdir -p ./public && chown -R nextjs:nodejs ./public

USER nextjs
EXPOSE 3000

CMD ["node", "server.js"]
