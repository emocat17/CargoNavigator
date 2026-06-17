# ── Build stage ──
FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# ── Serve stage: Nginx + SPA ──
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html

# SPA fallback: all routes → index.html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 16789
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost:16789/ || exit 1
