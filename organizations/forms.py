from django import forms
from django.contrib.auth.password_validation import validate_password

from accounts.models import User
from organizations.models import Branch, Organization


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = [
            "name",
            "organization_type",
            "email",
            "phone",
            "website",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "timezone",
            "currency",
            "logo",
            "is_active",
            "max_members",
            "max_books",
            "max_staff",
            "max_branches",
        ]


class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        exclude = ("organization",)

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        if organization:
            self.fields["manager"].queryset = User.objects.filter(
                organization=organization
            ).exclude(role=User.Role.MEMBER)

    def clean_code(self):
        code = (self.cleaned_data.get("code") or "").strip().upper()
        org = self.organization or getattr(self.instance, "organization", None)
        qs = Branch.objects.filter(organization=org, code=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Branch code must be unique within the organization.")
        return code


class OnboardingOrganizationForm(forms.Form):
    name = forms.CharField(max_length=255)
    organization_type = forms.ChoiceField(choices=Organization.OrganizationType.choices)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20, required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)
    city = forms.CharField(max_length=100, required=False)
    state = forms.CharField(max_length=100, required=False)
    country = forms.CharField(max_length=100, required=False)


class OnboardingBranchForm(forms.Form):
    branch_name = forms.CharField(max_length=255, initial="Main Branch")
    branch_code = forms.CharField(max_length=50, initial="MAIN")
    branch_address = forms.CharField(widget=forms.Textarea, required=False)


class OnboardingAdminForm(forms.Form):
    admin_first_name = forms.CharField(max_length=150)
    admin_last_name = forms.CharField(max_length=150, required=False)
    admin_email = forms.EmailField()
    admin_username = forms.CharField(max_length=150)
    admin_password = forms.CharField(widget=forms.PasswordInput)

    def clean_admin_username(self):
        username = self.cleaned_data["admin_username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists.")
        return username

    def clean_admin_email(self):
        email = self.cleaned_data["admin_email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already registered.")
        return email

    def clean_admin_password(self):
        password = self.cleaned_data["admin_password"]
        validate_password(password)
        return password


class OnboardingRulesForm(forms.Form):
    borrow_limit = forms.IntegerField(min_value=1, initial=3)
    borrow_duration = forms.IntegerField(min_value=1, initial=14)
    fine_per_day = forms.DecimalField(min_value=0, initial=5, decimal_places=2)
    currency = forms.CharField(max_length=8, initial="INR")


class OnboardingBrandingForm(forms.Form):
    logo = forms.ImageField(required=False)
    primary_color = forms.CharField(max_length=7, initial="#111111")
    secondary_color = forms.CharField(max_length=7, initial="#10B981")
