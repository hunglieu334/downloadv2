# Hướng dẫn cài đặt và chạy Video Tool

Đây là hướng dẫn chi tiết để cài đặt và chạy ứng dụng Video Tool trên môi trường cục bộ của bạn, bao gồm cả môi trường phát triển (development) và môi trường sản xuất (production).

## 1. Yêu cầu hệ thống

Đảm bảo hệ thống của bạn đã cài đặt các phần mềm sau:

-   **Python 3.8+**: Môi trường chạy cho backend Flask.
-   **pip**: Trình quản lý gói của Python (thường đi kèm với Python).
-   **FFmpeg**: Thư viện xử lý video và âm thanh mạnh mẽ. Bạn có thể tải xuống từ [trang chủ FFmpeg](https://ffmpeg.org/download.html) hoặc cài đặt qua trình quản lý gói của hệ điều hành (ví dụ: `sudo apt install ffmpeg` trên Ubuntu, `brew install ffmpeg` trên macOS).
-   **yt-dlp**: Công cụ download video (được cài đặt qua pip).

## 2. Cài đặt môi trường phát triển (Development Environment)

Thực hiện các bước sau để thiết lập môi trường phát triển:

### Bước 1: Clone Repository (nếu có)

Nếu bạn nhận được dự án dưới dạng một kho lưu trữ Git, hãy clone nó về máy của bạn:

```bash
git clone <địa_chỉ_repository>
cd video-tool-prototype
```

Nếu bạn nhận được dự án dưới dạng file nén, hãy giải nén và di chuyển vào thư mục dự án:

```bash
unzip video-tool-prototype.zip
cd video-tool-prototype
```

### Bước 2: Tạo và kích hoạt môi trường ảo (Virtual Environment)

Sử dụng môi trường ảo giúp quản lý các thư viện Python của dự án một cách độc lập:

```bash
python3 -m venv venv
source venv/bin/activate  # Trên Linux/macOS
# venv\Scripts\activate   # Trên Windows
```

### Bước 3: Cài đặt các thư viện Python cần thiết

Di chuyển vào thư mục gốc của dự án (nơi chứa `requirements.txt`) và cài đặt các thư viện:

```bash
pip install -r requirements.txt
```

### Bước 4: Chạy ứng dụng Flask Backend

Ứng dụng Flask sẽ phục vụ cả API backend và các file frontend tĩnh (HTML, CSS, JS).

```bash
export FLASK_APP=src/main.py
export FLASK_ENV=development # Đặt môi trường là development để bật chế độ debug
flask run
```

Hoặc bạn có thể chạy trực tiếp bằng Python:

```bash
python3 src/main.py
```

Ứng dụng sẽ chạy trên `http://127.0.0.1:5000` (hoặc một cổng khác nếu được cấu hình).

## 3. Build cho môi trường sản xuất (Production Environment)

Ứng dụng này được thiết kế để Flask phục vụ các file frontend tĩnh. Do đó, không có bước build frontend riêng biệt như các dự án React/Vue độc lập. Các file HTML, CSS, JS đã được đặt trong thư mục `src/static` và sẽ được Flask phục vụ trực tiếp.

Để chạy ứng dụng trong môi trường sản xuất, bạn nên sử dụng một máy chủ WSGI (Web Server Gateway Interface) như Gunicorn hoặc uWSGI.

### Bước 1: Cài đặt Gunicorn (hoặc uWSGI)

```bash
pip install gunicorn
```

### Bước 2: Chạy ứng dụng với Gunicorn

Di chuyển vào thư mục gốc của dự án và chạy lệnh sau:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 src.main:app
```

-   `-w 4`: Chạy 4 worker process (có thể điều chỉnh tùy theo số lượng CPU core).
-   `-b 0.0.0.0:5000`: Lắng nghe trên tất cả các interface ở cổng 5000.
-   `src.main:app`: Chỉ định module và đối tượng ứng dụng Flask.

## 4. Cấu trúc thư mục dự án

```
video-tool-prototype/
├── src/
│   ├── main.py             # File chính của ứng dụng Flask
│   ├── models/             # Định nghĩa các model database (nếu có)
│   ├── routes/             # Định nghĩa các API routes (video.py, upload.py)
│   │   ├── video.py
│   │   └── upload.py
│   ├── static/             # Chứa các file frontend tĩnh (HTML, CSS, JS)
│   │   └── index.html
│   ├── downloads/          # Thư mục chứa các video đã download
│   └── processed/          # Thư mục chứa các video đã xử lý
├── requirements.txt        # Danh sách các thư viện Python cần thiết
├── README.md               # Hướng dẫn này
└── venv/                   # Môi trường ảo (sau khi tạo)
```

## 5. Các tính năng đã triển khai

Hiện tại, ứng dụng đã triển khai các tính năng chính sau:

-   **Download video đơn lẻ**: Tải video từ URL với các tùy chọn chất lượng khác nhau.
-   **Download kênh**: Tải nhiều video từ một kênh YouTube với giới hạn số lượng video.
-   **Chỉnh sửa video**: Ứng dụng hỗ trợ một số bộ lọc video và âm thanh cơ bản sử dụng FFmpeg. Danh sách các bộ lọc hiện có thể được truy vấn thông qua API `/api/video/filters`. Hiện tại, có 20 bộ lọc video và 9 bộ lọc âm thanh được hỗ trợ. Việc mở rộng lên "300 tính năng chỉnh sửa" sẽ yêu cầu phát triển thêm và có thể mất nhiều thời gian.

Chúc bạn thành công!

