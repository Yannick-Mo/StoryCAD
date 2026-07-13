FROM node:20.18-alpine AS base

WORKDIR /app

RUN addgroup --system --gid 1001 appuser && adduser --system --uid 1001 appuser

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

COPY package.json ./
RUN npm install --legacy-peer-deps && npm cache clean --force

COPY . .

RUN chown -R appuser:appuser /app

EXPOSE 5173

USER appuser

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
