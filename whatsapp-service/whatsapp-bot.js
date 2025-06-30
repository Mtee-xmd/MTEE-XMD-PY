const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');
const cors = require('cors');
const axios = require('axios');
const fs = require('fs-extra');
const path = require('path');

// Configuration
const app = express();
const PORT = process.env.PORT || 3001;
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8001';

app.use(cors());
app.use(express.json());

// WhatsApp client setup
let client = null;
let qrCodeData = null;
let isConnected = false;
let currentUser = null;

// Session directory
const SESSION_DIR = path.join(__dirname, 'sessions');

// Initialize WhatsApp client
async function initializeWhatsApp() {
    try {
        console.log('Initializing WhatsApp client...');
        
        // Ensure session directory exists
        await fs.ensureDir(SESSION_DIR);
        
        client = new Client({
            authStrategy: new LocalAuth({
                clientId: "whatsapp-bot",
                dataPath: SESSION_DIR
            }),
            puppeteer: {
                headless: true,
                args: [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu'
                ]
            }
        });

        // QR Code generation
        client.on('qr', async (qr) => {
            console.log('QR Code received');
            qrCodeData = qr;
            qrcode.generate(qr, { small: true });
            
            // Update backend with QR code
            try {
                await axios.post(`${BACKEND_URL}/api/bot/status`, {
                    id: 'whatsapp-bot-1',
                    is_connected: false,
                    qr_code: qr,
                    last_seen: new Date().toISOString()
                });
            } catch (error) {
                console.error('Failed to update backend with QR code:', error.message);
            }
        });

        // Authentication
        client.on('authenticated', async () => {
            console.log('WhatsApp authenticated successfully');
            
            // Backup session to our backend
            await backupSession();
        });

        // Ready event
        client.on('ready', async () => {
            console.log('WhatsApp client is ready!');
            isConnected = true;
            currentUser = client.info;
            
            // Update backend status
            try {
                await axios.post(`${BACKEND_URL}/api/bot/status`, {
                    id: 'whatsapp-bot-1',
                    is_connected: true,
                    phone_number: currentUser.wid.user,
                    qr_code: null,
                    last_seen: new Date().toISOString()
                });
            } catch (error) {
                console.error('Failed to update backend status:', error.message);
            }
            
            console.log(`Connected as: ${currentUser.pushname} (${currentUser.wid.user})`);
        });

        // Message handling
        client.on('message', async (message) => {
            console.log(`Message from ${message.from}: ${message.body}`);
            
            // Simple echo bot for demonstration
            if (message.body.toLowerCase().startsWith('bot ')) {
                const response = `Echo: ${message.body.substring(4)}`;
                await message.reply(response);
            }
            
            // Help command
            if (message.body.toLowerCase() === 'help') {
                const helpText = `
🤖 WhatsApp Bot Commands:
• *bot [message]* - Echo your message
• *help* - Show this help
• *status* - Show bot status
                `;
                await message.reply(helpText);
            }
            
            // Status command
            if (message.body.toLowerCase() === 'status') {
                const statusText = `
📊 Bot Status:
• Connected: ✅ Yes
• Phone: ${currentUser?.wid?.user || 'Unknown'}
• Name: ${currentUser?.pushname || 'Unknown'}
• Session: Backed up securely
                `;
                await message.reply(statusText);
            }
        });

        // Disconnection handling
        client.on('disconnected', async (reason) => {
            console.log('WhatsApp client disconnected:', reason);
            isConnected = false;
            qrCodeData = null;
            currentUser = null;
            
            // Update backend status
            try {
                await axios.post(`${BACKEND_URL}/api/bot/status`, {
                    id: 'whatsapp-bot-1',
                    is_connected: false,
                    phone_number: null,
                    qr_code: null,
                    last_seen: new Date().toISOString()
                });
            } catch (error) {
                console.error('Failed to update backend status:', error.message);
            }
            
            // Attempt to reconnect after 5 seconds
            console.log('Attempting to reconnect in 5 seconds...');
            setTimeout(initializeWhatsApp, 5000);
        });

        // Initialize the client
        await client.initialize();
        
    } catch (error) {
        console.error('Failed to initialize WhatsApp client:', error);
        // Retry after 10 seconds
        setTimeout(initializeWhatsApp, 10000);
    }
}

