"""Печатный шаблон клавиатуры 1:1 — A4 альбомная, по 8 белых клавиш на лист, начиная с «до».
Белая 30×150 мм, чёрная 17×95 мм. python keys/key_template.py out.pdf [pages]"""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_pdf import PdfPages

W, L, BW, BL = 30.0, 150.0, 17.0, 95.0           # мм
PER_PAGE, PAGES = 8, int(sys.argv[2]) if len(sys.argv) > 2 else 4
NAMES = ["до", "ре", "ми", "фа", "соль", "ля", "си"]
HAS_SHARP = {0, 1, 3, 4, 5}                        # после ми и си чёрных нет
out = sys.argv[1] if len(sys.argv) > 1 else "keys/keyboard_template.pdf"
with PdfPages(out) as pdf:
    for page in range(PAGES):
        fig = plt.figure(figsize=(297 / 25.4, 210 / 25.4))
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 297); ax.set_ylim(0, 210); ax.axis("off")
        x0, y0 = (297 - PER_PAGE * W) / 2, 35
        for i in range(PER_PAGE):
            idx = page * PER_PAGE + i
            x = x0 + i * W
            ax.add_patch(Rectangle((x, y0), W, L, fill=False, lw=2.2, ec="black"))
            ax.text(x + W / 2, y0 - 6, NAMES[idx % 7], ha="center", va="top", fontsize=9, color="black")
            if idx % 7 == 0:
                ax.text(x + W / 2, y0 - 14, f"октава {idx // 7 + 1}", ha="center", va="top", fontsize=7, color="gray")
        for i in range(PER_PAGE):
            idx = page * PER_PAGE + i
            if idx % 7 in HAS_SHARP and i < PER_PAGE - 1 or (idx % 7 in HAS_SHARP and i == PER_PAGE - 1):
                x = x0 + (i + 1) * W - BW / 2
                ax.add_patch(Rectangle((x, y0 + L - BL), BW, BL, fc="black", ec="black"))
        ax.plot([x0 - 5, x0 - 5], [y0 - 20, y0 + L + 5], color="gray", lw=0.5, ls="--")
        ax.plot([x0 + PER_PAGE * W + 5] * 2, [y0 - 20, y0 + L + 5], color="gray", lw=0.5, ls="--")
        ax.text(148.5, 200, f"Souls of Muse · клавиатура 1:1 · лист {page + 1} из {PAGES} · клавиши {page*PER_PAGE+1}–{(page+1)*PER_PAGE} · "
                "склеивать встык по пунктиру, половинки чёрных на стыках совпадают", ha="center", va="top", fontsize=8, color="gray")
        pdf.savefig(fig); plt.close(fig)
print(out)
