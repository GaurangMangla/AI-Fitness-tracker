# ── Stage 1: Dependency installer ─────────────────────────────────────────
FROM node:20-alpine AS deps

WORKDIR /app

# Copy only manifests first for layer caching
COPY package.json package-lock.json ./

# ci installs exact versions from the lockfile — reproducible builds
RUN npm ci


# ── Stage 2: Builder ──────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copy installed node_modules from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy full source
COPY . .

# NEXT_PUBLIC_* vars must be available at BUILD TIME (they're inlined into
# the JS bundle by Next.js). Pass as build args so the image stays
# configurable without baking in a fixed URL.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Enable standalone output for minimal runtime image
ENV NEXT_STANDALONE=true

# Build the Next.js application
RUN npm run build


# ── Stage 3: Production runner ────────────────────────────────────────────
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
# Disable Next.js telemetry in the container
ENV NEXT_TELEMETRY_DISABLED=1

# Security: non-root user
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# Standalone output structure:
#   .next/standalone/ — minimal server + only required dependencies
#   .next/static/     — compiled static assets (CSS, JS chunks)
#   public/           — public static files (images, fonts, etc.)
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Health check — polls the Next.js root page
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget -qO- http://localhost:3000/ > /dev/null || exit 1

# next/standalone ships its own server.js — no `next start` needed
CMD ["node", "server.js"]
