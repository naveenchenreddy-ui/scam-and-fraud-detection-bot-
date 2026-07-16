# 📖 Detailed Setup Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Windows Setup](#windows-setup)
3. [macOS Setup](#macos-setup)
4. [Linux Setup](#linux-setup)
5. [Docker Setup](#docker-setup)
6. [Twilio Configuration](#twilio-configuration)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software
- **Python 3.11+** - Download from https://www.python.org
- **Node.js 18+** - Download from https://nodejs.org
- **MongoDB 7.0+** - Download from https://www.mongodb.com/try/download/community
- **Git** (optional) - Download from https://git-scm.com

### Twilio Account
- Free Twilio account from https://www.twilio.com
- WhatsApp Sandbox setup
- Account SID and Auth Token

---

## Windows Setup

### Step 1: Install Python

1. Download Python from https://www.python.org/downloads/
2. Run the installer
3. **IMPORTANT**: Check "Add Python to PATH"
4. Click "Install Now"
5. Verify installation:
   ```cmd
   python --version
   pip --version
   ```

### Step 2: Install Node.js

1. Download from https://nodejs.org (LTS version)
2. Run the installer
3. Accept default options
4. Verify installation:
   ```cmd
   node --version
   npm --version
   ```

### Step 3: Install MongoDB

1. Download from https://www.mongodb.com/try/download/community
2. Run the MongoDB installer
3. Choose "Complete" installation
4. Check "Install MongoD as a Service"
5. Start MongoDB service

### Step 4: Setup Project

1. Extract project files to a folder
2. Open Command Prompt (cmd) in project root
3. Run the startup script:
   ```cmd
   start.bat
   ```

This will automatically:
- Create Python virtual environment
- Install all dependencies
- Start FastAPI server
- Start React development server

### Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## macOS Setup

### Step 1: Install Python

Using Homebrew (recommended):
```bash
brew install python@3.11
python3 --version
```

Or download from https://www.python.org

### Step 2: Install Node.js

Using Homebrew:
```bash
brew install node
node --version
npm --version
```

Or download from https://nodejs.org

### Step 3: Install MongoDB

Using Homebrew:
```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

Or download from https://www.mongodb.com

### Step 4: Setup Project

```bash
# Navigate to project directory
cd path/to/whatsapp-nlp-bot

# Make startup script executable
chmod +x start.sh

# Run startup script
./start.sh
```

The script will guide you through setup and start all services.

---

## Linux Setup

### Step 1: Install Python

Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv python3-pip
python3 --version
```

Fedora:
```bash
sudo dnf install python3.11 python3-pip
python3 --version
```

### Step 2: Install Node.js

Ubuntu/Debian:
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
node --version
```

Or using NVM:
```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
node --version
```

### Step 3: Install MongoDB

Ubuntu/Debian:
```bash
sudo apt-get install -y mongodb
sudo systemctl start mongodb
sudo systemctl enable mongodb
```

Fedora:
```bash
sudo dnf install mongodb-server
sudo systemctl start mongod
sudo systemctl enable mongod
```

### Step 4: Setup Project

```bash
# Navigate to project
cd path/to/whatsapp-nlp-bot

# Make script executable
chmod +x start.sh

# Run startup script
./start.sh
```

---

## Docker Setup

### Prerequisites
- Docker Desktop from https://www.docker.com/products/docker-desktop
- Docker Compose (included with Docker Desktop)

### Steps

1. **Create .env file in project root:**
   ```bash
   cp backend/.env.example backend/.env
   ```

2. **Edit .env with Twilio credentials:**
   ```env
   TWILIO_ACCOUNT_SID=your_account_sid
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_WHATSAPP_NUMBER=+1234567890
   ```

3. **Build and start containers:**
   ```bash
   docker-compose up --build
   ```

4. **Access services:**
   - Frontend: http://localhost:3000
   - Backend: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - MongoDB: localhost:27017

5. **Stop services:**
   ```bash
   docker-compose down
   ```

---

## Twilio Configuration

### Step 1: Create Account

1. Go to https://www.twilio.com
2. Sign up for free account
3. Verify your email and phone number

### Step 2: Setup WhatsApp Sandbox

1. Go to Twilio Console
2. Navigate to: Messaging → Try it out → Send a WhatsApp message
3. You'll see a Twilio WhatsApp number (e.g., +14155238886)
4. To test locally, send the join code to the Twilio number via WhatsApp
   - Message: "join <code>"
   - Example: "join ancient-river"

### Step 3: Get Credentials

1. **Account SID:**
   - Go to Twilio Console main page
   - Copy your Account SID
   - Add to backend/.env

2. **Auth Token:**
   - Go to Twilio Console
   - Click "Show" next to Account SID
   - Copy your Auth Token
   - Add to backend/.env

3. **WhatsApp Number:**
   - From the sandbox setup
   - Add to backend/.env

### Step 4: Configure Webhook (Production)

1. Get your production server URL
2. Go to Twilio Console → Messaging → Whatsapp
3. Set webhook: `https://your-domain.com/api/messages/webhook`
4. Method: POST

### Example .env


```

---

## Troubleshooting

### Python Issues

**Error: "python: command not found"**
- Solution: Check Python is in PATH
- Windows: Reinstall Python with "Add to PATH" checked
- macOS/Linux: Use `python3` instead of `python`

**Error: "ModuleNotFoundError"**
- Solution: Ensure virtual environment is activated
- Windows: `venv\Scripts\activate.bat`
- macOS/Linux: `source venv/bin/activate`

### Node.js Issues

**Error: "npm: command not found"**
- Solution: Reinstall Node.js
- Verify with: `npm --version`

**Error: Module not found after npm install**
- Solution: Clear cache and reinstall
  ```bash
  rm -rf node_modules package-lock.json
  npm install
  ```

### MongoDB Issues

**Error: "MongoDB connection refused"**
- Solution: Start MongoDB
- Windows: Check Services → MongoDB Server
- macOS: `brew services start mongodb-community`
- Linux: `sudo systemctl start mongodb`

**Error: "cannot open shared object file"**
- Solution: Install MongoDB dependencies
- Ubuntu: `sudo apt-get install libssl1.1`

### FastAPI Issues

**Error: "Port 8000 already in use"**
- Solution: Kill process using port 8000
- Windows: `netstat -ano | findstr :8000`
- macOS/Linux: `lsof -i :8000`

**Error: "Uvicorn not found"**
- Solution: Install uvicorn
  ```bash
  pip install uvicorn[standard]
  ```

### React Issues

**Error: "Cannot find module"**
- Solution: Clear and reinstall dependencies
  ```bash
  rm -rf node_modules
  npm install
  ```

**Port 3000 already in use**
- Solution: Use different port
  ```bash
  npm run dev -- --port 3001
  ```

### API Connection Issues

**Frontend can't connect to backend**
1. Check backend is running: http://localhost:8000/health
2. Check VITE_API_URL in frontend/.env
3. Check CORS settings in backend/main.py
4. Clear browser cache and cookies

**WebSocket connection fails**
- Currently uses HTTP polling, not WebSockets
- Check network connectivity

---

## Next Steps

1. ✅ Setup complete!
2. 📖 Read README.md for full documentation
3. 🧪 Test with API docs: http://localhost:8000/docs
4. 🚀 Deploy to production when ready

---

## Support

- Check GitHub Issues
- Review API documentation at http://localhost:8000/docs
- Check logs: backend.log and frontend.log

## Need Help?

1. **Backend Issues** → Check FastAPI logs
2. **Frontend Issues** → Check browser console
3. **Database Issues** → Check MongoDB logs
4. **Integration Issues** → Check Twilio logs

Happy coding! 🎉
