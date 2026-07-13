FROM node:22-alpine

WORKDIR /app

COPY certs /usr/local/share/ca-certificates/local-certs
ENV NODE_EXTRA_CA_CERTS=/usr/local/share/ca-certificates/local-certs/local-avg-webmail-shield-root.crt

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
