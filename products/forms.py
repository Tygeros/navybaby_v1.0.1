from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    code = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700',
            'placeholder': 'Mã SP (để trống sẽ tự tạo)'
        })
    )
    colors = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700',
            'placeholder': 'Ví dụ: Đỏ, Xanh, Vàng',
        }),
        help_text="Nhập các màu sắc, ngăn cách bởi dấu phẩy"
    )
    
    sizes = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700',
            'placeholder': 'Ví dụ: S, M, L, XL',
        }),
        help_text="Nhập các kích thước, ngăn cách bởi dấu phẩy"
    )
    
    class Meta:
        model = Product
        fields = [
            'code', 'name', 'category', 'supplier', 'description', 
            'image', 'price', 'private_order', 'note', 'colors', 'sizes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700',
            }),
            'category': forms.Select(attrs={
                'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700',
            }),
            'supplier': forms.Select(attrs={
                'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700',
                'rows': 3,
            }),
            'image': forms.FileInput(attrs={
                'class': 'hidden',
                'id': 'image-upload',
                'onchange': 'previewImage(this, \'image-preview\')',
            }),
            'price': forms.NumberInput(attrs={
                'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700',
                'min': 0,
            }),
            'note': forms.Textarea(attrs={
                'class': 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700',
                'rows': 2,
            }),
            'private_order': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-700 rounded',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial values for colors and sizes if editing
        if self.instance.pk:
            self.fields['colors'].initial = ', '.join([color.name for color in self.instance.colors.all()])
            self.fields['sizes'].initial = ', '.join([size.name for size in self.instance.sizes.all()])
    
    def clean_colors(self):
        colors = self.cleaned_data.get('colors', '')
        # Split by comma and remove any empty strings and strip whitespace
        colors_list = [c.strip() for c in colors.split(',') if c.strip()]
        return colors_list
    
    def clean_sizes(self):
        sizes = self.cleaned_data.get('sizes', '')
        # Split by comma and remove any empty strings and strip whitespace
        sizes_list = [s.strip() for s in sizes.split(',') if s.strip()]
        return sizes_list
    
    def save(self, commit=True):
        # Save the product first
        product = super().save(commit=commit)
        
        # Handle colors and sizes
        if commit:
            # Update colors
            current_colors = set(product.colors.values_list('name', flat=True))
            new_colors = set(self.cleaned_data['colors'])
            
            # Remove old colors not in new colors
            for color in current_colors - new_colors:
                product.colors.filter(name=color).delete()
            
            # Add new colors
            for color in new_colors - current_colors:
                product.colors.create(name=color)
            
            # Update sizes
            current_sizes = set(product.sizes.values_list('name', flat=True))
            new_sizes = set(self.cleaned_data['sizes'])
            
            # Remove old sizes not in new sizes
            for size in current_sizes - new_sizes:
                product.sizes.filter(name=size).delete()
            
            # Add new sizes
            for size in new_sizes - current_sizes:
                product.sizes.create(name=size)
        
        return product
