"""Build the handbook: inject annotated real-render galleries into en.html / tr.html.

    python gallery.py            -> writes build/en.html and build/tr.html

Gallery stills live in img/real/ (real `lionstone fx preview` renders, 9:16, of one
source clip). Each card shows the frame, the preset name and id, and a one-line note.
"""
from pathlib import Path
import html
import re

HERE = Path(__file__).parent

# id: (EN note, TR note)
LOOKS = {
    "original": ("The untouched source frame, for comparison.", "Karşılaştırma için dokunulmamış kaynak kare."),
    "look-natural-neutral": ("Balanced, honest colour. Safe default.", "Dengeli, dürüst renk. Güvenli varsayılan."),
    "look-clean-daylight": ("Fresh, slightly brighter daylight balance.", "Ferah, biraz daha aydınlık gün ışığı."),
    "look-warm-cinema": ("Warm shadows, cinematic contrast.", "Sıcak gölgeler, sinematik kontrast."),
    "look-cool-cinema": ("Cooler, moodier cinematic grade.", "Daha serin, daha duygusal sinema rengi."),
    "look-muted-film": ("Lower saturation, soft film curve.", "Düşük doygunluk, yumuşak film eğrisi."),
    "look-soft-contrast": ("Gentle contrast for long talks.", "Uzun konuşmalar için yumuşak kontrast."),
    "look-matte-editorial": ("Lifted blacks, magazine feel.", "Kaldırılmış siyahlar, dergi hissi."),
    "look-true-to-life": ("Documentary accuracy, minimal styling.", "Belgesel doğruluğu, en az stil."),
    "look-low-saturation": ("Calm, desaturated and serious.", "Sakin, soluk ve ciddi."),
    "look-golden-hour": ("Golden warmth, sunset glow.", "Altın sıcaklığı, gün batımı ışıltısı."),
    "look-warm-interior": ("Cosy indoor warmth.", "Samimi iç mekân sıcaklığı."),
    "look-steel-blue": ("Cool steel tones for tech topics.", "Teknoloji için serin çelik tonları."),
    "look-cool-shadow": ("Blue shadows, neutral skin.", "Mavi gölgeler, doğal ten."),
    "look-analog-soft": ("Soft analogue warmth.", "Yumuşak analog sıcaklık."),
    "look-vintage-fade": ("Faded, nostalgic print.", "Solmuş, nostaljik baskı."),
    "look-night-detail": ("Lifts detail in dark scenes.", "Karanlık sahnelerde detayı açar."),
    "look-neon-balance": ("Keeps neon colour under control.", "Neon renkleri kontrol altında tutar."),
    "look-classic-bw": ("Classic black and white.", "Klasik siyah-beyaz."),
    "look-high-contrast-mono": ("Hard, dramatic monochrome.", "Sert, dramatik siyah-beyaz."),
    "look-product-neutral": ("Accurate colour for products.", "Ürünler için doğru renk."),
    "look-detail-pop": ("Crisper texture and detail.", "Daha keskin doku ve detay."),
    "look-bright-interior": ("Bright, airy rooms for property.", "Emlak için aydınlık, ferah odalar."),
    "look-window-balance": ("Tames bright windows indoors.", "İç mekânda parlak pencereyi dengeler."),
    "look-natural-exterior": ("Natural greens and skies.", "Doğal yeşiller ve gökyüzü."),
    "look-punchy-social": ("Contrast and pop that read on phones.", "Telefonda okunan kontrast ve canlılık."),
    "look-soft-skin-safe": ("Flattering, skin-safe social look.", "Teni koruyan, hoş sosyal görünüm."),
    "color-controls": ("Manual grade: exposure, curves, temp, vibrance.", "Elle renk: pozlama, eğri, sıcaklık, canlılık."),
}
EFFECTS = {
    "soft-bloom": ("Gentle glow around highlights.", "Parlak alanların çevresinde yumuşak ışıma."),
    "light-leak": ("Warm drifting light washes.", "Süzülen sıcak ışık sızıntıları."),
    "halation": ("Red film glow at bright edges.", "Parlak kenarlarda kırmızı film ışıması."),
    "haze": ("Soft atmospheric lift; dreamy.", "Yumuşak pus; rüya gibi."),
    "smooth-zoom": ("Slow eased zoom, face kept in frame.", "Yavaş yumuşak zoom, yüz kadrajda."),
    "quick-punch-in": ("Fast push-in to stress a line.", "Bir cümleyi vurgulayan hızlı yakınlaşma."),
    "focus-pull": ("Rack focus soft to sharp.", "Bulanıktan nete odak kaydırma."),
    "directional-blur": ("Motion blur along an angle.", "Bir açı boyunca hareket bulanıklığı."),
    "motion-blur": ("Frame-blend motion trail.", "Kare karışımıyla hareket izi."),
    "film-grain": ("Organic temporal grain.", "Doğal, zamana yayılan gren."),
    "vhs-texture": ("Chroma bleed, noise, tape softness.", "Renk taşması, gürültü, kaset yumuşaklığı."),
    "film-burn": ("Orange burn swelling in and out.", "Gelip giden turuncu film yanığı."),
    "subtle-glitch": ("Sparse RGB-split bursts (≤3/s).", "Seyrek RGB kayma patlamaları (≤3/sn)."),
    "chromatic-shift": ("Constant red/blue channel offset.", "Sabit kırmızı/mavi kanal kayması."),
    "soft-vignette": ("Darkens edges, keeps the face.", "Kenarları karartır, yüzü korur."),
    "letterbox": ("Cinema bars (made for 16:9).", "Sinema bantları (16:9 için)."),
    "beat-flash": ("Short brightness hits on beats.", "Vuruşlarda kısa parlaklık darbeleri."),
    "exposure-balance": ("Gentle, highlight-safe exposure fix.", "Parlak alanı koruyan pozlama düzeltmesi."),
    "noise-reduction": ("Temporal + spatial denoise.", "Zamansal + uzamsal gürültü azaltma."),
}
REELFX = {
    "stage-light": ("The room goes dark, you stay lit.", "Oda kararır, siz aydınlıkta kalırsınız."),
    "press-mono": ("You, printed in tomorrow's paper.", "Yarının gazetesinde siz."),
    "frost-panels": ("Glass cards float beside you.", "Yanınızda buzlu cam kartlar."),
    "duotone-pop": ("Two colours, zero noise.", "İki renk, sıfır gürültü."),
    "scan-line": ("A light beam reads the frame.", "Bir ışık huzmesi kareyi okur."),
    "afterimage": ("Every move leaves a trail.", "Her hareket bir iz bırakır."),
    "halo-orbit": ("A ring of light circles your head.", "Başınızın çevresinde ışık halkası."),
    "neon-outline": ("Neon traces your silhouette.", "Neon silüetinizi çizer."),
    "insight-split": ("Your numbers on top, you below.", "Üstte rakamlar, altta siz."),
    "brand-frame": ("Your clip, framed in your brand.", "Klibiniz, markanızın çerçevesinde."),
    "progress-rail": ("A rail fills as you count steps.", "Adımları saydıkça ray dolar."),
    "pixel-resolve": ("Your shot assembles out of pixels.", "Görüntünüz piksellerden toplanır."),
}
REELFX_CMD = {
    "stage-light": "--source 1.2-3.7 --param y=0.22", "press-mono": "--source 41-47",
    "frost-panels": "--param panels=3", "duotone-pop": "--source 0-1.5",
    "scan-line": "--param speed=0.6", "afterimage": "--param decay=0.9",
    "halo-orbit": "--param y=0.1 --param radius=0.22", "neon-outline": "--param detail=0.5",
    "insight-split": "--param values=0.3,0.55,0.9", "brand-frame": "--param inset=0.84",
    "progress-rail": "--param steps=5", "pixel-resolve": "--source 0-1.2",
}
TEXT = {
    "editorial-fade": ("Soft fade with background dim.", "Arka planı karartan yumuşak geçiş."),
    "minimal-rise": ("Title rises gently and settles.", "Başlık yavaşça yükselip yerleşir."),
    "tracking-reveal": ("Letter spacing eases wide to normal.", "Harf aralığı genişten normale iner."),
    "line-reveal": ("A rule opens under the title.", "Başlığın altında bir çizgi açılır."),
    "chapter-card": ("Full-frame chapter card.", "Tam ekran bölüm kartı."),
    "mask-reveal": ("Footage shows through the letters.", "Görüntü harflerin içinden görünür."),
    "soft-light-sweep": ("A sheen sweeps across the title.", "Başlığın üzerinden parıltı geçer."),
    "depth-title": ("Parallax depth title.", "Derinlikli paralaks başlık."),
    "film-title": ("Title in grain and vignette.", "Gren ve vinyet içinde başlık."),
    "word-pop": ("One word at a time, springy.", "Kelime kelime, yaylı giriş."),
    "staggered-words": ("Words land in sequence; last in accent.", "Kelimeler sırayla iner; sonuncusu vurgulu."),
    "phrase-build": ("Lines build one after another.", "Satırlar art arda kurulur."),
    "type-on": ("Types on with a cursor.", "İmleçle yazılarak gelir."),
    "speaker-label": ("Names the current speaker.", "Konuşan kişiyi adlandırır."),
    "pin-label": ("Dot + label on a point of interest.", "İlgi noktasına nokta + etiket."),
    "logo-reveal": ("Signature brand open/close.", "İmza marka açılışı/kapanışı."),
    "brand-lockup": ("Brand name + tagline from the kit.", "Kitten marka adı + slogan."),
    "end-card": ("Title, subtitle and CTA end card.", "Başlık, alt başlık ve CTA bitiş kartı."),
    "counter-up": ("A number counts up to a value.", "Sayı bir değere kadar sayar."),
    "price-reveal": ("Price pops on a panel; old price optional.", "Fiyat panelde belirir; eski fiyat isteğe bağlı."),
    "stat-emphasis": ("Big figure + label.", "Büyük rakam + etiket."),
    "name-role": ("Name + role lower third.", "İsim + unvan alt bandı."),
    "location-label": ("Pin glyph + place name.", "Konum simgesi + yer adı."),
    "info-bar": ("Full-width info bar.", "Tam genişlikte bilgi bandı."),
    "cta": ("Button-style call to action.", "Düğme biçiminde harekete çağrı."),
}
TRANSITIONS = {
    "zoom-through": ("Punch in to the cut, settle out after it.", "Kesmeye doğru yakınlaş, sonra yerleş."),
    "whip-pan": ("The cut hides in a fast blurred pan.", "Kesme hızlı, bulanık bir kaydırmada saklanır."),
    "light-leak-flash": ("Warm light wash peaks on the cut.", "Sıcak ışık kesmede tepe yapar."),
    "film-burn-flash": ("Orange burn flare hides the cut.", "Turuncu yanık kesmeyi gizler."),
    "glitch-cut": ("Brief RGB split and noise across the cut.", "Kesmede kısa RGB kayması ve gürültü."),
    "dip-to-black": ("Out to black and back in.", "Siyaha çıkıp geri gelir."),
}
REEL_BEATS = [  # (frame, time, EN, TR, tool)
    ("reel-0.3", "0.3 s", "Opener: the shot assembles out of pixels.", "Açılış: görüntü piksellerden toplanır.", "pixel-resolve"),
    ("reel-0.7", "0.7 s", "The pixels resolve into the clean shot.", "Pikseller temiz görüntüye dönüşür.", "pixel-resolve"),
    ("reel-2.6", "2.6 s", "Hook: the room dims, the promise pops in.", "Kanca: oda kararır, vaat belirir.", "stage-light + word-pop"),
    ("reel-3.9", "3.9 s", "First cut, carried by a zoom.", "İlk kesme, zoomla taşınır.", "zoom-through"),
    ("reel-10.5", "10.5 s", "Three takeaways on glass cards.", "Cam kartlarda üç çıkarım.", "frost-panels"),
    ("reel-16.5", "16.5 s", "Proof: bars rise, the number counts up.", "Kanıt: çubuklar yükselir, sayı artar.", "insight-split + counter-up"),
    ("reel-22.5", "22.5 s", "Steps: the rail fills as you count.", "Adımlar: saydıkça ray dolar.", "progress-rail"),
    ("reel-27.5", "27.5 s", "Close: one clear call to action.", "Kapanış: tek ve net bir çağrı.", "cta"),
]
SHOW_BEATS = [
    ("show-0.5", "0.5 s", "Console, your clip in a card.", "Konsol, kartta klibiniz."),
    ("show-1.8", "1.8 s", "The command types itself.", "Komut kendini yazar."),
    ("show-3.1", "3.1 s", "The clip dissolves through pixels.", "Klip piksellerle erir."),
    ("show-5.2", "5.2 s", "The real render fills the screen.", "Gerçek render ekranı doldurur."),
]

