# CLSMC V26.0 Deploy

## Mevcut Neon veritabanıyla güncelleme

Mevcut admin hesabı ve şifresi korunur. Render Environment içindeki `DATABASE_URL` ve `SECRET_KEY` değerlerini silmeyin.

1. Temiz paketin içeriğini GitHub depo köküne yükleyin.
2. Render > Manual Deploy > Clear build cache & deploy.
3. Deploy sonrası `/health` adresinde `status: ok` ve `database: reachable` kontrolü yapın.
4. Tarayıcıda Ctrl+F5 uygulayın.

## Sıfırdan kurulum

Kaynak kodda varsayılan admin şifresi yoktur. İlk admin oluşmadan önce Render Environment'a aşağıdakilerden birini ekleyin:

- `INITIAL_ADMIN_PASSWORD`: En az 10 karakterlik geçici parola. İlk girişte değiştirilmesi zorunludur.
- veya `ADMIN_PASSWORD_HASH`: Werkzeug uyumlu parola özeti.

İlk admin oluştuktan sonra `INITIAL_ADMIN_PASSWORD` değerini Render Environment'dan kaldırın.

## Değişkenler

- `DATABASE_URL`: Neon PostgreSQL bağlantısı
- `SECRET_KEY`: Güçlü ve kalıcı Flask oturum anahtarı
- `ADMIN_USERNAME`: İsteğe bağlı ilk admin kullanıcı adı
- `INITIAL_ADMIN_PASSWORD`: Sadece ilk kurulum için geçici parola
- `ADMIN_PASSWORD_HASH`: İlk kurulum için alternatif parola özeti

Gizli değerleri GitHub'a yüklemeyin.
