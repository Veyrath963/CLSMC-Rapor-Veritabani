# CLSMC Rapor Sistemi V19.4 — Neon PostgreSQL Dağıtımı

Bu sürümde web uygulaması Render üzerinde, PostgreSQL veritabanı ise Neon üzerinde çalışacak şekilde hazırlanmıştır.

## Mimari

- Web uygulaması: Render
- Veritabanı: Neon PostgreSQL
- Kaynak kod: GitHub
- Başlatma: `gunicorn app:app`
- Render health check: `/health`

## Güvenli DATABASE_URL kullanımı

Neon bağlantı adresini GitHub'a veya `render.yaml` içine yazmayın. `render.yaml` içinde:

```yaml
- key: DATABASE_URL
  sync: false
```

bulunur. Bağlantı adresini Render Dashboard > Web Service > Environment bölümünde `DATABASE_URL` değeri olarak girin.

Mevcut bir Render Blueprint'i güncelliyorsanız `sync: false` yeni değeri otomatik istemeyebilir. Bu durumda `DATABASE_URL` değerini Render Dashboard'dan elle ekleyin/güncelleyin.

## Neon bağlantısı

Neon Dashboard > Project > Connect bölümünden uygulamanız için bağlantı adresini alın. Web uygulaması için Neon'un sunduğu pooled bağlantı adresi tercih edilebilir. Adres `postgresql://...` biçimindedir ve Neon'un verdiği SSL parametrelerini aynen koruyun.

## İlk veritabanı

Yeni ve boş bir Neon veritabanına ilk bağlanıldığında uygulama mevcut SQLAlchemy modellerinin tablolarını `db.create_all()` ile oluşturur ve varsayılan admin hesabını seed eder.

> Eski Render PostgreSQL içinde gerçek verileriniz varsa, yalnızca `DATABASE_URL` değiştirmek bu verileri Neon'a taşımaz. Önce yedek/migrasyon yapılmalıdır.

## Kullanıcı hesabı oluşturma

V19.3 ve sonrasında public kayıt kapalıdır. Yeni kullanıcılar yalnızca `/admin/login` üzerinden Admin Paneli > Yeni Üyelik Oluştur ile açılır.

## Admin

- Yol: `/admin/login`
- Varsayılan kullanıcı adı: `Veyrath`
- Varsayılan parola: uygulamadaki hash üzerinden doğrulanır; parolayı kaynak koda düz metin olarak eklemeyin.

## Eski Render Postgres kaynağı

`render.yaml` artık Render PostgreSQL kaynağı tanımlamaz. Blueprint'ten tanımın kaldırılması mevcut Render DB'yi otomatik silmez. Neon'un doğru çalıştığını ve gerekiyorsa verilerin taşındığını doğruladıktan sonra eski Render DB'yi Dashboard'dan ayrıca silebilirsiniz.