T = {
    "en": {
        "real": "Real render", "foot": "Lionstone Pro &amp; Studio v0.3.2", "hb": "Lionstone Reel Handbook",
        "looks_k": "Gallery · looks", "looks_h": "Every look, on the same frame",
        "looks_p": "Real <code>lionstone fx preview</code> renders at default intensity on one clip. Grades are deliberately subtle: they protect skin, so compare neighbours rather than expecting a filter.",
        "fx_k": "Gallery · effects", "fx_h": "The finishing effects, rendered",
        "fx_p": "Each frame is a real preview of the effect at its default settings, captured mid-window.",
        "tr_h": "Transitions, frame by frame", "tr_p": "Before the cut · on the cut · after the cut. Applied with <code>--join N</code>.",
        "text_k": "Gallery · text", "text_h": "Animated text, rendered",
        "text_p": "Captured while each preset is on screen. Placed with <code>lionstone fx text plan.json &lt;id&gt; --text \"…\" --at S</code>.",
        "rfx_k": "Gallery · Reel FX", "rfx_h": "All 12 Reel FX on one clip",
        "rfx_p": "Real renders with the settings shown under each frame: <code>lionstone fx apply plan.json &lt;id&gt; …</code>",
        "px_h": "pixel-resolve, frame by frame", "px_p": "Left to right, about 0.15 s apart: five pixel stages resolve into the clean shot.",
        "show_h": "The real showcase reel", "show_p": "Output of <code>lionstone fx showcase stage-light talk.mp4 --param y=0.22</code>.",
        "reel_k": "Chapter 8 · the result", "reel_h": "The finished Reel, frame by frame",
        "reel_p": "The exact command sequence from the previous pages, rendered on this handbook's presenter clip (1080×1920; QA: deliverable, 17 checks run, 4 skipped and reported). Every frame below is real output; captions are absent only because the test clip has no speech.",
        "orig": "Original",
    },
    "tr": {
        "real": "Gerçek render", "foot": "Lionstone Pro &amp; Studio v0.3.2", "hb": "Lionstone Reels Kitapçığı",
        "looks_k": "Galeri · görünümler", "looks_h": "Tüm görünümler, aynı karede",
        "looks_p": "Tek bir klipte, varsayılan yoğunlukta gerçek <code>lionstone fx preview</code> renderları. Renkler bilerek ölçülüdür, teni korur; filtre beklemek yerine yan yana karşılaştırın.",
        "fx_k": "Galeri · efektler", "fx_h": "Son dokunuş efektleri, render edilmiş",
        "fx_p": "Her kare, efektin varsayılan ayarlarıyla, pencerenin ortasında alınmış gerçek bir önizlemedir.",
        "tr_h": "Geçişler, kare kare", "tr_p": "Kesmeden önce · kesmede · kesmeden sonra. <code>--join N</code> ile uygulanır.",
        "text_k": "Galeri · yazı", "text_h": "Animasyonlu yazı, render edilmiş",
        "text_p": "Her preset ekrandayken yakalandı. Yerleştirme: <code>lionstone fx text plan.json &lt;id&gt; --text \"…\" --at S</code>.",
        "rfx_k": "Galeri · Reel FX", "rfx_h": "Tek klipte 12 Reel FX",
        "rfx_p": "Her karenin altındaki ayarlarla gerçek renderlar: <code>lionstone fx apply plan.json &lt;id&gt; …</code>",
        "px_h": "pixel-resolve, kare kare", "px_p": "Soldan sağa, yaklaşık 0,15 sn arayla: beş piksel aşaması temiz görüntüye dönüşür.",
        "show_h": "Gerçek vitrin videosu", "show_p": "<code>lionstone fx showcase stage-light talk.mp4 --param y=0.22</code> çıktısı.",
        "reel_k": "8. bölüm · sonuç", "reel_h": "Bitmiş Reels, kare kare",
        "reel_p": "Önceki sayfalardaki komut dizisi, bu kitapçığın sunucu klibinde render edildi (1080×1920; QA: teslime hazır, 17 kontrol çalıştı, 4 atlandı ve raporlandı). Yazılar İngilizce örnek metinle verildi. Aşağıdaki her kare gerçek çıktıdır; altyazı yalnızca test klibinde konuşma olmadığı için yok.",
        "orig": "Orijinal",
    },
}


