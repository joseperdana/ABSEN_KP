import base64
from flask import Flask, session, url_for, render_template, jsonify, request, redirect
import cv2
import numpy as np
import face_recognition
import pickle
import os
import json
from datetime import datetime
import urllib.request
import traceback

# DETEKSI PROXY
try:
    # 'Bertanya' pada sistem operasi tentang pengaturan proxy yang aktif
    proxies = urllib.request.getproxies()
    
    # Jika sistem mengembalikan daftar proxy (tidak kosong)
    if proxies:
       # Ambil URL proxy yang terdeteksi
        http_proxy = proxies.get('http')
        https_proxy = proxies.get('https')

        # --- Logika Perbaikan URL Proxy ---
        # Jika proxy untuk HTTPS ada, kita proses
        if https_proxy:
            # Jika URL-nya dimulai dengan https:// (ini penyebab masalah), ganti menjadi http://
            if https_proxy.startswith('https://'):
                print(f"🔧 Proxy HTTPS terdeteksi sebagai '{https_proxy}', mengubah ke protokol HTTP untuk kompatibilitas...")
                # Ganti 'https://' menjadi 'http://' hanya pada kemunculan pertama
                https_proxy = https_proxy.replace('https://', 'http://', 1)
            
            # Atur environment variable HANYA untuk sesi skrip ini dengan URL yang sudah diperbaiki
            os.environ['HTTPS_PROXY'] = https_proxy
        
        # Atur juga untuk HTTP proxy jika ada
        if http_proxy:
            os.environ['HTTP_PROXY'] = http_proxy
            
        print(f"✅ Pengaturan proxy telah diterapkan: HTTPS_PROXY={os.environ.get('HTTPS_PROXY')}, HTTP_PROXY={os.environ.get('HTTP_PROXY')}")

except Exception as e:
    print(f"⚠️ Tidak dapat mendeteksi proxy sistem: {e}")

# import google sheets
import gspread
from google.oauth2.service_account import Credentials

# KONFIGURASI GOOGLE SHEETS
# app.py

# ==============================================================================
# === KONFIGURASI DAN KONEKSI GOOGLE SHEETS (DENGAN KODE DEBUGGING) ===
# ==============================================================================
try:
    # Tentukan scope (izin) yang dibutuhkan
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
    creds = Credentials.from_service_account_file('kredensial.json', scopes=scopes)
    client = gspread.authorize(creds)
    print("✅ Otorisasi ke Google berhasil.")

    # --- Variabel Konfigurasi ---
    NAMA_FILE_SPREADSHEET = 'Log Absen KP'
    # !!! GANTI DENGAN ALAMAT EMAIL PRIBADI ANDA !!!
    EMAIL_PRIBADI_ANDA = 'joseperdanat@gmail.com' 
    
    try:
        # Coba buka spreadsheet yang sudah ada
        print(f"Mencoba membuka spreadsheet: '{NAMA_FILE_SPREADSHEET}'")
        spreadsheet = client.open(NAMA_FILE_SPREADSHEET)
        
        print(f"✅ SPREADSHEET DITEMUKAN! Buka URL ini di browser Anda untuk melihatnya: {spreadsheet.url}")
        
        print("✅ Spreadsheet ditemukan dan berhasil dibuka.")
    except gspread.exceptions.SpreadsheetNotFound:
        # JIKA TIDAK DITEMUKAN, BUAT YANG BARU
        print(f"⚠️ Spreadsheet tidak ditemukan. Membuat file baru dengan nama '{NAMA_FILE_SPREADSHEET}'...")
        
        # Buat spreadsheet baru
        spreadsheet = client.create(NAMA_FILE_SPREADSHEET)
        
        # Bagikan ke email pribadi Anda agar bisa dilihat dan diakses
        spreadsheet.share(EMAIL_PRIBADI_ANDA, perm_type='user', role='writer')
        print(f"✅ Spreadsheet baru telah dibuat dan dibagikan ke {EMAIL_PRIBADI_ANDA}.")

    # Lanjutkan ke proses worksheet seperti biasa
    worksheet = spreadsheet.sheet1
    print("✅ Berhasil membuka worksheet pertama.")

    # Cek dan siapkan header jika sheet masih kosong
    if not worksheet.get_all_values():
        worksheet.append_row(['Timestamp', 'Tanggal', 'Nama'])
        print("📝 Header berhasil ditambahkan ke spreadsheet.")


except FileNotFoundError:
    print("⚠️ Gagal terhubung ke Google Sheets: File 'kredensial.json' tidak ditemukan.")
    worksheet = None
except Exception as e:
    print(f"⚠️ Terjadi error detail saat mencoba terhubung ke Google Sheets:")
    traceback.print_exc()
    worksheet = None
    
# FLASK
app = Flask(__name__)
app.secret_key = 'kp2025'

