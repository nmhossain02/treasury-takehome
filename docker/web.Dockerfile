FROM node:22-alpine AS build
RUN corepack enable
WORKDIR /workspace
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/package.json
RUN pnpm install --frozen-lockfile
COPY fixtures/demo ./fixtures/demo
COPY apps/web ./apps/web
RUN pnpm web:build

FROM caddy:2.10-alpine
# The upstream binary can bind privileged ports. This image only listens on
# 8080, so remove that file capability to support cap_drop: ALL safely.
RUN setcap -r /usr/bin/caddy
COPY docker/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /workspace/apps/web/dist /srv
EXPOSE 8080
