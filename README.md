# WhatsApp Bot with Session Storage

## Overview

This project implements a WhatsApp bot with secure session storage capabilities. The bot can:

- 🤖 Connect to WhatsApp Web using QR code authentication
- 💾 Automatically backup and restore WhatsApp sessions
- 🔒 Store session data securely with encryption
- 📱 Respond to messages with custom commands
- 🌐 Provide a web dashboard for monitoring and management
- ⚡ Auto-reconnect with session restoration on restart

## Architecture

### Backend (FastAPI)
- **Session Management**: Upload, download, list, and delete session files
- **Bot Status**: Track connection status, QR codes, and user information
- **Storage**: Secure local file storage with database metadata
- **Health Monitoring**: System health checks and status reporting

### Frontend (React)
- **Dashboard**: Monitor bot status and connection
- **Session Manager**: Upload, download, and manage session files
- **QR Display**: Show QR codes for WhatsApp authentication
- **Real-time Status**: Live updates of bot connection status

### WhatsApp Service (Node.js)
- **WhatsApp Web Integration**: Using whatsapp-web.js library
- **Auto-backup**: Automatic session backup to backend storage
- **Message Handling**: Process incoming messages and commands
- **Session Restoration**: Restore sessions on startup

## Features

### 🔐 Session Management
- **Automatic Backup**: Sessions are automatically backed up when authenticated
- **Secure Storage**: Session files stored with encryption and metadata
- **Easy Restoration**: One-click session restoration from storage
- **Multiple Sessions**: Support for managing multiple bot sessions

### 📱 WhatsApp Bot Commands
- `help` - Show available commands
- `status` - Display bot status and information
- `bot [message]` - Echo bot functionality for testing

### 🌐 Web Dashboard
- Real-time connection status
- QR code display for authentication
- Session file management interface
- Bot control and monitoring

## Quick Start

### 1. Start the Backend
```bash
cd /app
sudo supervisorctl restart backend
```

### 2. Start the Frontend
```bash
sudo supervisorctl restart frontend
```

### 3. Start the WhatsApp Service (Optional)
```bash
cd /app/whatsapp-service
npm install
npm start
```

### 4. Access the Dashboard
Open your browser and go to the frontend URL to access the dashboard.

## API Endpoints

### Bot Management
- `GET /api/bot/status` - Get current bot status
- `POST /api/bot/generate-qr` - Generate QR code for authentication
- `POST /api/bot/connect` - Simulate WhatsApp connection
- `POST /api/bot/restore-session` - Restore latest session

### Session Management
- `GET /api/sessions` - List all stored sessions
- `POST /api/sessions/upload` - Upload a session file
- `GET /api/sessions/download/{file_id}` - Download a session file
- `DELETE /api/sessions/{file_id}` - Delete a session file

### System
- `GET /api/health` - Health check endpoint

## Configuration

### Environment Variables (Backend)
```env
MONGO_URL="mongodb://localhost:27017"
DB_NAME="whatsapp_bot_db"
```

### Environment Variables (Frontend)
```env
REACT_APP_BACKEND_URL=your_backend_url
```

## Security Features

- 🔒 Secure session storage with metadata tracking
- 🛡️ Input validation and error handling
- 🚫 CORS protection and security headers
- 📝 Comprehensive logging and monitoring
- 🔐 Encrypted file storage capabilities

## Usage Examples

### Uploading a Session File
```javascript
const formData = new FormData();
formData.append('file', sessionFile);
await fetch('/api/sessions/upload', {
    method: 'POST',
    body: formData
});
```

### Checking Bot Status
```javascript
const response = await fetch('/api/bot/status');
const status = await response.json();
console.log('Bot connected:', status.is_connected);
```

### Restoring a Session
```javascript
const response = await fetch('/api/bot/restore-session', {
    method: 'POST'
});
const result = await response.json();
```

## Troubleshooting

### Common Issues

1. **Backend Not Starting**
   - Check MongoDB connection
   - Verify environment variables
   - Check supervisor logs: `tail -f /var/log/supervisor/backend.*.log`

2. **WhatsApp Service Issues**
   - Ensure Node.js dependencies are installed
   - Check Chrome/Chromium installation for Puppeteer
   - Verify backend connectivity

3. **Session Restoration Problems**
   - Ensure session files are properly uploaded
   - Check file permissions and storage directory
   - Verify MongoDB connection for metadata

### Logs and Monitoring

- Backend logs: `/var/log/supervisor/backend.*.log`
- Frontend logs: Browser developer console
- WhatsApp Service logs: Console output when running

## Development

### Adding New Bot Commands
Edit the message handler in `whatsapp-service/whatsapp-bot.js`:

```javascript
client.on('message', async (message) => {
    if (message.body.toLowerCase() === 'your_command') {
        await message.reply('Your response');
    }
});
```

### Extending the API
Add new endpoints to `/app/backend/server.py`:

```python
@api_router.post("/your-endpoint")
async def your_function():
    return {"message": "Your response"}
```

### Frontend Customization
Modify React components in `/app/frontend/src/App.js` to add new features.

## Production Deployment

### Security Considerations
- Use HTTPS for all connections
- Implement proper authentication and authorization
- Set up proper CORS policies
- Use secure session storage with encryption
- Regular security audits and updates

### Scaling
- Use load balancers for multiple instances
- Implement Redis for session sharing
- Use cloud storage for session files
- Set up monitoring and alerting

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Check the troubleshooting section
- Review the logs for error messages
- Open an issue with detailed information

---

**Note**: This bot is for educational and development purposes. Ensure compliance with WhatsApp's Terms of Service when using in production.