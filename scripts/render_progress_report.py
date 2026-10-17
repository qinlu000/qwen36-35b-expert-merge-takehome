#!/usr/bin/env python3
"""Draw a one-page progress draft from retained receipts; no model/API calls."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
ABSTRACT = ('本实验研究以四类任务训练专家，再以参数合版兼顾代码修复、终端交互、学术推理与科研编程。'
            '四个专家和同源混训对照均已完成监督训练，等权平均主模型已经冻结。'
            '代码修复专家完整评测零通过，科研专家低于基座；学术专家取得提升，不报告总体提升。'
            '实测冲突消解合版的低秩回投影误差较大，已完成完整权重导出。'
            '实验保留资源预算、替代判分和调度差异，损失仅作训练诊断。'
            '后续收齐任务结果、配对区间与最终成本，未决项如实列出。')
NAVY = colors.HexColor('#18354A')
TEAL = colors.HexColor('#23696A')
GRAY = colors.HexColor('#586976')
PALE = colors.HexColor('#F1F5F6')
LINE = colors.HexColor('#DCE4E8')


def load(name):
    return json.loads((ROOT / name).read_text())


def render(output, font):
    han_count = len(re.findall(r'[\u3400-\u4dbf\u4e00-\u9fff]', ABSTRACT))
    assert 150 <= han_count <= 200
    pdfmetrics.registerFont(TTFont('Chinese', str(font)))
    training = load('configs/train/four_experts_v1.json')
    formal_receipt = load('analysis/source_snapshots/formal_aggregation_20261017_1115.json')
    formal = formal_receipt['views']['strict']
    budget_terminal = formal_receipt['views']['audited_terminal_budget']['models']['base']['benchmarks']['terminal']
    merge = load('analysis/source_snapshots/merge_export_20261017.json')
    dense_export = load('analysis/source_snapshots/ties_dense_export_728007_20261017.json')
    publication = load('analysis/source_snapshots/hf_publication_20261017.json')
    github = load('analysis/source_snapshots/github_repository_20261017.json')
    assert merge['status'] == 'exported_and_serialized_delta_verified'
    assert dense_export['state'] == 'export_complete_verified'
    assert dense_export['verified_checks']['real_weight_svd_calls'] == 0
    assert publication['state'] == 'all_five_public_anonymous_verified'
    assert len(publication['artifacts']) == 5 and github['private'] is True
    generated = datetime.now(ZoneInfo('Asia/Shanghai'))
    output.parent.mkdir(parents=True, exist_ok=True)
    page_w, page_h = A4
    margin = 37
    width = page_w - 2 * margin
    pdf = canvas.Canvas(str(output), pagesize=A4)
    pdf.setTitle('多专家SFT与参数合版：阶段性草稿')
    pdf.setAuthor('Qwen expert merge experiment')
    pdf.setSubject('阶段性草稿；正式评测未齐备；不是最终report.pdf')
    y = page_h - 39
    used_text = [ABSTRACT]

    def paragraph(text, size=9.0, leading=13.2, color=NAVY, after=5):
        nonlocal y
        used_text.append(re.sub('<[^>]+>', '', text))
        style = ParagraphStyle('body', fontName='Chinese', fontSize=size, leading=leading,
                               textColor=color, wordWrap='CJK', spaceAfter=0)
        item = Paragraph(text, style)
        _, height = item.wrap(width, page_h)
        item.drawOn(pdf, margin, y - height)
        y -= height + after

    def section(text):
        nonlocal y
        y -= 5
        pdf.setStrokeColor(LINE)
        pdf.line(margin, y, page_w - margin, y)
        y -= 17
        paragraph(text, size=10.0, leading=13, color=TEAL, after=5)

    def table(rows, widths, row_height=23):
        nonlocal y
        for row in rows:
            used_text.extend(str(cell) for cell in row)
        style = ParagraphStyle('cell', fontName='Chinese', fontSize=8.5, leading=11,
                               alignment=TA_CENTER, textColor=NAVY, wordWrap='CJK')
        cells = [[Paragraph(escape(str(cell)).replace('\n', '<br/>'), style) for cell in row]
                 for row in rows]
        item = Table(cells, colWidths=widths, rowHeights=[row_height] * len(rows))
        item.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PALE),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFB')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), .6, LINE),
            ('INNERGRID', (0, 0), (-1, -1), .4, LINE),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        _, height = item.wrap(width, page_h)
        item.drawOn(pdf, margin, y - height)
        y -= height + 7

    pdf.setFont('Chinese', 19)
    pdf.setFillColor(NAVY)
    pdf.drawString(margin, y, '多专家 SFT 与参数合版')
    pdf.setFont('Chinese', 9.2)
    pdf.setFillColor(TEAL)
    pdf.drawRightString(page_w - margin, y + 1, '阶段性草稿')
    y -= 22
    paragraph('Qwen3.6-35B-A3B  |  四专家 + Mixed 对照  |  AVG64 主模型 / TIES 方法推进',
              size=8.3, leading=12, color=GRAY, after=9)

    paragraph('摘要', size=10, color=TEAL, after=3)
    paragraph(ABSTRACT, size=9.1, leading=13.4, after=3)

    section('过程  |  五个训练完成，合版配方已冻结')
    rows = {row['name']: row for row in training['experts']}
    counts = '；'.join(f'{label}{rows[key]["native_loaded_train_rows"]}/{rows[key]["native_loaded_val_rows"]}'
                       for key, label in [('swe', 'SWE'), ('terminal', 'Terminal'), ('hle', 'HLE'), ('asi', 'ASI')])
    paragraph(f'原生 train/诊断留出：{counts}；Mixed 7066/249。五个一轮训练均完成；'
              '共享 LoRA r16/alpha32、BF16、global batch8、64K、非thinking。SWE原2000条中7条角色配对过滤，Mixed继承同样过滤。')
    paragraph('AVG64将四专家真实更新各按0.25平均，以rank64拼接精确保存；AVG16只作辅助压缩。'
              'TIES试跑回投影误差30%-57%，未导出该近似；TIES-Dense已完整导出，无SVD，'
              f'BF16相对更新误差{100*dense_export["global_rounding"]["effective_update_deviation_relative_to_delta"]:.2f}%。'
              '主AVG64及答卷不变，不按正式分数择优；loss仅作诊断。', after=1)

    section('结果  |  正式 4 × 6 矩阵待齐备')
    model_ids = ['base', 'swe249', 'hle250', 'asi128', 'terminal250', 'avg64']
    matrix = [['完整范围', 'Base', 'SWE专家', 'HLE专家', 'ASI专家', '终端专家', 'AVG64']]
    for benchmark, label in [('swe', 'SWE HARD-51'), ('hle', 'HLE 2500'),
                             ('asi', 'ASI 60 × 4'), ('terminal', 'TB 89 × 5')]:
        row = [label]
        for model in model_ids:
            metric = formal['models'][model]['benchmarks'].get(benchmark)
            if metric is None:
                row.append('未评')
            elif metric['complete'] and metric['primary_score_percent'] is not None:
                row.append(f'{metric["primary_score_percent"]:.3f}%')
            else:
                row.append('待齐备')
        matrix.append(row)
    table(matrix, [96] + [(width - 96) / 6] * 6, row_height=23)
    swe_ci = formal['comparisons']['avg64_vs_base']['benchmarks']['swe']['delta_ci95_percent_points']
    paragraph(f'SWE完整：Base10/51、专家0/51、AVG4/51；AVG较Base -11.765pp，95%CI[{swe_ci["lower"]:.3f},{swe_ci["upper"]:.3f}]。'
              '专家50 native+1官方报告审计；AVG45 native+6逐项native审计。原invalid不覆盖。',
              size=8.1, leading=11.7, color=GRAY, after=2)
    asi_ci = formal['comparisons']['asi128_vs_base']['benchmarks']['asi']['delta_ci95_percent_points']
    paragraph(f'ASI专家0.379%低于Base1.571%，差-1.192pp，配对95%CI[{asi_ci["lower"]:.3f},{asi_ci["upper"]:.3f}]；'
              '均为240条件公开local原生聚合。未评为专家非目标项；四项宏平均与提升仍待齐备，不以部分coverage估分。',
              size=8.1, leading=11.7, color=GRAY, after=2)
    paragraph(f'BaseTB独立预算{budget_terminal["primary_score_percent"]:.6f}%，'
              f'{budget_terminal["native_valid"]} native+{budget_terminal["derived_timeout"]}审计超时派生0，raw null不变。',
              size=8.1, leading=11.7, color=GRAY, after=2)

    section('已完整的 HLE 任务结果  |  同2500题、含342张图')
    ids = ['base', 'hle250', 'mixed883', 'avg64', 'avg16']
    hle = [formal['models'][name]['benchmarks']['hle'] for name in ids]
    assert all(row['complete'] for row in hle)
    table([['完整HLE', 'Base', 'HLE专家', 'Mixed对照', 'AVG64', 'AVG16'],
           ['准确率', *[f'{row["primary_score_percent"]:.2f}%' for row in hle]]],
          [width / 6] * 6, row_height=22)
    ci = formal['comparisons']['hle250_vs_base']['benchmarks']['hle']['delta_ci95_percent_points']
    avg_ci = formal['comparisons']['avg64_vs_base']['benchmarks']['hle']['delta_ci95_percent_points']
    paragraph(f'专家较Base +2.96pp，配对95%CI [{ci["lower"]:.2f}, {ci["upper"]:.2f}]；'
              f'AVG64 +0.72pp [{avg_ci["lower"]:.2f}, {avg_ci["upper"]:.2f}]，尚不足确认稳定提升。'
              'Base/专家/Mixed/AVG原生无答1445/30/41/1196，历史服务混杂未消除，不能单独归因权重。'
              '固定名单Judge截断作一次格式恢复，原答卷不变，显式披露2+1例外。'
              'TIES全2500生成、2499有效，1项缺正确性字段仍未决，完整方法分差暂缺。',
              size=8.1, leading=11.7, color=GRAY, after=1)

    section('协议边界与交付')
    paragraph('实际统一64K/8K、非thinking；Terminal为30min/4CPU/8GiB，低于原题3h/32CPU/48GB/256K/80K，'
              '尚无例外批准。SWE为30min；HLE/ASI使用披露的替代Judge，ASI为公开local，服务并发差异仍保留。',
              size=8.5, leading=12.3, after=4)
    paragraph('11:11资源账本：结束241.294 GPUh，在跑4卡暂计26.998 GPUh；API核算15.0291 CNY另0.3283 USD，'
              '含保留reservation、非发票，HPC单价未知。', size=8.1, leading=11.7, color=GRAY, after=3)
    paragraph('已交付：五个Public HF adapter已匿名完整下载核对；Private GitHub已创建并推送默认master。'
              '模型链接与不可变revision见models/README.md。', size=8.5, leading=12.3, after=4)
    paragraph('已整理20个真实失败及3项后续实验。待完成：完整评分 / TIES任务对照 / 最终成本与离线资产。',
              size=9.0, leading=13, color=TEAL, after=0)

    assert y > 91, f'Page content reaches footer: y={y}'
    pdf.setStrokeColor(LINE)
    pdf.line(margin, 79, page_w - margin, 79)
    footer = [
        '阶段性草稿，不是最终 report.pdf；生成 ' + generated.strftime('%Y-%m-%d %H:%M:%S CST') + '  |  1 / 1',
        '结果收据：analysis/source_snapshots/formal_aggregation_20261017_1115.json（11:14 CST，strict与预算分开）',
        '方法：analysis/merge_method_decision_20261017.md；失败：analysis/avg64_failure_cases_20261017.md',
        '发布收据：analysis/source_snapshots/hf_publication_20261017.json；github_repository_20261017.json',
    ]
    pdf.setFont('Chinese', 6.7)
    pdf.setFillColor(GRAY)
    for i, line in enumerate(footer):
        used_text.append(line)
        pdf.drawString(margin, 65 - i * 10, line)
    missing = sorted({char for text in used_text for char in text
                      if not char.isspace() and ord(char) not in pdfmetrics.getFont('Chinese').face.charToGlyph})
    assert not missing, f'Font glyphs missing: {missing}'
    pdf.showPage()
    pdf.save()
    reader = PdfReader(output)
    assert len(reader.pages) == 1
    fonts = reader.pages[0]['/Resources']['/Font']
    chinese = [value.get_object() for value in fonts.values()
               if 'ArialUnicodeMS' in str(value.get_object().get('/BaseFont'))]
    assert chinese and all('/FontFile2' in row['/FontDescriptor'] for row in chinese)
    print(json.dumps({'output': str(output), 'generated_at': generated.isoformat(), 'pages': len(reader.pages),
                      'abstract_han_characters': han_count, 'abstract_all_characters': len(ABSTRACT),
                      'embedded_chinese_font': str(font), 'font_missing_glyphs': missing,
                      'content_bottom_y': round(y, 2), 'formal_snapshot': formal['as_of_utc'],
                      'hle_scores': dict(zip(ids, [row['primary_score_percent'] for row in hle]))}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'output/pdf/progress_report_20261017.pdf')
    parser.add_argument('--font', type=Path, default=Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf'))
    args = parser.parse_args()
    render(args.output.resolve(), args.font)
