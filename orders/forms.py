from django import forms
from django.forms import ModelForm, inlineformset_factory
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from customers.models import Customer
from products.models import Product, Color, Size
from .models import Order

class OrderForm(forms.ModelForm):
    code = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700',
            'placeholder': 'Mã ĐH (để trống sẽ tự tạo)'
        })
    )
    class Meta:
        model = Order
        fields = ['code', 'customer', 'product', 'color', 'size', 'amount', 'sale_price', 'discount', 'status', 'note']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set required fields
        self.fields['customer'].required = True
        self.fields['product'].required = True
        self.fields['amount'].required = True
        
        # Enrich option labels for search/display
        try:
            self.fields['customer'].queryset = Customer.objects.all().order_by('name')
            self.fields['customer'].label_from_instance = lambda obj: f"{obj.name} — [{obj.code}] — {obj.phone_number or ''}"
        except Exception:
            pass
        try:
            self.fields['product'].queryset = Product.objects.select_related('supplier').order_by('name')
            self.fields['product'].label_from_instance = lambda obj: f"{obj.name} — [{obj.code}] — {obj.supplier.name if obj.supplier else ''}"
        except Exception:
            pass

        # Set widget attributes
        self.fields['customer'].widget.attrs.update({
            'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700',
            'data-control': 'select2',
            'data-placeholder': 'Chọn khách hàng',
        })
        
        self.fields['product'].widget.attrs.update({
            'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700',
            'data-control': 'select2',
            'data-placeholder': 'Chọn sản phẩm',
        })
        
        self.fields['color'].widget.attrs.update({
            'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700',
            'data-control': 'select2',
            'data-placeholder': 'Chọn màu sắc',
        })
        
        self.fields['size'].widget.attrs.update({
            'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700',
            'data-control': 'select2',
            'data-placeholder': 'Chọn kích thước',
        })
        
        self.fields['amount'].widget.attrs.update({
            'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700',
            'min': 1,
            'value': 1,
        })

        # Sale price editable; default will be set client-side on product change or server-side in model.save
        if 'sale_price' in self.fields:
            self.fields['sale_price'].required = False
            self.fields['sale_price'].widget = forms.NumberInput(attrs={
                'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700',
                'min': 0,
                'step': 1,
            })
        
        self.fields['discount'].widget.attrs.update({
            'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700',
            'value': 0,
        })
        
        self.fields['status'].widget.attrs.update({
            'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700',
        })
        # Status field may be hidden in the template; keep optional.
        # For updates, preserve current instance status; for creates, default to 'created'.
        self.fields['status'].required = False
        if self.instance.pk:
            self.fields['status'].initial = self.instance.status
        elif not self.initial.get('status'):
            self.fields['status'].initial = 'created'
        
        # Filter color and size choices based on selected product
        if 'product' in self.data:
            try:
                product_id = int(self.data.get('product'))
                product = Product.objects.get(id=product_id)
                self.fields['color'].queryset = product.colors.all().order_by('name')
                self.fields['size'].queryset = product.sizes.all().order_by('name')
            except (ValueError, Product.DoesNotExist):
                self.fields['color'].queryset = Color.objects.none()
                self.fields['size'].queryset = Size.objects.none()
        elif self.instance.pk:
            self.fields['color'].queryset = self.instance.product.colors.all().order_by('name')
            self.fields['size'].queryset = self.instance.product.sizes.all().order_by('name')
        elif self.initial.get('product'):
            try:
                prod_id = int(self.initial.get('product'))
                product = Product.objects.get(id=prod_id)
                self.fields['color'].queryset = product.colors.all().order_by('name')
                self.fields['size'].queryset = product.sizes.all().order_by('name')
            except (ValueError, Product.DoesNotExist):
                self.fields['color'].queryset = Color.objects.none()
                self.fields['size'].queryset = Size.objects.none()
        else:
            self.fields['color'].queryset = Color.objects.none()
            self.fields['size'].queryset = Size.objects.none()
        # Style optional note field
        if 'note' in self.fields:
            self.fields['note'].required = False
            # Use Textarea and dark theme classes
            self.fields['note'].widget = forms.Textarea(attrs={
                'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700',
                'rows': 3,
                'placeholder': 'Ghi chú (tùy chọn)'
            })
    
    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        sale_price = cleaned_data.get('sale_price')
        color = cleaned_data.get('color')
        size = cleaned_data.get('size')
        amount = cleaned_data.get('amount')
        status = cleaned_data.get('status')
        
        # Validate that color is available for the selected product
        if product and color and color not in product.colors.all():
            self.add_error('color', 'Màu sắc không khả dụng cho sản phẩm đã chọn')
            
        # Validate that size is available for the selected product
        if product and size and size not in product.sizes.all():
            self.add_error('size', 'Kích thước không khả dụng cho sản phẩm đã chọn')
            
        # Validate that amount is positive
        if amount and amount <= 0:
            self.add_error('amount', 'Số lượng phải lớn hơn 0')
        # Validate that sale_price is non-negative (allow zero for promotions if needed)
        if sale_price is not None and sale_price < 0:
            self.add_error('sale_price', 'Giá bán không được âm')
        # Default status if missing (since the field may be hidden in UI)
        if not status:
            if self.instance.pk:
                cleaned_data['status'] = self.instance.status
            else:
                cleaned_data['status'] = 'created'
            
        return cleaned_data