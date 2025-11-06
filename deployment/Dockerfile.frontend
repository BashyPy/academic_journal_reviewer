# Multi-stage build for AARIS Frontend
# Stage 1: Builder
FROM node:18-alpine AS builder

WORKDIR /build

# Copy package files
COPY frontend/package.json frontend/package-lock.json ./

# Install dependencies
RUN npm install --only=production && \
    npm cache clean --force

# Copy source code
COPY frontend/ .

# Build production bundle
RUN npm run build

# Stage 2: Production with Nginx
FROM nginx:1.25-alpine

# Security: Remove default nginx config
RUN rm -rf /etc/nginx/conf.d/* /usr/share/nginx/html/*

# Copy custom nginx config
COPY deployment/nginx-frontend.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder
COPY --from=builder /build/build /usr/share/nginx/html

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD wget --quiet --tries=1 --spider http://localhost:3000/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
