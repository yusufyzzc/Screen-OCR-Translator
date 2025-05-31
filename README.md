# Screen Text Translator

An Electron-based desktop application that allows you to capture screen areas and translate text.

![Application Screenshot](assets/icon.png)

## Features

- **Screen Capture**: Quickly capture any area of your screen
- **Text Recognition**: Extract text from captured images
- **Translation**: Translate extracted text between multiple languages
- **Global Shortcuts**: Use the application even when it's running in background
- **Copy & Save**: Easily copy or save translated text


## Global Keyboard Shortcuts

| Shortcut | Function | Description |
|----------|----------|-------------|
| Ctrl+Alt+T | Screen Capture | Captures a selected area of the screen (works in background) |
| Ctrl+Alt+C | Copy Text | Copy the translated text to clipboard |
| Ctrl+Alt+S | Save Text | Save the translated text to a file |
| F1 | Help | Display keyboard shortcuts help |
| Esc | Exit | Close the application (only when app is in foreground) |

## Development

### Project Structure
- `main.js` - Main Electron process
- `index.html` - Main application UI
- `renderer.js` - Renderer process code
- `assets/` - Application icons and resources
- `captures/` - Folder where screen captures are stored

### Building from Source
```
npm run build
```

## Acknowledgements

- [Electron](https://www.electronjs.org/)
- [Tesseract.js](https://tesseract.projectnaptha.com/) for OCR functionality
- [Google Translate API](https://cloud.google.com/translate) for translation services 