DB_DIR = './db'
if not os.path.exists(DB_DIR):
    os.mkdir(DB_DIR)

# Variabel untuk mencegah log duplikat dalam satu sesi aplikasi
# Format: {'YYYY-MM-DD': {'user1', 'user2'}}
daily_log_cache = {}

@app.route('/')
def home():
    # Logika untuk menghitung jumlah yang hadir hari ini bisa diambil dari cache
    today_str = datetime.now().strftime("%Y-%m-%d")
    logged_users_today = daily_log_cache.get(today_str, set())
    count_today = len(logged_users_today)
    return render_template('index.html', count_today=count_today, nickname=session.get('nickname'))

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register_user():
    # ... (KODE REGISTER ANDA YANG SUDAH DENGAN PENGECEKAN NAMA CASE-INSENSITIVE) ...
    # Salin fungsi register_user dari jawaban saya sebelumnya ke sini
    data = request.get_json()
    nickname = data.get('nickname')
    image_data = data.get('image')

    if not nickname or not image_data:
        return jsonify({'status': 'error', 'message': 'Nickname or image data missing.'})

    new_nickname_lower = nickname.lower()
    try:
        existing_files = os.listdir(DB_DIR)
    except FileNotFoundError:
        existing_files = []

    for filename in existing_files:
        if filename.endswith(".pickle"):
            existing_name = os.path.splitext(filename)[0]
            if existing_name.lower() == new_nickname_lower:
                return jsonify({'status': 'error', 'message': f'Nickname "{nickname}" sudah terdaftar. Silakan gunakan nama lain.'})
    
    # ... sisa kode register ... (decode image, find encoding, save pickle)
    image_data = image_data.split(',')[1]
    image_bytes = base64.b64decode(image_data)
    np_arr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame)
    if not face_locations:
        return jsonify({'status': 'error', 'message': 'Wajah tidak terdeteksi. Pastikan wajah terlihat jelas.'})
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
    file_path = os.path.join(DB_DIR, f"{nickname}.pickle")
    with open(file_path, 'wb') as f:
        pickle.dump({'encoding':face_encodings[0], 'logs':[]},f)
    return jsonify({'status': 'success', 'message': 'User registered successfully.'})


@app.route('/recognize', methods=['POST'])
def recognize():
    data = request.get_json()
    image_data = data.get('image')
    if not image_data:
        return jsonify({'status': 'error', 'message': 'No image data received.'})

    # ... (kode decode image dan generate encoding) ...
    image_data = image_data.split(',')[1]
    image_bytes = base64.b64decode(image_data)
    np_arr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if frame is None:
        return jsonify({'status': 'error', 'message': 'Image decoding failed.'})
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame)
    if not face_locations:
        return jsonify({'status': 'error', 'message': 'No face detected.'})
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    current_encoding = face_encodings[0]

    # Loop untuk mencocokkan wajah
    for filename in os.listdir(DB_DIR):
        if filename.endswith(".pickle"):
            with open(os.path.join(DB_DIR, filename), 'rb') as f:
                stored_data = pickle.load(f)
                stored_encoding = stored_data['encoding']
                
                matches = face_recognition.compare_faces([stored_encoding], current_encoding, tolerance=0.4)
                
                if matches[0]:
                    name = os.path.splitext(filename)[0]
                    
                    # === LOGIKA PENCEGAHAN DUPLIKAT & LOGGING KE SHEETS ===
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    
                    # Jika tanggal berganti, reset cache
                    if today_str not in daily_log_cache:
                        daily_log_cache[today_str] = set()

                    # Cek apakah user sudah login hari ini
                    if name not in daily_log_cache[today_str]:
                        # Jika belum, tambahkan ke cache
                        daily_log_cache[today_str].add(name)
                        
                        # Dan kirim log ke Google Sheets
                        if worksheet:
                            try:
                                now = datetime.now()
                                timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
                                worksheet.append_row([timestamp_str, today_str, name])
                                print(f"📝 Log berhasil ditambahkan ke Google Sheets untuk {name}")
                            except Exception as e:
                                print(f"🔥 Gagal menambahkan log ke Google Sheet: {e}")
                        
                    else:
                        print(f"✅ {name} sudah tercatat hadir hari ini.")
                    # === AKHIR BLOK ===

                    session['nickname'] = name
                    return jsonify({'status': 'success', 'name': name, "redirect_url": "/welcome"})

    return jsonify({'status': 'error', 'message': 'Wajah tidak dikenali.'})


@app.route('/welcome')
def welcome_page():
    nickname = session.get('nickname')
    if not nickname:
        return redirect(url_for('home'))
    return render_template('welcome.html', nickname=nickname)


@app.route('/logout')
def logout():
    session.pop('nickname', None)
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)