def card(img, title, ident, note, cls=""):
    idh = f'<code>{html.escape(ident)}</code>' if ident else ""
    return (f'<figure class="g {cls}"><img src="img/real/{img}.jpg" alt="">'
            f'<figcaption><b>{title}</b>{idh}<span>{note}</span></figcaption></figure>')


def page(lang, run, kicker, h, p, body, n_hint, dark=False):
    t = T[lang]
    return (f'<section class="page{" dark" if dark else ""}">'
            f'<div class="run"><span><b>{run}</b></span><span>{t["hb"]}</span></div>'
            f'<span class="kicker">{kicker} · <span class="realtag">{t["real"]}</span></span><h2>{h}</h2>'
            f'<p class="lead small-lead">{p}</p>{body}'
            f'<div class="foot"><span>{t["foot"]}</span><span class="pn">{n_hint}</span></div></section>')


def nice(i):
    fixed = {"cta": "CTA", "vhs-texture": "VHS Texture", "look-classic-bw": "Classic B&amp;W",
             "look-true-to-life": "True-to-Life", "rgb-shift-cut": "RGB Shift Cut", "end-card": "End Card",
             "color-controls": "Colour Controls", "dip-to-black": "Dip to Black"}
    return fixed.get(i) or i.replace("look-", "").replace("-", " ").title()


