from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=100, help_text='First Name')
    last_name = forms.CharField(max_length=100, help_text='Last Name')
    email = forms.EmailField(max_length=150, help_text='Email')
    phon_number = forms.CharField(max_length=11, help_text='Mobile')


    class Meta:
        model = User
        fields = ('username', 'phon_number', 'first_name', 'last_name', 'email', 'password1', 'password2', )


class SmsActivationForm(forms.Form):
    sms_code = forms.CharField(max_length=6, help_text='only and if only 6 charachter')
