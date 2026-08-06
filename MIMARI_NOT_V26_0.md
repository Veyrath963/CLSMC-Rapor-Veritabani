# V26.0 Mimari Not

V26.0, canlı rotaları kırmadan servis katmanına geçiş yapar. Güvenlik, hasta eşleştirme ve denetim serileştirme mantığı `clsmc/services` ve `clsmc/security.py` içine ayrılmıştır. `create_app()` test/deploy köprüsü eklenmiştir.

Mevcut yaklaşık 65 rotanın tamamı bu sürümde fiziksel Blueprint dosyalarına taşınmamıştır. Bu bilinçli bir geriye uyumluluk kararıdır: tek seferde rota adlarını ve `url_for` bağlantılarını değiştirmek canlı sistemi gereksiz riske sokar. Sonraki mimari sürümde modüller rota adları korunarak Blueprint'lere kademeli taşınabilir.
