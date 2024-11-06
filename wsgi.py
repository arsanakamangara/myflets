import flet as ft

# وارد کردن تابع اصلی که برنامه شما را اجرا می‌کند
from my_flet_chat import main  # نام فایل یا ماژولی که در آن تابع main تعریف شده است

# ایجاد شیء app برای استفاده در Gunicorn
app = ft.app(target=main)

if __name__ == "__main__":
    # این بخش فقط در صورتی اجرا می‌شود که به صورت مستقیم برنامه را اجرا کنید
    app.run()
