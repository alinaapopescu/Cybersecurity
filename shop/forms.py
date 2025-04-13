from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

from .models import Order, Comment
from .utils import complex_encode


class CheckoutForm(forms.ModelForm):
    postal_code = forms.CharField(
        max_length=10,
        validators=[RegexValidator(r'^\d{4,10}$', 'Introduceți un cod poștal valid.')]
    )
    class Meta:
        model = Order
        fields = ['customer_name', 'email', 'address', 'city', 'postal_code', 'shipping_method']
        widgets = {
            'shipping_method': forms.RadioSelect
        }


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        })
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super(UserRegistrationForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Username'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Repeat Password'
        })


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Lasă un comentariu...'})
        }

    def clean_text(self):
        text = self.cleaned_data.get("text", "")
        encoded_text = complex_encode(text, shift=5)
        return encoded_text

