CLSMC MERKEZİ TAKİP VE RAPORLAMA SİSTEMİ — V23.1
TAM PROJE KURULUMU
Developer: Veyrath
====================================================

PAKETİN AMACI
-------------
Bu klasör bugüne kadar hazırlanan GEÇERLİ geliştirmelerin birleştiği son sürümdür.
Başarısız eski hızlı menü ve sabit sol panel denemeleri pakete dahil değildir.

GITHUB'A YÜKLEME
----------------
1. Bu klasörün içindeki bütün dosya ve klasörleri seç.
2. GitHub repository köküne yükle:
   Veyrath963/CLSMC-Rapor-Veritabani
3. Eski dosyaların üzerine yazılmasını onayla.
4. Commit mesajı:
   CLSMC V23.1 - Full final project package

RENDER
------
Build Command:
pip install -r requirements.txt

Start Command:
gunicorn app:app

Health Check:
 /health

DATABASE_URL
------------
Gerçek Neon DATABASE_URL değerini hiçbir dosyaya yazma.
Render > Service > Environment bölümünde DATABASE_URL olarak sakla.
.env.example yalnızca örnek bağlantı metni içerir.

KONTROL ADRESLERİ
-----------------
Ana giriş:
https://clsmc-rapor-sistemi-jjcg.onrender.com

Admin girişi:
https://clsmc-rapor-sistemi-jjcg.onrender.com/admin/login

Admin hesapları:
https://clsmc-rapor-sistemi-jjcg.onrender.com/admin/accounts

Hastane yöneticisi:
https://clsmc-rapor-sistemi-jjcg.onrender.com/admin/hospital-management

Sistem sağlık kontrolü:
https://clsmc-rapor-sistemi-jjcg.onrender.com/health

ÖNEMLİ
------
Bu paket kaynak kod ve arayüz yedeğidir.
Canlı Neon veritabanındaki kullanıcı/rapor kayıtlarının haricî yedeği değildir.
