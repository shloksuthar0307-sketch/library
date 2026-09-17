import csv
import io
from datetime import datetime, date, timedelta
from django.utils import timezone
from django.db.models import Q
from books.models import Book
from members.models import MemberProfile
from transactions.models import Transaction
from reservations.models import Reservation
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from django.core.mail import EmailMessage

class ReportGenerationService:
    @staticmethod
    def get_queryset(model_type, filters, request_user=None):
        if model_type == 'transactions':
            qs = Transaction.objects.all()
            if request_user and request_user.role == 'STAFF' and request_user.branch_id and not request.user.can_access_all_branches:
                qs = qs.filter(Q(branch=request_user.branch) | Q(branch__isnull=True))
            qs = qs.select_related('book', 'member', 'member__member_profile')
        elif model_type == 'books':
            qs = Book.objects.all()
        elif model_type == 'members':
            qs = MemberProfile.objects.all().select_related('user')
        elif model_type == 'reservations':
            qs = Reservation.objects.all().select_related('book', 'member')
        else:
            return None

        # Apply basic dynamic filters
        if 'date_range' in filters:
            days = int(filters['date_range'])
            cutoff = timezone.now() - timedelta(days=days)
            if model_type == 'transactions':
                qs = qs.filter(issue_date__gte=cutoff)
                
        if 'status' in filters and filters['status'] != 'ALL':
            qs = qs.filter(status=filters['status'])
            
        return qs.order_by('-id')[:1000] # Cap at 1000 for safety

class ExportService:
    @staticmethod
    def sanitize_csv_cell(value):
        if not isinstance(value, str):
            value = str(value)
        # Prevent CSV injection by escaping starting characters that trigger formulas
        if value and value[0] in ['=', '+', '-', '@']:
            return f"'{value}"
        return value

    @staticmethod
    def generate_csv(queryset, model_type, columns=None):
        output = io.StringIO()
        writer = csv.writer(output)
        
        if model_type == 'transactions':
            writer.writerow(['ID', 'Book Title', 'Member Name', 'Issue Date', 'Due Date', 'Return Date', 'Status', 'Fine Amount'])
            for txn in queryset:
                writer.writerow([
                    txn.id,
                    ExportService.sanitize_csv_cell(txn.book.title if txn.book else "N/A"),
                    ExportService.sanitize_csv_cell(txn.member.get_full_name() or txn.member.username if txn.member else "N/A"),
                    txn.issue_date.strftime("%Y-%m-%d") if txn.issue_date else "",
                    txn.due_date.strftime("%Y-%m-%d") if txn.due_date else "",
                    txn.return_date.strftime("%Y-%m-%d") if txn.return_date else "",
                    ExportService.sanitize_csv_cell(txn.status),
                    txn.fine_amount
                ])
        elif model_type == 'books':
            writer.writerow(['ID', 'Title', 'ISBN', 'Author', 'Available Copies'])
            for b in queryset:
                writer.writerow([
                    b.id, 
                    ExportService.sanitize_csv_cell(b.title), 
                    ExportService.sanitize_csv_cell(b.isbn), 
                    ExportService.sanitize_csv_cell(b.author), 
                    b.available_copies
                ])
                
        return output.getvalue()

    @staticmethod
    def generate_pdf(queryset, model_type, title="Library Report"):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
        elements = []
        styles = getSampleStyleSheet()
        
        elements.append(Paragraph(title, styles['Title']))
        elements.append(Paragraph(f"Generated at: {timezone.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 20))
        
        data = []
        if model_type == 'transactions':
            data.append(['ID', 'Book Title', 'Member Name', 'Issue Date', 'Status', 'Fine'])
            for txn in queryset:
                data.append([
                    str(txn.id),
                    (txn.book.title[:30] + '...') if txn.book and len(txn.book.title) > 30 else (txn.book.title if txn.book else "N/A"),
                    txn.member.get_full_name() or txn.member.username if txn.member else "N/A",
                    txn.issue_date.strftime("%Y-%m-%d") if txn.issue_date else "",
                    txn.status,
                    str(txn.fine_amount)
                ])
                
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6'))
        ]))
        
        elements.append(table)
        doc.build(elements)
        buffer.seek(0)
        return buffer.read()

class EmailService:
    @staticmethod
    def send_report(scheduled_report, file_content, file_name, mime_type):
        email = EmailMessage(
            subject=f"Library Report — {scheduled_report.name}",
            body=f"Your scheduled library report is ready.\n\nReport: {scheduled_report.name}\nGenerated: {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            from_email='reports@library.com',
            to=[email.strip() for email in scheduled_report.recipients.split(',') if email.strip()]
        )
        email.attach(file_name, file_content, mime_type)
        email.send()
