FROM node:18-alpine

WORKDIR /app

# Copy package files and install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy application source
COPY . .

# Expose port
EXPOSE 3000

# Start development server
CMD ["npm", "start"]
