from django import forms


class UploadBookForm(forms.Form):
    file = forms.FileField()
