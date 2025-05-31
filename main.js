const { app, BrowserWindow, globalShortcut, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');

// Main window reference
let mainWindow = null;

function createWindow () {
  // Create main window
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    title: "Screen Text Translator",
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      enableRemoteModule: true
    },
    icon: path.join(__dirname, 'assets/icon.png')
  });

  // Load HTML file
  mainWindow.loadFile('index.html');
  
  // Remove menu bar
  mainWindow.setMenuBarVisibility(false);
  
  // Open developer tools (useful during development)
  // mainWindow.webContents.openDevTools();
  
  // Send notification when application is ready
  mainWindow.webContents.on('did-finish-load', () => {
    setTimeout(() => {
      mainWindow.webContents.send('app-ready');
    }, 500);
  });
  
  // Clear reference when window is closed
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Set shortcuts - this function will be replaced with registerGlobalShortcuts
function setupShortcuts() {
  // This function is no longer used - left in favor of registerGlobalShortcuts
  console.log("Using global shortcuts instead of window-focused shortcuts");
}

// Register global shortcuts (works without window focus)
function registerGlobalShortcuts() {
  // Clear all shortcuts first
  globalShortcut.unregisterAll();
  
  // Ctrl+Alt+T - Screen capture shortcut (Global)
  globalShortcut.register('CommandOrControl+Alt+T', () => {
    console.log('Global hotkey triggered: Ctrl+Alt+T (Screen Capture)');
    
    if (mainWindow) {
      // First send screen capture command directly (without showing window)
      mainWindow.webContents.send('hotkey-pressed-capture-only');
      
      // Minimize window (hide visible window if any)
      if (!mainWindow.isMinimized()) {
        mainWindow.minimize();
      }
    }
  });

  // Ctrl+Alt+C - Copy text (Global)
  globalShortcut.register('CommandOrControl+Alt+C', () => {
    console.log('Global hotkey triggered: Ctrl+Alt+C (Copy Text)');
    
    if (mainWindow) {
      if (mainWindow.isMinimized()) {
        mainWindow.restore();
      }
      mainWindow.show();
      mainWindow.webContents.send('copy-text');
    }
  });

  // Ctrl+Alt+S - Save text (Global)
  globalShortcut.register('CommandOrControl+Alt+S', () => {
    console.log('Global hotkey triggered: Ctrl+Alt+S (Save Text)');
    
    if (mainWindow) {
      if (mainWindow.isMinimized()) {
        mainWindow.restore();
      }
      mainWindow.show();
      mainWindow.webContents.send('save-text');
    }
  });
  
  // F1 - Help menu
  globalShortcut.register('F1', () => {
    console.log('Global hotkey triggered: F1 (Help)');
    
    if (mainWindow) {
      if (mainWindow.isMinimized()) {
        mainWindow.restore();
      }
      mainWindow.show();
      mainWindow.focus();
      
      dialog.showMessageBox(mainWindow, {
        type: 'info',
        title: 'Keyboard Shortcuts',
        message: 'Available Shortcuts (Works even when app is in background):',
        detail: 'Ctrl+Alt+T: Screen Capture\nCtrl+Alt+C: Copy Text\nCtrl+Alt+S: Save Text\nF1: This help screen\nEsc: Exit Application (Only when app is in foreground)',
        buttons: ['OK']
      });
    }
  });
  
  // ESC key - Close application (only if user confirms and window is focused)
  globalShortcut.register('Escape', () => {
    console.log('Escape key pressed');
    
    if (mainWindow && mainWindow.isFocused()) {
      dialog.showMessageBox(mainWindow, {
        type: 'question',
        buttons: ['Cancel', 'Exit'],
        defaultId: 1,
        title: 'Exit Application',
        message: 'Are you sure you want to exit the application?'
      }).then(result => {
        if (result.response === 1) {
          console.log('User confirmed exit');
          app.quit();
        }
      });
    }
  });
  
  console.log("Global shortcuts registered successfully");
}

// Start application
app.whenReady().then(() => {
  createWindow();
  
  // Register all shortcuts (to work globally)
  registerGlobalShortcuts();
  
  // Create captures folder (if it doesn't exist)
  const capturesDir = path.join(__dirname, 'captures');
  if (!fs.existsSync(capturesDir)) {
    fs.mkdirSync(capturesDir);
    console.log(`Created captures directory: ${capturesDir}`);
  }
  
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
      // Register shortcuts again after window is recreated
      registerGlobalShortcuts();
    }
  });
});

// When all windows are closed (except on macOS)
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Clear all shortcuts on exit
app.on('will-quit', () => {
  globalShortcut.unregisterAll();
  console.log("All shortcuts unregistered on exit");
});

// IPC Events (inter-process communication)
ipcMain.on('show-save-dialog', (event, options) => {
  dialog.showSaveDialog(mainWindow, options).then(result => {
    event.reply('save-dialog-response', result);
  }).catch(err => {
    console.error('Save dialog error:', err);
  });
});

// Show window after screen capture is completed
ipcMain.on('show-window-after-capture', (event, data) => {
  console.log('Showing window after capture completed:', data);
  
  if (mainWindow) {
    // Show window if minimized
    if (mainWindow.isMinimized()) {
      mainWindow.restore();
    }
    
    // Bring window to front
    mainWindow.show();
    mainWindow.focus();
    
    // Display notification
    setTimeout(() => {
      if (data && data.message) {
        mainWindow.webContents.send('show-notification', {
          message: data.message,
          type: data.type || 'info'
        });
      }
    }, 300); // Display notification after window appears
  }
});
    