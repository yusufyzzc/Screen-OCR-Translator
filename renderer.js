const { exec } = require('child_process');
const { ipcRenderer } = require('electron');
const fs = require('fs');
const path = require('path');

// OCR işlemini çalıştır
function runPythonTranslate() {
  const targetLang = document.getElementById('targetLang').value || 'en';
  console.log(`Starting screen capture, target language: ${targetLang}`);
  
  document.getElementById('inputText').value = "Scanning in progress, please wait...";
  document.getElementById('outputText').value = "";
  
  // Yükleme göstergesini göster
  showLoading(true);

  // OCR log dosyasını temizle
  try {
    if (fs.existsSync('ocr_log.txt')) {
      fs.unlinkSync('ocr_log.txt');
    }
  } catch (err) {
    console.error('Could not clean log file:', err);
  }

  // Python translate.py'yi çalıştır
  exec(`python ./backend/translate.py ${targetLang}`, (err, stdout, stderr) => {
    // Yükleme göstergesini gizle
    showLoading(false);
    
    if (err) {
      console.error(`Python script error: ${err}`);
      console.error(`Stderr: ${stderr}`);
      
      // İptal edildi mi kontrol et
      if (fs.existsSync('capture_cancelled.tmp')) {
        try {
          fs.unlinkSync('capture_cancelled.tmp');
          showNotification('Process cancelled', 'info');
          document.getElementById('inputText').value = "Process cancelled by user";
        } catch (e) {
          console.error('Could not clean temp file:', e);
        }
        return;
      }
      
      // Standart hata mesajı
      document.getElementById('inputText').value = `OCR execution error: ${stderr || err.message}`;
      showNotification('OCR process failed', 'error');
      return;
    }

    console.log(`Python output: ${stdout}`);
    
    try {
      // Çıktıdan sadece JSON kısmını çıkar
      const jsonMatch = stdout.match(/{.*}/s);
      if (jsonMatch) {
        const jsonStr = jsonMatch[0];
        const result = JSON.parse(jsonStr);
        
        // Sonuçları göster
        document.getElementById('inputText').value = result.extracted || "No text detected";
        document.getElementById('outputText').value = result.translated || "Translation failed";
        
        // Başarı bildirimi
        if (result.extracted && !result.extracted.startsWith("Error:") && !result.extracted.startsWith("No text")) {
          showNotification('Text successfully detected', 'success');
        } else if (result.extracted.includes("No text detected")) {
          showNotification('No text found in the selected area', 'warning');
        } else if (result.extracted.startsWith("Error:")) {
          showNotification(result.extracted, 'error');
        }
      } else {
        throw new Error("No JSON found in output");
      }
    } catch (e) {
      console.error(`JSON processing error: ${e}`);
      document.getElementById('inputText').value = `JSON processing error: ${e.message}\n\nRaw output: ${stdout}`;
      showNotification('Could not process result', 'error');
      
      // Hata log dosyasını okumayı dene
      try {
        if (fs.existsSync('ocr_log.txt')) {
          const logContent = fs.readFileSync('ocr_log.txt', 'utf8');
          console.error('OCR log content:', logContent);
        }
      } catch (logErr) {
        console.error('Could not read log file:', logErr);
      }
    }
  });
}

