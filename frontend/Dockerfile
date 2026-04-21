FROM node:22-alpine

WORKDIR /app

# Install deps first for better caching.
COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev"]
