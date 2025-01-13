import logging
import textwrap

from io import BytesIO

from PIL import Image
from PIL import ImageDraw
from fpdf import FPDF
from matplotlib import pyplot as plt

from bot.utils.consts import dejavu_path


class PDF(FPDF):
    def __init__(self, logo_path=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logo_path = logo_path
        self.footer_logo_path = None
        if self.logo_path:
            self.footer_logo_path = self._create_round_logo(self.logo_path)

    def _create_round_logo(self, path):
        """Обрезает изображение в форме круга и сохраняет его временно."""
        img = Image.open(path).convert("RGBA")
        size = min(img.size)
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        circular_img = Image.new("RGBA", (size, size))
        circular_img.paste(img, (0, 0, size, size), mask)
        temp_path = "temp_footer_logo.png"
        circular_img.save(temp_path, "PNG")
        return temp_path

    def header(self):
        """Добавление логотипа в верхний левый угол каждой страницы."""
        if self.footer_logo_path:
            self.image(self.footer_logo_path, x=193, y=5, w=10)  # Логотип в верхнем левом углу


def create_pdf_file(data, additional_headers):
    pdf = FPDF()
    pdf.add_page()

    pdf.add_font("DejaVu", '', dejavu_path, uni=True)
    # pdf.add_font("DejaVu", '', dejavu_path, uni=True)
    pdf.set_font("DejaVu", size=12)

    for header in additional_headers:
        pdf.cell(40, 10, header, 1)
    pdf.ln()

    for row in data:
        for value in row:
            pdf.cell(40, 10, str(value), 1)
        pdf.ln()

    return pdf


def generate_pie_chart(distribution):
    labels = []
    sizes = []

    try:
        float(distribution.strip().strip('%'))
        labels = ["Funds"]
        sizes = [100]
    except ValueError:
        items = distribution.split('\n')

        if len(items) == 1:
            items = distribution.split(') ')
            items = [item + ')' if '(' in item and ')' not in item else item for item in items]

        for item in items:
            if '(' in item and ')' in item:
                label = item[:item.rfind('(')].strip()
                size_str = item[item.rfind('(') + 1:item.rfind(')')].strip('%').strip()
                try:
                    if size_str == '-':
                        logging.warning(f"Пропущен элемент '{label}' из-за некорректного размера '{size_str}'.")
                        continue

                    size = float(size_str)
                except ValueError:
                    raise ValueError(f"Не удалось преобразовать размер '{size_str}' в число.")
                labels.append(label)
                sizes.append(size)

    fig, ax = plt.subplots(figsize=(13, 10))
    wedges, texts = ax.pie(sizes, startangle=90, wedgeprops=dict(width=1))
    wrapped_labels = [textwrap.fill(f'{label} - {size:.1f}%', width=30) for label, size in zip(labels, sizes)]
    ax.legend(wedges, wrapped_labels, loc="center left", bbox_to_anchor=(1, 0, 0.9, 1), fontsize=25)

    ax.axis('equal')
    plt.tight_layout()

    pie_chart_img = BytesIO()
    plt.savefig(pie_chart_img, format='PNG')
    pie_chart_img.seek(0)
    plt.close(fig)

    return pie_chart_img
