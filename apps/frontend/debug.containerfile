FROM docker.io/library/node:24-bookworm-slim

WORKDIR /app

EXPOSE 8080

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "8080"]