// Backup session to backend
async function backupSession() {
    try {
        const sessionPath = path.join(SESSION_DIR, 'whatsapp-bot');
        
        if (await fs.pathExists(sessionPath)) {
            // Create a zip/tar of the session directory
            const sessionFiles = await fs.readdir(sessionPath, { recursive: true });
            
            // For simplicity, backup the main session file
            const sessionFile = path.join(sessionPath, 'session.json');
            
            if (await fs.pathExists(sessionFile)) {
                const sessionData = await fs.readFile(sessionFile);
                
                // Upload to backend
                const formData = new FormData();
                const blob = new Blob([sessionData], { type: 'application/json' });
                formData.append('file', blob, 'whatsapp_session.json');
                
                await axios.post(`${BACKEND_URL}/api/sessions/upload`, formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
                
                console.log('Session backed up successfully');
            }
        }
    } catch (error) {
        console.error('Failed to backup session:', error.message);
    }
}

// Restore session from backend
async function restoreSession() {
    try {
        const response = await axios.post(`${BACKEND_URL}/api/bot/restore-session`);
        
        if (response.data.success) {
            console.log(`Session restored: ${response.data.filename}`);
            return true;
        } else {
            console.log('No session to restore');
            return false;
        }
    } catch (error) {
        console.error('Failed to restore session:', error.message);
        return false;
    }
}

// API Routes
app.get('/status', (req, res) => {
    res.json({
        connected: isConnected,
        hasQR: !!qrCodeData,
        user: currentUser,
        timestamp: new Date().toISOString()
    });
});

app.get('/qr', (req, res) => {
    if (qrCodeData) {
        res.json({ qr: qrCodeData });
    } else {
        res.json({ qr: null, message: 'No QR code available' });
    }
});

app.post('/send', async (req, res) => {
    const { number, message } = req.body;
    
    if (!isConnected) {
        return res.status(503).json({ error: 'WhatsApp not connected' });
    }
    
    if (!number || !message) {
        return res.status(400).json({ error: 'Number and message required' });
    }
    
    try {
        const chatId = number.includes('@') ? number : `${number}@c.us`;
        await client.sendMessage(chatId, message);
        
        res.json({ success: true, message: 'Message sent successfully' });
    } catch (error) {
        console.error('Failed to send message:', error);
        res.status(500).json({ error: 'Failed to send message' });
    }
});

app.post('/restart', async (req, res) => {
    try {
        if (client) {
            await client.destroy();
        }
        
        // Restore session if available
        await restoreSession();
        
        // Reinitialize
        setTimeout(initializeWhatsApp, 2000);
        
        res.json({ success: true, message: 'WhatsApp client restarting' });
    } catch (error) {
        console.error('Failed to restart client:', error);
        res.status(500).json({ error: 'Failed to restart client' });
    }
});

// Health check
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        whatsapp_connected: isConnected,
        timestamp: new Date().toISOString()
    });
});

// Start the server
app.listen(PORT, () => {
    console.log(`WhatsApp service running on port ${PORT}`);
    console.log(`Backend URL: ${BACKEND_URL}`);
    
    // Try to restore session first, then initialize
    restoreSession().then(() => {
        setTimeout(initializeWhatsApp, 1000);
    });
});

// Graceful shutdown
process.on('SIGTERM', async () => {
    console.log('Shutting down gracefully...');
    
    if (client) {
        await backupSession();
        await client.destroy();
    }
    
    process.exit(0);
});

process.on('SIGINT', async () => {
    console.log('Shutting down gracefully...');
    
    if (client) {
        await backupSession();
        await client.destroy();
    }
    
    process.exit(0);
});