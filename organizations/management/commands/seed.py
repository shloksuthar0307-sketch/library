import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from organizations.models import Organization, Branch
from books.models import Category, Author, Publisher, Book, BookCopy

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with initial data for development'

    def handle(self, *args, **options):
        self.stdout.write("Seeding database...")

        # 1. Create Superuser
        if not User.objects.filter(username="shlok25@gmail.com").exists():
            su = User.objects.create_superuser("shlok25@gmail.com", "shlok25@gmail.com", "Shlok@123")
            su.first_name = "Super"
            su.last_name = "Admin"
            su.save()
            self.stdout.write("Created Superuser")

        # 2. Create Organization
        org, _ = Organization.objects.get_or_create(
            name="University of Phoenix Library",
            defaults={
                "organization_type": Organization.OrganizationType.UNIVERSITY,
                "email": "library@phoenix.edu",
                "is_active": True,
            }
        )
        self.stdout.write(f"Organization: {org.name}")

        # 3. Create Branch
        branch, _ = Branch.objects.get_or_create(
            organization=org,
            name="Main Campus Library",
            defaults={
                "code": "MAIN",
                "is_main": True,
                "is_active": True,
            }
        )
        self.stdout.write(f"Branch: {branch.name}")

        # 4. Create Users (Staff & Members)
        staff, _ = User.objects.get_or_create(
            username="staff_user",
            defaults={
                "email": "staff@example.com",
                "first_name": "Librarian",
                "last_name": "Jane",
                "role": User.Role.STAFF,
                "organization": org,
                "branch": branch,
                "is_staff": True,
            }
        )
        if _: staff.set_password("password123"); staff.save()

        member1, _ = User.objects.get_or_create(
            username="marcus_chen",
            defaults={
                "email": "m.chen@university.edu",
                "first_name": "Marcus",
                "last_name": "Chen",
                "role": User.Role.MEMBER,
                "organization": org,
                "branch": branch,
            }
        )
        if _: member1.set_password("password123"); member1.save()

        member2, _ = User.objects.get_or_create(
            username="elena_rostova",
            defaults={
                "email": "elena@university.edu",
                "first_name": "Elena",
                "last_name": "Rostova",
                "role": User.Role.MEMBER,
                "organization": org,
                "branch": branch,
            }
        )
        if _: member2.set_password("password123"); member2.save()

        self.stdout.write("Created Users")

        # 5. Create Categories
        cs_cat, _ = Category.objects.get_or_create(organization=org, name="Computer Science")
        math_cat, _ = Category.objects.get_or_create(organization=org, name="Mathematics")

        # 6. Create Authors
        knuth, _ = Author.objects.get_or_create(organization=org, name="Donald Knuth")
        kleppmann, _ = Author.objects.get_or_create(organization=org, name="Martin Kleppmann")
        cormen, _ = Author.objects.get_or_create(organization=org, name="Thomas H. Cormen")

        # 7. Create Publishers
        aw, _ = Publisher.objects.get_or_create(organization=org, name="Addison-Wesley")
        oreilly, _ = Publisher.objects.get_or_create(organization=org, name="O'Reilly Media")
        mit, _ = Publisher.objects.get_or_create(organization=org, name="MIT Press")

        # 8. Create Books & Copies
        books_data = [
            {
                "title": "The Art of Computer Programming",
                "isbn": "9780201896831",
                "author": knuth,
                "category": cs_cat,
                "publisher": aw,
                "copies": 3,
            },
            {
                "title": "Designing Data-Intensive Applications",
                "isbn": "9781449373320",
                "author": kleppmann,
                "category": cs_cat,
                "publisher": oreilly,
                "copies": 5,
            },
            {
                "title": "Introduction to Algorithms",
                "isbn": "9780262033848",
                "author": cormen,
                "category": cs_cat,
                "publisher": mit,
                "copies": 2,
            }
        ]

        for bdata in books_data:
            book, created = Book.objects.get_or_create(
                organization=org,
                isbn=bdata["isbn"],
                defaults={
                    "title": bdata["title"],
                    "author": bdata["author"],
                    "category": bdata["category"],
                    "publisher": bdata["publisher"],
                    "status": "AVAILABLE",
                }
            )
            
            if created:
                for i in range(bdata["copies"]):
                    BookCopy.objects.create(
                        organization=org,
                        branch=branch,
                        book=book,
                        barcode=f"BC-{book.isbn}-{i+1}",
                        status=BookCopy.Status.AVAILABLE,
                        condition=BookCopy.Condition.GOOD
                    )
                book.sync_copy_counts()
                self.stdout.write(f"Created Book: {book.title} ({bdata['copies']} copies)")

        self.stdout.write(self.style.SUCCESS("Database seeded successfully!"))
