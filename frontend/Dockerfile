# Dashboard di F1 Data Platform. Contesto di build: la cartella frontend/.
#   docker build -t f1-frontend frontend/

# ---- Build: installazione pulita, test del componente, dist/ ----
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY scripts ./scripts
COPY src ./src
COPY test ./test
# `npm test` esegue prima la build (pretest): se un test fallisce l'immagine non si crea.
RUN npm test && npm run build

# ---- Esecuzione: solo Node, il server e dist/ (nessuna dipendenza npm) ----
FROM node:22-alpine
ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=3000 \
    API_TARGET=http://backend:8080
WORKDIR /app
COPY --from=build /app/package.json ./
COPY --from=build /app/scripts/server.mjs /app/scripts/serve.mjs ./scripts/
COPY --from=build /app/dist ./dist
USER node
EXPOSE 3000
HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=12 \
  CMD wget -q -O /dev/null http://127.0.0.1:3000/ || exit 1
CMD ["node", "scripts/serve.mjs"]
