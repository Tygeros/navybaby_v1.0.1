from django import forms
from .models import FinanceCategory, FinanceTransaction
from customers.models import Customer


class FinanceCategoryForm(forms.ModelForm):
    class Meta:
        model = FinanceCategory
        fields = ["name", "type", "description"]
        widgets = {
            "name": forms.TextInput(attrs={
                'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200'
            }),
            "type": forms.Select(attrs={
                'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200'
            }),
            "description": forms.Textarea(attrs={
                'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200',
                'rows': 3,
            }),
        }


class FinanceTransactionForm(forms.ModelForm):
    class Meta:
        model = FinanceTransaction
        fields = ["category", "customer", "amount", "note"]
        widgets = {
            "category": forms.Select(attrs={
                'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200'
            }),
            "customer": forms.Select(attrs={
                'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200',
                'data-control': 'select2',
                'data-placeholder': 'Chọn khách hàng',
            }),
            "amount": forms.NumberInput(attrs={
                'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200',
                'min': '0',
                'step': '0.01'
            }),
            "note": forms.Textarea(attrs={
                'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200',
                'rows': 3,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active categories; type will be filtered in the view
        self.fields['category'].required = True
        self.fields['amount'].required = True
        # Customer is optional
        try:
            self.fields['customer'].queryset = Customer.objects.all().order_by('name')
            self.fields['customer'].label_from_instance = lambda obj: f"{obj.name} — [{obj.code}] — {obj.phone_number or ''}"
        except Exception:
            pass
