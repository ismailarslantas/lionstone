# Lionstone Reels — markaya özel Instagram Reels akışı

Çekimi ver, video markanın stiliyle, kontrol edilmiş ve paylaşıma hazır gelsin.
Konu bulmaktan takvime kadar her adım düz dosyalarda durur: okunur, değiştirilir, geri alınır.

```
Konu → Hook → Script → Çekim → Kesim → Grafik → Ses → Kontrol → Kapak + Caption → Takvim
 🧠      🧠      🧠       🎥      🤖       🤖      🤖      🤖          🤖 + 🧠          🤖
```

🧠 Claude yazar (marka profilini ve kanca kütüphanesini okuyarak) · 🎥 sen çekersin · 🤖 Lionstone yapar ve ölçer.

## Hazırlaman gereken

| | |
|---|---|
| Claude | Ücretli bir Claude planı ve **Claude Code** (sistem normal sohbette değil, bilgisayarına kurulan Claude Code'da çalışır) |
| Bilgisayar | Mac, Windows ya da Linux. Render senin bilgisayarında yapılır; hız bilgisayarına bağlı |
| Yazılım | Python 3.10+, FFmpeg. Kurgu programı gerekmez |
| Ücret | Lionstone ücretsiz ve açık kaynak (Apache-2.0). Aylık ücret yok, video başına ücret yok |

```bash
pip install "lionstone[whisper] @ git+https://github.com/ismailarslantas/lionstone"
lionstone doctor
lionstone reels sfx build        # 31 özgün ses efektiyle başlangıç paketi
```

## 1 · Markayı bir kez tanıt

```bash
lionstone reels brand init "Örnek Emlak" --handle @ornekemlak \
  --audience "İzmir'de ev arayan genç aileler" --accent "#E8B04B"
```

`brands/ornek-emlak/brand.json` ve `brand.md` oluşur. JSON'da: kitle, ses tonu, ürünler,
dürüstçe vaat edilebilecek sonuçlar, kitlenin sorunları, yasaklı ifadeler, CTA, hashtag'ler,
renkler, font ve kurgu stili (`style`). `brand.md` serbest notlar içindir: Claude konu, hook ve
caption yazarken ikisini de okur. Logo, alt yazı bandı ve bitiş kartı için mevcut bir Lionstone
brand kit'i `kit` alanıyla bağlanır.

| `style` alanı | Varsayılan | Ne yapar |
|---|---|---|
| `intensity` | `dynamic` | Kesim sertliği: natural · balanced · dynamic |
| `caption_style` | `karaoke` | Türkçe kelime kelime altyazı, konuşulan kelime vurgulu |
| `color` | `punchy` | Renk görünümü |
| `title_effect` | `T02` | Kanca yazısı efekti (dikeye göre satır kırar) |
| `music`, `music_volume` | yok · 0.18 | Müzik dosyası; konuşmanın altında kendiliğinden kısılır |
| `sfx` | `true` | Ses efektlerini seyrek ve anlamlı yerleştirir |

## 2 · Konu, hook, script (Claude)

```bash
lionstone reels new "Örnek Emlak" "Kira mı ev almak mı"
lionstone reels hooks "Örnek Emlak" "kira artışı" --angle hata --angle karsit
```

`hooks`, 10 açıdan (merak, hata, sonuç, karşıt görüş, liste, hikâye, soru, gösterim, uyarı,
kolaylık) 60 özgün şablonu marka bilgisiyle doldurur; ayrıca ikinci kanca ve CTA şablonları verir.
Bilinmeyen alanlar `{sayı}` gibi görünür kalır, uydurulmaz. Claude bunlardan yola çıkıp
`reel.json`'u yazar: konu, **neden tutacağı**, en az iki kanca (A/B), ikinci kanca, konuşur gibi
akan ve çağrıyla biten script, caption, hashtag'ler, kapak yazıları.

```bash
lionstone reels lint projects/ornek-emlak/2026-11-05-kira-mi-ev-almak-mi
```

Kontrol eder: kanca uzunluğu (≤ 14 kelime), doldurulmamış şablon, A/B kanca, ikinci kanca,
scriptin hedef süreye uyması (Türkçe ≈ 2,5 kelime/sn), CTA ile bitiş, yasaklı ifadeler,
caption ≤ 2200 karakter, hashtag ≤ 30, kapak yazısı.

## 3 · Çek ve teslim al

Videoyu reel klasöründeki `ham/` içine koy:

```bash
lionstone reels make projects/ornek-emlak/2026-11-05-kira-mi-ev-almak-mi
```

| Adım | Ne olur |
|---|---|
| Kesim | Boşluk, dolgu sesi, tekrar eden kelime ve cümleler atılır; kesim kelimenin içine düşmez. Kesilemeyen tekrar raporda görünür |
| Grafik | 9:16, Türkçe kelime kelime altyazı, kanca yazısı, marka rengi, brand kit |
| Ses | Efektler, müzik (ducking), -14 LUFS |
| Kontrol | Bitmiş video yeniden ölçülür (aşağıda) |
| Kapak | Ham görüntüden 3 versiyon, yazı 3:4 grid kırpmasına göre yerleşir |
| Metin | `caption.txt` (caption + hashtag'ler), metin kontrol sonucu |
| Düzenleme odası | `kurgu/room.html` |

Çıktı `teslim/` klasörüne gelir:

```
teslim/
  ornek-emlak-kira-mi-ev-almak-mi.mp4
  kapak-1.jpg  kapak-2.jpg  kapak-3.jpg
  caption.txt
  rapor.md  rapor.json  qa.md  qa.json
```

### Teslim raporu

```
TESLİME HAZIR ✅

| Kontrol                  | Durum |
| Tekrar taraması          | Temiz |
| Kesim noktaları          | Temiz |
| Senaryo karşılaştırması  | Temiz |
| Yazı taşması             | Temiz |
| Ses seviyesi             | Temiz |
| Görüntü                  | Temiz |
| Kapak                    | 3 versiyon |
```

- **Senaryo karşılaştırması:** videoda gerçekten duyulan kelimeler scriptle hizalanır; eksik,
  fazla ve değişen kelimeler listelenir. %75'in altı teslimi durdurur.
- **Tekrar taraması:** kesimden sonra kalan "bence bence" türü tekrarlar.
- **Kesim noktaları:** kelime kırpılması, birleşimlerde tık, düşük güvenli kesimler.
- **Yazı taşması:** her grafik, efektin gerçek yazı boyutuyla ölçülür; Reels arayüzünün kapladığı
  alt %20 ve sağ kenar hesaba katılır. Açık taşma teslimi durdurur. Bu bir tahmindir (OCR yok)
  ve raporda öyle yazar.
- **Ses ve görüntü:** loudness, true peak, siyah/donmuş kare, A/V uzunluğu, format.

Çalışmayan bir kontrol "geçti" sayılmaz: raporda "Atlandı" ve nedeniyle yazılır.

Rapor üç karardan birini verir:

| Karar | Anlamı | Çıkış kodu |
|---|---|---|
| **TESLİME HAZIR ✅** | Çalışan kontroller temiz, senaryo ≥ %90 uyuşuyor | 0 |
| **GÖZDEN GEÇİR 👀** | Senaryo %75–90 uyuşuyor, tekrar kalmış ya da senaryo karşılaştırılamamış | 2 |
| **DÜZELTME GEREKİYOR 🛑** | Senaryo < %75, açık yazı taşması, teknik hata ya da metin hatası | 2 |

## 4 · Düzenleme odası

```bash
lionstone reels room projects/…/kurgu/plan.json   # make zaten oluşturur
```

Tarayıcıda açılan tek bir yerel sayfa: video ve her kelime yan yana. Kelimeye tıkla → o ana git.
Kes moduna geç → kelimeye tıklayarak kes ya da kesileni geri al. Çift tıkla → altyazıdaki yazımı
düzelt (isim, marka, ürün adı). Önizleme kesilen yerleri atlayarak oynatır. "Değişiklikleri indir"
ile gelen dosyayı uygula ve yeniden render et:

```bash
lionstone reels room-apply projects/…/kurgu/plan.json ~/Downloads/room-edits.json
lionstone reels make projects/… --keep-plan
```

`--keep-plan` planı yeniden üretmez: düzeltmelerin korunur; ses, kontrol ve kapaklar yeniden yapılır.

Video internete yüklenmez; sayfa dosyayı diskinden oynatır.

## 5 · Takvim

```bash
lionstone reels schedule projects/…/kira-mi-ev-almak-mi "2026-11-10 19:00"
lionstone reels calendar --brand "Örnek Emlak" --ics takvim.ics
```

Takvim reel klasörlerinin kendisinden üretilir (tek doğru kaynak). `.ics` Google, Apple ve
Outlook takvimine eklenir. Durumlar: fikir · script · çekim · kurgu · kontrol · hazır · yayında.

## Ses efektleri ve müzik

`lionstone reels sfx build` FFmpeg ile 31 özgün efekt üretir (whoosh, pop, click, ding, riser,
boom, swipe, type). Lisanslı kendi paketlerini aynı klasöre (`~/.config/lionstone/sfx`, ya da
`LIONSTONE_SFX_DIR`) koyduğunda alt klasör adı kategori olur ve otomatik kullanılır. Yerleşim
seyrektir (en fazla 1,2 sn'de bir): açılışta whoosh, yazı grafiklerinde pop, CTA'da ding. Elle
yerleşim için reel klasörüne `sfx.json` koy:

```json
[{"at": 1.2, "sound": "pop"}, {"at": 6.8, "sound": "ding/ding-02", "gain": 0.4}]
```

Müziğin ticari kullanım lisansı senin sorumluluğunda; Lionstone müzik dağıtmaz.

## Kontrol listesi

`lionstone reels checklist` 37 maddelik teslim öncesi listeyi gösterir: 🤖 olanları Lionstone
ölçer, 👀 olanlara (vaat edilen sonuç gerçek mi, müzik lisansı, müşteri onayı…) göz ile bakılır.

## Kim için

- Videosunu kendisi çıkarmak isteyen içerik üreticileri
- Düzenli içerik üreten markalar ve ajanslar
- Editörüyle daha hızlı üretmek isteyen ekipler
- Birden fazla markayı tek düzende yönetenler (`brands/` altında her marka ayrı)

Çekim yine sende. Tek tuşla viral video vaadi yok: kanca ve script iyi olduğu kadar iyidir,
Lionstone işin kalanını hatasız ve hızlı yapar.
