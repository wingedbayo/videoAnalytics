from django import forms
# from django.forms import ModelForm

class ChatForm(forms.Form):
    file = forms.FileField()