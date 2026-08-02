CLSMC V24.0 DEPLOY

1. ZIP içindeki dosyaları GitHub köküne yükle.
2. requirements.txt, render.yaml, DATABASE_URL değiştirilmez.
3. Commit: CLSMC V24.0 - Klinik görev hasta dosyası ve teslim zinciri
4. Render: Clear build cache & deploy
5. /health üzerinde V24.0 kontrolü yap.

Yeni tablolar uygulama başlangıcında db.create_all ile otomatik oluşur.
Mevcut kullanıcı ve rapor verileri silinmez.
