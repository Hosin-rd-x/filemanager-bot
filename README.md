# 📁 ربات فایل منیجر تلگرام

یک ربات حرفه‌ای مدیریت فایل برای تلگرام با پنل کامل ادمین.

---

## ✨ امکانات

### پنل ادمین
- 📁 **پوشه‌بندی** — ساخت پوشه و گروه‌بندی فایل‌ها
- 📤 **آپلود انواع فایل** — داکیومنت، ویدیو، صدا، عکس، ویس، GIF
- 🔗 **لینک اختصاصی** — برای هر فایل یا پوشه یک لینک یکتا
- ⏳ **انقضای خودکار** — بعد از 1d / 12h / 30m فایل غیرفعال میشه
- ⬇️ **محدودیت دانلود** — مثلاً فقط 100 بار قابل دانلود
- 🔑 **پسورد** — روی فایل یا پوشه
- 🛡 **فوروارد پروتکشن** — جلوگیری از فوروارد کردن فایل
- 📊 **آمار** — دانلود کل، کاربران یکتا، حجم
- 👥 **مدیریت ادمین‌ها** — افزودن/حذف ادمین
- 🚫 **بلاک کاربران** — جلوگیری از دسترسی
- 📢 **عضویت اجباری در کانال**

---

## 🚀 راه‌اندازی

### ۱. پیش‌نیازها
```bash
Python 3.10+
```

### ۲. نصب وابستگی‌ها
```bash
cd filemanager_bot
pip install -r requirements.txt
```

### ۳. تنظیم متغیرها

**روش اول — متغیر محیطی (توصیه‌شده):**
```bash
export BOT_TOKEN="توکن ربات از BotFather"
export OWNER_ID="آیدی عددی تلگرام خودت"
```

**روش دوم — ویرایش مستقیم `main.py`:**
```python
BOT_TOKEN = "توکن ربات از BotFather"
OWNER_ID  = 123456789   # آیدی عددی تلگرامت
```

### ۴. اجرا
```bash
python main.py
```

---

## 📂 ساختار پروژه

```
filemanager_bot/
├── main.py                  # نقطه ورود
├── requirements.txt
├── database/
│   └── db.py                # SQLite — تمام عملیات دیتابیس
├── handlers/
│   ├── admin.py             # پنل ادمین
│   ├── upload.py            # آپلود و مدیریت فایل
│   ├── user.py              # تحویل فایل به کاربر
│   └── blocked.py           # مدیریت بلاک
└── utils/
    ├── helpers.py           # توابع کمکی
    ├── keyboards.py         # کیبوردهای اینلاین
    └── expire_checker.py    # بکگراند — حذف خودکار
```

---

## 🔄 نحوه استفاده

### ادمین:
1. `/start` ← پنل اصلی باز میشه
2. **📁 پوشه‌ها** ← پوشه جدید بساز
3. داخل پوشه **📤 افزودن فایل** ← تنظیمات (انقضا، پسورد، ...) ← فایل رو بفرست
4. **🔗 کپی لینک** ← لینک رو تو گروه/کانال بذار

### کاربر:
1. روی لینک کلیک می‌کنه
2. اگه پسورد داره، وارد می‌کنه
3. فایل دریافت می‌کنه ✅

---

## ⚙️ فرمت زمان انقضا

| ورودی | معنا         |
|-------|--------------|
| `1d`  | ۱ روز        |
| `12h` | ۱۲ ساعت     |
| `30m` | ۳۰ دقیقه    |
| `60s` | ۶۰ ثانیه    |
| `0`   | بدون انقضا  |

---

## 🛡 نکات امنیتی

- توکن ربات رو هرگز در کد ننویس — از متغیر محیطی استفاده کن
- فایل `filemanager.db` رو بکاپ بگیر
- برای اجرای دائمی از `systemd` یا `screen` استفاده کن

### اجرای دائمی با screen:
```bash
screen -S filebot
python main.py
# Ctrl+A D برای detach
```

### اجرای دائمی با systemd:
```ini
# /etc/systemd/system/filebot.service
[Unit]
Description=Telegram File Manager Bot
After=network.target

[Service]
WorkingDirectory=/path/to/filemanager_bot
ExecStart=/usr/bin/python3 main.py
Environment=BOT_TOKEN=your_token
Environment=OWNER_ID=your_id
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
systemctl enable filebot
systemctl start filebot
```
