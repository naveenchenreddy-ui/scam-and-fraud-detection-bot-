FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY frontend/package.json frontend/package-lock.json ./

# Install dependencies
RUN npm install

# Copy frontend code
COPY frontend/ .

# Expose port
EXPOSE 3000

# Run dev server on port 3000 and bind to all interfaces
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
