from django import forms

from .models import Author, Book, Category, Publisher


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        exclude = ("organization",)
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["author"].queryset = Author.objects.for_organization(organization)
            self.fields["category"].queryset = Category.objects.for_organization(organization)
            self.fields["publisher"].queryset = Publisher.objects.for_organization(organization)
