FROM node:20-alpine AS builder

WORKDIR /app
RUN npm install -g pnpm

# Copy workspace config and lockfile
COPY pnpm-workspace.yaml package.json tsconfig.base.json pnpm-lock.yaml ./

# Copy package.jsons for dependency installation
COPY packages/types/package.json ./packages/types/
COPY apps/web/package.json ./apps/web/

# Install all dependencies
RUN pnpm install --frozen-lockfile

# Copy source
COPY packages/types/ ./packages/types/
COPY apps/web/ ./apps/web/

# Build Next.js with standalone output
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm --filter @sentinel/web build

# Production image
FROM node:20-alpine

WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=builder /app/apps/web/.next/standalone ./
COPY --from=builder /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder /app/apps/web/public ./apps/web/public

EXPOSE 3000
CMD ["node", "apps/web/server.js"]