def build(lang):
    t = T[lang]; k = 0 if lang == "en" else 1
    out = {}
    # looks: 28 cards (original + 27) over two pages, 5 cols x 3 rows = 15 per page
    ids = list(LOOKS)
    cards = [card("original" if i == "original" else i, t["orig"] if i == "original" else nice(i),
                  "" if i == "original" else i, LOOKS[i][k], "orig" if i == "original" else "") for i in ids]
    out["looks"] = (page(lang, "04 · " + t["looks_k"], t["looks_k"], t["looks_h"], t["looks_p"],
                         f'<div class="ggrid c5">{"".join(cards[:15])}</div>', "")
                    + page(lang, "04 · " + t["looks_k"], t["looks_k"], t["looks_h"] + " (2)", t["looks_p"],
                           f'<div class="ggrid c5">{"".join(cards[15:])}</div>', ""))
    fx = [card(i, nice(i), i, v[k]) for i, v in EFFECTS.items()]
    trs = "".join(
        f'<div class="trow"><div class="tlabel"><b>{nice(i)}</b><code>{i}</code><span>{v[k]}</span></div>'
        + "".join(f'<img src="img/real/seq-{i}-{s}.jpg" alt="">' for s in ("1.6", "2.0", "2.4")) + "</div>"
        for i, v in TRANSITIONS.items())
    out["effects"] = (page(lang, "05 · " + t["fx_k"], t["fx_k"], t["fx_h"], t["fx_p"],
                           f'<div class="ggrid c5">{"".join(fx[:15])}</div>', "")
                      + page(lang, "05 · " + t["fx_k"], t["fx_k"], t["fx_h"] + " (2)", t["fx_p"],
                             f'<div class="ggrid c5">{"".join(fx[15:])}</div><h3>{t["tr_h"]}</h3>'
                             f'<p class="small">{t["tr_p"]}</p><div class="tgrid">{trs}</div>', ""))
    tx = [card(i, nice(i), i, v[k]) for i, v in TEXT.items()]
    out["text"] = (page(lang, "06 · " + t["text_k"], t["text_k"], t["text_h"], t["text_p"],
                        f'<div class="ggrid c5">{"".join(tx[:15])}</div>', "")
                   + page(lang, "06 · " + t["text_k"], t["text_k"], t["text_h"] + " (2)", t["text_p"],
                          f'<div class="ggrid c5">{"".join(tx[15:])}</div>', ""))
    rf = [card(i, nice(i), i, f'{v[k]}<em>{REELFX_CMD[i]}</em>') for i, v in REELFX.items()]
    px = "".join(f'<img src="img/real/px-{s}.jpg" alt="">' for s in ("0.5", "0.75", "0.88", "1.0", "1.15"))
    out["reelfx"] = page(lang, "07 · " + t["rfx_k"], t["rfx_k"], t["rfx_h"], t["rfx_p"],
                         f'<div class="ggrid c6">{"".join(rf)}</div><h3>{t["px_h"]}</h3>'
                         f'<p class="small">{t["px_p"]}</p><div class="strip s5">{px}</div>', "", dark=True)
    sb = "".join(card(f, tm, "", n_en if lang == "en" else n_tr) for f, tm, n_en, n_tr in SHOW_BEATS)
    out["showcase"] = f'<h3>{t["show_h"]} · <span class="realtag">{t["real"]}</span></h3><p class="small">{t["show_p"]}</p><div class="ggrid c4">{sb}</div>'
    rb = "".join(card(f, tm, tool, (en if lang == "en" else tr)) for f, tm, en, tr, tool in REEL_BEATS)
    out["reel"] = page(lang, "08 · " + t["reel_k"], t["reel_k"], t["reel_h"], t["reel_p"],
                       f'<div class="ggrid c4 big">{rb}</div>', "")
    return out


