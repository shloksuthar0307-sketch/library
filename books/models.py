from django.db import models

from organizations.managers import TenantManager
from config.utils import GenerateSafeFilename


class Category(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="categories",
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_date = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()

    class Meta:
        verbose_name_plural = "Categories"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="uniq_category_name_per_organization",
            )
        ]

    def __str__(self):
        return self.name


class Author(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="authors",
    )
    name = models.CharField(max_length=150)
    biography = models.TextField(blank=True)
    photo = models.ImageField(upload_to=GenerateSafeFilename("authors/"), null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()

    def __str__(self):
        return self.name


class Publisher(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="publishers",
    )
    name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    created_date = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()

    def __str__(self):
        return self.name


class Book(models.Model):
    STATUS_CHOICES = (
        ("AVAILABLE", "Available"),
        ("ISSUED", "Issued"),
        ("RESERVED", "Reserved"),
        ("UNAVAILABLE", "Unavailable"),
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="books",
    )
    title = models.CharField(max_length=255)
    isbn = models.CharField(max_length=13, verbose_name="ISBN Number")
    description = models.TextField(blank=True)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="books")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="books")
    publisher = models.ForeignKey(Publisher, on_delete=models.SET_NULL, null=True, related_name="books")
    publication_year = models.PositiveIntegerField(null=True, blank=True)
    language = models.CharField(max_length=50, blank=True)
    edition = models.CharField(max_length=50, blank=True)

    total_copies = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)

    cover_image = models.ImageField(upload_to=GenerateSafeFilename("books/covers/"), null=True, blank=True)
    shelf_number = models.CharField(max_length=50, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="AVAILABLE")

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "isbn"],
                name="uniq_isbn_per_organization",
                condition=~models.Q(isbn=""),
            )
        ]
        indexes = [
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.available_copies == 0 and self.status == "AVAILABLE":
            self.status = "UNAVAILABLE"
        elif self.available_copies > 0 and self.status == "UNAVAILABLE":
            self.status = "AVAILABLE"
        super().save(*args, **kwargs)

    def sync_copy_counts(self):
        copies = self.copies.all()
        if copies.exists():
            self.total_copies = copies.count()
            self.available_copies = copies.filter(status=BookCopy.Status.AVAILABLE, is_available=True).count()
            self.save(update_fields=["total_copies", "available_copies", "status", "updated_date"])


class BookCopy(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        ISSUED = "ISSUED", "Issued"
        RESERVED = "RESERVED", "Reserved"
        LOST = "LOST", "Lost"
        DAMAGED = "DAMAGED", "Damaged"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        ARCHIVED = "ARCHIVED", "Archived"

    class Condition(models.TextChoices):
        NEW = "NEW", "New"
        GOOD = "GOOD", "Good"
        FAIR = "FAIR", "Fair"
        POOR = "POOR", "Poor"

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="copies")
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="book_copies",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="book_copies",
    )
    barcode = models.CharField(max_length=64)
    accession_number = models.CharField(max_length=64, blank=True)
    shelf_location = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.GOOD)
    acquired_date = models.DateField(null=True, blank=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        verbose_name_plural = "Book copies"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "barcode"],
                name="uniq_barcode_per_organization",
            )
        ]

    def save(self, *args, **kwargs):
        if not self.organization_id and self.book_id:
            self.organization_id = self.book.organization_id
        self.is_available = self.status == self.Status.AVAILABLE
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.book.title} [{self.barcode}]"

class DigitalAsset(models.Model):
    book = models.OneToOneField(Book, on_delete=models.CASCADE, related_name="digital_asset")
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="digital_assets",
    )
    file = models.FileField(upload_to=GenerateSafeFilename("digital_books/"))
    format = models.CharField(max_length=10, choices=[('PDF', 'PDF'), ('EPUB', 'EPUB')])
    file_size_bytes = models.PositiveIntegerField(default=0)
    requires_drm = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    objects = TenantManager()

    def save(self, *args, **kwargs):
        if not self.organization_id and self.book_id:
            self.organization_id = self.book.organization_id
        if self.file and not self.file_size_bytes:
            self.file_size_bytes = self.file.size
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Digital: {self.book.title} ({self.format})"
