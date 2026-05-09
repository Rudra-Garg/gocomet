FROM node:22-slim AS deps

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --legacy-peer-deps

FROM node:22-slim AS dev

WORKDIR /app/frontend
ENV PATH="/app/frontend/node_modules/.bin:$PATH"

COPY --from=deps /app/frontend/node_modules ./node_modules
COPY frontend/ ./

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--port", "5173"]
