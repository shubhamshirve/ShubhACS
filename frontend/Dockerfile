# ─────────────────────────────────────────────────────────────
# Stage 1: Build React app with pnpm (fast, disk-efficient)
# ─────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

# Install pnpm globally
RUN npm install -g pnpm

WORKDIR /app

# Copy manifests first for cache optimisation
COPY package.json ./
# Use pnpm-lock.yaml if it exists, otherwise fallback to yarn.lock
RUN if [ -f pnpm-lock.yaml ]; then \
        pnpm install --frozen-lockfile; \
    elif [ -f yarn.lock ]; then \
        pnpm import && pnpm install --frozen-lockfile; \
    else \
        pnpm install; \
    fi

COPY . .

# Build arg for backend URL (empty = relative URLs via Caddy proxy)
ARG REACT_APP_BACKEND_URL=""
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL

# Disable CRA telemetry
ENV DISABLE_ESLINT_PLUGIN=true CI=false

RUN pnpm build

# ─────────────────────────────────────────────────────────────
# Stage 2: Serve with Caddy (tiny, fast, automatic HTTPS)
# ─────────────────────────────────────────────────────────────
FROM caddy:2-alpine

COPY --from=builder /app/build /srv
COPY Caddyfile /etc/caddy/Caddyfile

EXPOSE 80 443