// Ekran yakalama işlemini başlatan fonksiyon (sessiz mod - pencere göstermeden)
function runPythonTranslateSilent() {
  const targetLang = document.getElementById('targetLang').value || 'en';
  console.log(`Starting silent screen capture, target language: ${targetLang}`);
  
  // Hiçbir kullanıcı arayüzü bildirimi gösterme
  
  // OCR log dosyasını temizle
  try {
    if (fs.existsSync('ocr_log.txt')) {
      fs.unlinkSync('ocr_log.txt');
    }
  } catch (err) {
    console.error('Could not clean log file:', err);
  }

  // Python translate.py'yi çalıştır
  exec(`python ./backend/translate.py ${targetLang}`, (err, stdout, stderr) => {
    // İşlem tamamlandığında pencereyi göster ve sonuçları göster
    
    // Artık yakalama işlemi tamamlandı, pencereyi gösterebiliriz
    if (err) {
      console.error(`Python script error: ${err}`);
      console.error(`Stderr: ${stderr}`);
      
      // İptal edildi mi kontrol et
      if (fs.existsSync('capture_cancelled.tmp')) {
        try {
          fs.unlinkSync('capture_cancelled.tmp');
          // Kullanıcı iptal ettiyse pencereyi göstermeye gerek yok
          return;
        } catch (e) {
          console.error('Could not clean temp file:', e);
        }
        return;
      }
      
      // Pencereyi göster
      ipcRenderer.send('show-window-after-capture', { success: false, message: stderr || err.message });
      return;
    }

    console.log(`Python output: ${stdout}`);
    
    try {
      // Çıktıdan sadece JSON kısmını çıkar
      const jsonMatch = stdout.match(/{.*}/s);
      if (jsonMatch) {
        const jsonStr = jsonMatch[0];
        const result = JSON.parse(jsonStr);
        
        // Sonuçları göster
        document.getElementById('inputText').value = result.extracted || "No text detected";
        document.getElementById('outputText').value = result.translated || "Translation failed";
        
        // Pencereyi göster ve bildirimi ayarla
        let notification = 'Text successfully detected';
        let type = 'success';
        
        if (result.extracted && !result.extracted.startsWith("Error:") && !result.extracted.startsWith("No text")) {
          // Başarılı
        } else if (result.extracted.includes("No text detected")) {
          notification = 'No text found in the selected area';
          type = 'warning';
        } else if (result.extracted.startsWith("Error:")) {
          notification = result.extracted;
          type = 'error';
        }
        
        // Pencereyi göster ve bildirimi ilet
        ipcRenderer.send('show-window-after-capture', { 
          success: true, 
          message: notification,
          type: type
        });
      } else {
        throw new Error("No JSON found in output");
      }
    } catch (e) {
      console.error(`JSON processing error: ${e}`);
      document.getElementById('inputText').value = `JSON processing error: ${e.message}\n\nRaw output: ${stdout}`;
      
      // Pencereyi göster ve hatayı bildir
      ipcRenderer.send('show-window-after-capture', { 
        success: false, 
        message: 'Could not process result', 
        type: 'error' 
      });
      
      // Hata log dosyasını okumayı dene
      try {
        if (fs.existsSync('ocr_log.txt')) {
          const logContent = fs.readFileSync('ocr_log.txt', 'utf8');
          console.error('OCR log content:', logContent);
        }
      } catch (logErr) {
        console.error('Could not read log file:', logErr);
      }
    }
  });
}

// Yükleme animasyonunu göster/gizle
function showLoading(show) {
  document.getElementById('loading').style.display = show ? 'flex' : 'none';
  document.querySelector('.app-container').classList.toggle('loading-active', show);
}

// Bildirim sistemi
function showNotification(message, type = 'info') {
  const notification = document.getElementById('notification');
  notification.textContent = message;
  notification.className = `notification ${type}`;
  
  // Göster
  notification.classList.add('show');
  
  // 3 saniye sonra otomatik gizle
  setTimeout(() => {
    notification.classList.remove('show');
  }, 3500);
}

// Metni kopyala
function copyText(id) {
  const textArea = document.getElementById(id);
  const text = textArea.value;
  
  if (!text) {
    showNotification('No text to copy', 'error');
    return;
  }
  
  navigator.clipboard.writeText(text)
    .then(() => {
      showNotification('Text copied to clipboard', 'success');
      console.log(`Copied text from ${id}`);
    })
    .catch(err => {
      showNotification('Could not copy text', 'error');
      console.error(`Copy error: ${err}`);
    });
}

// Dosya kaydetme için varsayılan klasör ve seçenekleri ayarla
function getSaveFileOptions(defaultName) {
  // Captures klasörünün yolunu oluştur
  const capturesDir = path.join(process.cwd(), 'captures');
  
  return {
    title: 'Save Text',
    defaultPath: path.join(capturesDir, defaultName),
    filters: [
      { name: 'Text Files', extensions: ['txt'] },
      { name: 'All Files', extensions: ['*'] }
    ]
  };
}

// Metni dosyaya kaydet
function saveTextToFile(text, defaultName = "translated_text.txt") {
  if (!text) {
    showNotification('No text to save', 'error');
    return;
  }
  
  // Dosya kaydetme dialogunu aç
  ipcRenderer.send('show-save-dialog', getSaveFileOptions(defaultName));
}

// Kaydet dialogu yanıtını işle
ipcRenderer.on('save-dialog-response', (event, result) => {
  if (!result.canceled && result.filePath) {
    const filePath = result.filePath;
    const content = document.getElementById('outputText').value || document.getElementById('inputText').value;
    
    try {
      fs.writeFileSync(filePath, content, 'utf-8');
      showNotification(`Text successfully saved: ${filePath}`, 'success');
    } catch (err) {
      showNotification(`Could not save file: ${err.message}`, 'error');
      console.error('File write error:', err);
    }
  }
});

// Uygulama başlatıldığında
ipcRenderer.on('app-ready', () => {
  showNotification('Application ready - Press Ctrl+Alt+T to capture screen', 'info');
});