def number_pages(src):
    """Number every page footer in order and fill TOC entries (data-to) from data-ch."""
    parts = re.split(r'(?=<section )', src)
    chap = {}
    for i, part in enumerate(parts[1:], start=1):
        m = re.search(r'data-ch="(\d+)"', part[:200])
        if m:
            chap[m.group(1)] = i
        parts[i] = re.sub(r'<span class="pn">[^<]*</span>', f'<span class="pn">{i}</span>', part)
    src = "".join(parts)
    return re.sub(r'<span class="p" data-to="(\d+)">[^<]*</span>',
                  lambda m: f'<span class="p">{chap[m.group(1)]}</span>', src)


def main():
    (HERE / "build").mkdir(exist_ok=True)
    for lang in ("en", "tr"):
        src = (HERE / f"{lang}.html").read_text(encoding="utf-8")
        for key, frag in build(lang).items():
            marker = f"<!--GALLERY:{key}-->"
            assert marker in src, (lang, marker)
            src = src.replace(marker, frag)
        # paths are relative to src/, the build lives one level down
        src = src.replace('href="handbook.css"', 'href="../handbook.css"').replace('src="img/', 'src="../img/')
        src = number_pages(src)
        (HERE / "build" / f"{lang}.html").write_text(src, encoding="utf-8")


if __name__ == "__main__":
    main()
