FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
# 네트워크 변동(ECONNRESET 등)에 대비해 재시도·타임아웃을 넉넉히 둔다.
RUN npm install --fetch-retries=5 --fetch-retry-mintimeout=20000 --fetch-retry-maxtimeout=120000 --fetch-timeout=300000

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]