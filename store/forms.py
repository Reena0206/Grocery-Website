from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Order


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["full_name", "email", "phone", "city", "address", "note", "payment_method"]
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "John Doe", "autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"placeholder": "you@example.com", "autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"placeholder": "+1 234 567 890", "autocomplete": "tel"}),
            "address": forms.TextInput(attrs={"placeholder": "House no., street, area", "autocomplete": "street-address"}),
            "city": forms.TextInput(attrs={"placeholder": "City", "autocomplete": "address-level2"}),
            "note": forms.TextInput(attrs={"placeholder": "e.g. Leave at the door (optional)"}),
            "payment_method": forms.RadioSelect,
        }
        labels = {"note": "Delivery note", "full_name": "Full name"}

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        digits = [c for c in phone if c.isdigit()]
        if len(digits) < 7:
            raise forms.ValidationError("Please enter a valid phone number.")
        return phone


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=60, label="Full name",
                                 widget=forms.TextInput(attrs={"placeholder": "Your name", "autocomplete": "name"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": "you@example.com", "autocomplete": "email"}))

    class Meta:
        model = User
        fields = ["first_name", "username", "email"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email
