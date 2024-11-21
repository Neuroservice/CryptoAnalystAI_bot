import logging
import textwrap

from io import BytesIO
from fpdf import FPDF
from matplotlib import pyplot as plt


class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Data Report', 0, 1, 'C')

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')


def create_pdf_file(data, additional_headers):
    pdf = FPDF()
    pdf.add_page()

    pdf.add_font("DejaVu", '', 'D:\\dejavu-fonts-ttf-2.37\\ttf\\DejaVuSansCondensed.ttf', uni=True)
    # pdf.add_font("DejaVu", '', '/app/fonts/DejaVuSansCondensed.ttf', uni=True)
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
                    if size_str == '-':  # Пропускаем, если размер '-'
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
