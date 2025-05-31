import pytesseract
from PIL import Image, ImageEnhance
import subprocess
import sys
import json
import requests
import os
import traceback
import time

# Write to log file
def log_message(message):
    with open("ocr_log.txt", "a", encoding="utf-8") as log_file:
        log_file.write(f"{message}\n")

# Check Tesseract path
tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if not os.path.exists(tesseract_path):
    # Check alternative paths
    alt_paths = [
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Tesseract-OCR\tesseract.exe"
    ]
    
    for path in alt_paths:
        if os.path.exists(path):
            tesseract_path = path
            break

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = tesseract_path
log_message(f"OCR Engine: Tesseract")
log_message(f"Tesseract path: {pytesseract.pytesseract.tesseract_cmd}")
log_message(f"Tesseract exists: {os.path.exists(pytesseract.pytesseract.tesseract_cmd)}")

def run_snipping_tool():
    """Runs a Win+Shift+S-like screen capture tool"""
    try:
        log_message("Starting screen capture tool...")
        
        # Check and create captures directory (if it doesn't exist)
        captures_dir = "captures"
        if not os.path.exists(captures_dir):
            os.makedirs(captures_dir)
            log_message(f"Created captures directory: {captures_dir}")
        
        # Run Python module directly
        capture_process = subprocess.run(
            [sys.executable, 'backend/snipper.py'], 
            check=True
        )
        
        log_message(f"Screen capture process completed with exit code: {capture_process.returncode}")
        
        # Check for cancellation
        if os.path.exists("capture_cancelled.tmp"):
            with open("capture_cancelled.tmp", "r") as f:
                reason = f.read()
            os.remove("capture_cancelled.tmp")
            log_message(f"Screen capture was cancelled: {reason}")
            return False, reason
        
        # Check captured image
        capture_path = os.path.join("captures", "capture.png")
        if not os.path.exists(capture_path):
            err_msg = "Screen capture failed: No image file was created"
            log_message(err_msg)
            return False, err_msg
            
        return True, capture_path
        
    except subprocess.CalledProcessError as e:
        err_msg = f"Screen capture error: Process failed with code {e.returncode}"
        log_message(err_msg)
        return False, err_msg
    except Exception as e:
        err_msg = f"Screen capture error: {str(e)}"
        log_message(err_msg)
        return False, err_msg

def preprocess_image(image_path):
    """Preprocesses the image for OCR"""
    try:
        log_message(f"Preprocessing image: {image_path}")
        
        # Open image
        img = Image.open(image_path)
        log_message(f"Original image size: {img.size}, Mode: {img.mode}")
        
        # Preprocessing steps
        # 1. Grayscale conversion
        img_gray = img.convert('L')
        
        # 2. Increase contrast
        enhancer = ImageEnhance.Contrast(img_gray)
        img_contrast = enhancer.enhance(2.0)
        
        # 3. Sharpen
        enhancer = ImageEnhance.Sharpness(img_contrast)
        img_processed = enhancer.enhance(1.5)
        
        # 4. Dilation (optional, if text is too thin)
        # from PIL import ImageFilter
        # img_processed = img_processed.filter(ImageFilter.MinFilter(3))
        
        # Save processed image to captures folder
        captures_dir = "captures"
        preprocessed_filename = "preprocessed_capture.png"
        preprocessed_path = os.path.join(captures_dir, preprocessed_filename)
        
        # Save the processed image only once in the captures folder
        img_processed.save(preprocessed_path, quality=95)
        
        log_message(f"Image preprocessed and saved to: {preprocessed_path}")
        return preprocessed_path
    except Exception as e:
        log_message(f"Error preprocessing image: {str(e)}")
        return image_path

