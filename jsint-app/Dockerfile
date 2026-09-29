FROM node:24-alpine AS builder

WORKDIR /app

RUN apk add --no-cache python3 make g++

COPY package.json yarn.lock ./

RUN yarn install --network-timeout 100000

COPY . .

# The TanStack Router tree is committed, but it must match src/routes — a new
# route file is invisible to the app until it is regenerated, so generate it
# here rather than shipping whatever the last local run produced. The local
# binary is called directly: `npx` would try to resolve `tsr` from the registry.
RUN ./node_modules/.bin/tsr generate

# API URL baked at build time. Empty = same-origin relative URLs (/api/...),
# served through the nginx reverse proxy below. Only override for an external API origin.
ARG VITE_API_URL=""
ENV VITE_API_URL=${VITE_API_URL}

# Optional: repository URL used by the in-app GitHub/Support links.
ARG VITE_REPO_URL=""
ENV VITE_REPO_URL=${VITE_REPO_URL}

RUN yarn build

FROM nginx:1.29-alpine AS production

LABEL org.opencontainers.image.description="Jsint Frontend"
LABEL org.opencontainers.image.licenses="Apache-2.0"

RUN addgroup -g 1001 -S jsint && \
    adduser -u 1001 -S jsint -G jsint && \
    # Set ownership for nginx html directory
    chown -R jsint:jsint /usr/share/nginx/html && \
    # Remove default config
    rm -f /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/nginx.conf

COPY --from=builder --chown=jsint:jsint /app/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:8080/health || exit 1

USER jsint

CMD ["nginx", "-g", "daemon off;"]
