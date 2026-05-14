# Stage 1: Build React app
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json ./
RUN yarn install --network-timeout 300000

COPY . .

# Empty string → relative URLs → nginx proxy handles /api routing
ARG REACT_APP_BACKEND_URL=""
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL
ENV GENERATE_SOURCEMAP=false
ENV NODE_ENV=production

RUN yarn build

# Stage 2: Serve with nginx
FROM nginx:1.25-alpine

COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