def extract_text_from_image(image_path):
    """Extracts text from image (OCR)"""
    try:
        log_message(f"Extracting text from: {image_path}")
        
        if not os.path.exists(image_path):
            return "Error: Image file not found"
        
        # Preprocess image
        preprocessed_image = preprocess_image(image_path)
        
        # Open image
        img = Image.open(preprocessed_image)
        
        # OCR configurations - each works well in different situations
        ocr_configs = [
            {"name": "Default", "config": "--psm 6 --oem 3"},            # Single text block
            {"name": "Auto page", "config": "--psm 3 --oem 3"},          # Auto page segmentation
            {"name": "Single column", "config": "--psm 4 --oem 3"},      # Single column of variable-sized text
            {"name": "Single word", "config": "--psm 8 --oem 3 -c preserve_interword_spaces=1"}    # Single word
        ]
        
        best_text = ""
        best_config = ""
        
        # Try all configurations and choose the best result
        for idx, config in enumerate(ocr_configs):
            try:
                log_message(f"Trying OCR config {idx+1}: {config['name']}")
                
                # OCR process
                current_text = pytesseract.image_to_string(
                    img, 
                    lang='eng',
                    config=config['config']
                ).strip()
                
                log_message(f"  - Extracted {len(current_text)} characters")
                
                # Save if longer or better output
                if len(current_text) > len(best_text):
                    best_text = current_text
                    best_config = config['name']
                    
                # Can skip other configs if we found a text long enough
                if len(best_text) > 50 and any(c.isalpha() for c in best_text):
                    log_message(f"  - Found good quality text, stopping OCR tries")
                    break
                    
            except Exception as e:
                log_message(f"  - Error with config {config['name']}: {str(e)}")
        
        if best_text:
            log_message(f"Best text extraction from config: {best_config}")
            log_message(f"Extracted text length: {len(best_text)}")
            log_message(f"Text sample: {best_text[:100]}...")
            return best_text
        else:
            log_message("No text could be extracted from the image")
            return "No text detected in the image. Please try a different area."
            
    except Exception as e:
        error_message = f"OCR Error: {str(e)}\n{traceback.format_exc()}"
        log_message(error_message)
        return error_message

def translate_text(text, target_lang="en"):
    """Translates text to target language"""
    if not text or text.startswith("Error:") or text.startswith("No text"):
        return text
    
    try:
        log_message(f"Translating text of length {len(text)} to {target_lang}")
        
        # Google Translate API
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": target_lang,
            "dt": "t",
            "q": text
        }
        
        # API request
        log_message("Sending translation request to Google Translate API")
        response = requests.get(url, params=params)
        response.raise_for_status()  # Check for HTTP errors
        
        # Process response
        translation_data = response.json()
        
        # Check if response is empty
        if not translation_data or not translation_data[0]:
            log_message("Translation API returned empty response")
            return "Translation failed: Empty API response"
            
        # Combine translation
        translated_text = ""
        for item in translation_data[0]:
            if item[0]:
                translated_text += item[0]
                
        log_message(f"Translation complete: {len(translated_text)} characters")
        return translated_text
        
    except requests.RequestException as e:
        error_message = f"Translation request error: {str(e)}"
        log_message(error_message)
        return error_message
    except Exception as e:
        error_message = f"Translation error: {str(e)}"
        log_message(error_message)
        return error_message

def main():
    try:
        # Start time
        start_time = time.time()
        
        # Initialize log file
        log_file = "ocr_log.txt"
        if not os.path.exists(log_file):
            open(log_file, "w").close()
        else:
            # Add separator to the beginning of the file
            with open(log_file, "a", encoding="utf-8") as f:
                f.write("\n\n" + "="*50 + "\n")
                f.write(f"NEW OCR SESSION: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*50 + "\n\n")
        
        # Get target language
        target_lang = sys.argv[1] if len(sys.argv) > 1 else "en"
        log_message(f"Target language: {target_lang}")

        # Run snipping tool
        success, result = run_snipping_tool()
        
        if not success:
            log_message(f"Snipping tool failed: {result}")
            print(json.dumps({
                "extracted": f"Error capturing screen: {result}",
                "translated": ""
            }))
            return
            
        # Extract text from image
        image_path = result
        extracted_text = extract_text_from_image(image_path)
        
        # Check if text is empty or contains error
        if not extracted_text or extracted_text.isspace():
            log_message("No text extracted or text is empty")
            print(json.dumps({
                "extracted": "No text detected in the selected area. Please try selecting an area with clearer text.",
                "translated": ""
            }))
            return
            
        if extracted_text.startswith("Error:") or extracted_text.startswith("OCR Error:"):
            log_message(f"OCR failed: {extracted_text}")
            print(json.dumps({
                "extracted": extracted_text,
                "translated": ""
            }))
            return
            
        # Translate text
        translated_text = translate_text(extracted_text, target_lang)
        
        # Print results as json
        result = {
            "extracted": extracted_text,
            "translated": translated_text
        }
        
        # Calculate processing time
        end_time = time.time()
        elapsed_time = end_time - start_time
        log_message(f"Total processing time: {elapsed_time:.2f} seconds")
        
        # Print only JSON output
        print(json.dumps(result))
        
    except Exception as e:
        error_message = f"Main process error: {str(e)}\n{traceback.format_exc()}"
        log_message(error_message)
        print(json.dumps({
            "extracted": error_message,
            "translated": ""
        }))

if __name__ == "__main__":
    main()
