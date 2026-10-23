"""Xuất PDF Unicode tiếng Việt cho các phiên EmotionAI đã được phân quyền."""
from io import BytesIO
from pathlib import Path
import json
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether


def _register_font():
    candidates = [
        Path('C:/Windows/Fonts/arial.ttf'),
        Path('C:/Windows/Fonts/tahoma.ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
        Path('/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf'),
    ]
    for path in candidates:
        if path.is_file():
            if 'EmotionAIViet' not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont('EmotionAIViet', str(path)))
            return 'EmotionAIViet'
    raise FileNotFoundError('Không tìm thấy font hỗ trợ tiếng Việt. Trên Windows cần Arial hoặc Tahoma.')


def _p(text, style):
    return Paragraph(escape(str(text if text is not None else '—')).replace('\n', '<br/>'), style)


def build_patient_report_pdf(patient, sessions):
    """Nhận dữ liệu bệnh nhân đã được lọc quyền ở Dashboard, trả về bytes PDF."""
    if not patient or not sessions:
        raise ValueError('Cần chọn bệnh nhân có ít nhất một phiên đã lưu.')
    patient_id = patient['id']
    if any(s.get('patient_id') != patient_id for s in sessions):
        raise PermissionError('Dữ liệu phiên không thuộc bệnh nhân đang chọn.')
    font = _register_font()
    styles = getSampleStyleSheet()
    body = ParagraphStyle('EmotionBody', parent=styles['Normal'], fontName=font, fontSize=9, leading=15, spaceAfter=5)
    title = ParagraphStyle('EmotionTitle', parent=body, fontSize=16, leading=23, alignment=TA_CENTER, spaceAfter=10, textColor=colors.HexColor('#173b70'))
    h2 = ParagraphStyle('EmotionHeading', parent=body, fontSize=11, leading=17, spaceBefore=10, spaceAfter=6, textColor=colors.HexColor('#173b70'))
    small = ParagraphStyle('EmotionSmall', parent=body, fontSize=8, leading=12, textColor=colors.HexColor('#555555'))
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=(210*mm, 297*mm), leftMargin=18*mm, rightMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
    story = [
        _p('EMOTIONAI - BÁO CÁO PHÂN TÍCH CẢM XÚC', title),
        _p('Báo cáo hỗ trợ bác sĩ tâm lý - không phải chẩn đoán y khoa', small),
        Spacer(1, 6*mm),
        _p(f"Mã bệnh nhân: {patient.get('patient_code', '')}", body),
        _p(f"Tên hiển thị: {patient.get('display_name', '')}", body),
        _p(f"Số phiên trong báo cáo: {len(sessions)}", body),
    ]
    for session in sorted(sessions, key=lambda x: (x.get('created_at') or '', x['id'])):
        parts = [
            _p(f"Phiên #{session['id']} - {session.get('created_at', '')}", h2),
            _p(f"Nhận xét AI: {session.get('ai_label', '—')}", body),
            _p(session.get('ai_detail', ''), body),
        ]
        try:
            results = json.loads(session.get('results_json') or '{}')
        except (TypeError, ValueError):
            results = {}
        entries = []
        if 'face' in results:
            entries.append(('Khuôn mặt', results['face'].get('emotion', '—')))
        if 'voice' in results:
            entries.append(('Giọng nói', results['voice'].get('emotion', '—')))
        if 'heart' in results:
            heart = results['heart']
            entries.append(('Nhịp tim', f"{heart.get('bpm', '—')} BPM - {heart.get('status', '')}"))
        if entries:
            data = [[_p('Nguồn', body), _p('Kết quả', body)]] + [[_p(a, body), _p(b, body)] for a,b in entries]
            table = Table(data, colWidths=[43*mm, 125*mm], repeatRows=1, hAlign='LEFT')
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#eaf1fb')),
                ('GRID', (0,0), (-1,-1), .35, colors.HexColor('#d4deea')),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), 7),
                ('RIGHTPADDING', (0,0), (-1,-1), 7),
            ]))
            parts.append(table)
        if session.get('phq9_score') is not None:
            parts.append(_p(f"PHQ-9: {session['phq9_score']}/27 - {session.get('phq9_band', '')}", body))
            if (session.get('phq9_item9') or 0) > 0:
                parts.append(_p('LƯU Ý: Câu 9 PHQ-9 khác 0; cần đánh giá an toàn trực tiếp.', body))
        parts += [
            _p(f"Bác sĩ/người đánh giá: {session.get('doctor_name', '')}", body),
            _p(f"Nhận định: {session.get('assessment', '')}", body),
            _p(f"Ghi chú chuyên môn: {session.get('doctor_notes', '')}", body),
            Spacer(1, 3*mm),
        ]
        story.extend(parts)
    story.append(_p('LƯU Ý: Kết quả AI là dự đoán từ tín hiệu, PHQ-9 là sàng lọc; không thay thế đánh giá chuyên môn. Chỉ chia sẻ báo cáo với người có thẩm quyền.', small))
    doc.build(story)
    return buffer.getvalue()