// Bildirim gösterme olayını dinle
ipcRenderer.on('show-notification', (event, data) => {
  if (data && data.message) {
    showNotification(data.message, data.type || 'info');
  }
});

// Kısayollarla tetiklenen olaylar
ipcRenderer.on('hotkey-pressed', () => {
  // Önceki sonuçları temizle
  document.getElementById('inputText').value = '';
  document.getElementById('outputText').value = '';
  
  runPythonTranslate();
  showNotification('Screen capture started', 'info');
});

// Sessiz mod - pencereyi göstermeden ekran yakalama
ipcRenderer.on('hotkey-pressed-capture-only', () => {
  // Önceki sonuçları temizle
  document.getElementById('inputText').value = '';
  document.getElementById('outputText').value = '';
  
  // Sessiz modda ekran yakalamayı başlat
  runPythonTranslateSilent();
});

ipcRenderer.on('copy-text', () => {
  // Aktif olan metin alanını bul ve içeriğini kopyala
  const focusedElement = document.activeElement;
  if (focusedElement && (focusedElement.id === 'inputText' || focusedElement.id === 'outputText')) {
    copyText(focusedElement.id);
  } else {
    // Varsayılan olarak çeviri sonucunu kopyala
    copyText('outputText');
  }
});

ipcRenderer.on('save-text', () => {
  const outputText = document.getElementById('outputText').value;
  const inputText = document.getElementById('inputText').value;
  
  // Önce çeviri sonucunu, yoksa orijinal metni kaydet
  if (outputText && outputText !== 'Translation failed') {
    saveTextToFile(outputText, 'translated_text.txt');
  } else if (inputText) {
    saveTextToFile(inputText, 'extracted_text.txt');
  } else {
    showNotification('No text to save', 'error');
  }
});

// Sayfa Olay Dinleyicileri

// Ekran yakalama düğmesi
document.getElementById('selectBtn').addEventListener('click', () => {
  // Önceki sonuçları temizle
  document.getElementById('inputText').value = '';
  document.getElementById('outputText').value = '';
  
  runPythonTranslate();
});

// Çeviri düğmesi
document.getElementById('translateBtn').addEventListener('click', () => {
  const inputText = document.getElementById('inputText').value;
  if (!inputText || inputText === "Scanning in progress, please wait..." || inputText === "Process cancelled by user") {
    showNotification('Please capture text first', 'error');
    return;
  }
  
  // Hedef dili al
  const targetLang = document.getElementById('targetLang').value;
  
  // Manuel çeviri için
  document.getElementById('outputText').value = "Translating, please wait...";
  
  // Yükleme göstergesini göster
  showLoading(true);
  
  // Translate API'yi doğrudan çağır
  translateText(inputText, targetLang).then(result => {
    // Yükleme göstergesini gizle
    showLoading(false);
    document.getElementById('outputText').value = result;
    showNotification('Translation completed', 'success');
  }).catch(err => {
    // Yükleme göstergesini gizle
    showLoading(false);
    document.getElementById('outputText').value = `Translation error: ${err.message}`;
    showNotification('Translation failed', 'error');
  });
});

// Temizle düğmesi
document.getElementById('clearBtn').addEventListener('click', () => {
  document.getElementById('inputText').value = '';
  document.getElementById('outputText').value = '';
  showNotification('Text cleared', 'info');
});

// Kaydet düğmesi
document.getElementById('saveBtn').addEventListener('click', () => {
  const outputText = document.getElementById('outputText').value;
  const inputText = document.getElementById('inputText').value;
  
  // Önce çeviri sonucunu, yoksa orijinal metni kaydet
  if (outputText && outputText !== 'Translation failed') {
    saveTextToFile(outputText, 'translated_text.txt');
  } else if (inputText) {
    saveTextToFile(inputText, 'extracted_text.txt');
  } else {
    showNotification('No text to save', 'error');
  }
});

// Translate API
async function translateText(text, targetLang = "en") {
  if (!text) return "";
  
  const url = "https://translate.googleapis.com/translate_a/single";
  const params = new URLSearchParams({
    client: "gtx",
    sl: "auto",
    tl: targetLang,
    dt: "t",
    q: text
  });
  
  const response = await fetch(`${url}?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`Translation API error: ${response.status}`);
  }
  
  const data = await response.json();
  
  if (!data || !data[0]) {
    throw new Error("Translation API returned empty result");
  }
  
  // Çeviriyi birleştir
  return data[0].map(item => item[0]).join('');
}

// Kullanıcıya public fonksiyonları yayınla
window.copyText = copyText;
