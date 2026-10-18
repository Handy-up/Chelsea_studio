from django import forms
from django.core.exceptions import ValidationError

class BookingCustomerForm(forms.Form):
    first_name = forms.CharField(
        max_length=80,
        label="Prénom",
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Votre prénom', 'required': 'required'})
    )
    last_name = forms.CharField(
        max_length=80,
        label="Nom",
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Votre nom', 'required': 'required'})
    )
    email = forms.EmailField(
        label="Adresse courriel",
        widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'votre.email@exemple.com', 'required': 'required'})
    )
    phone = forms.CharField(
        max_length=30,
        label="Téléphone",
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '06 12 34 56 78', 'required': 'required'})
    )
    client_note = forms.CharField(
        required=False,
        label="Note ou précisions pour Chelsea",
        widget=forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Informations utiles sur vos cheveux ou votre demande...'})
    )
    accept_policy = forms.BooleanField(
        required=True,
        error_messages={'required': "Vous devez accepter les conditions et la politique d'annulation pour réserver."},
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'})
    )
    # Honeypot field anti-spam
    website_hp = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'tabindex': '-1', 'autocomplete': 'off'})
    )

    def clean_website_hp(self):
        hp = self.cleaned_data.get('website_hp')
        if hp:
            raise ValidationError("Spam détecté.")
        return hp

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.strip().lower()
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            phone = phone.strip()
            if len(phone) < 8:
                raise ValidationError("Le numéro de téléphone semble trop court.")
        return phone
