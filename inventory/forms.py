from django import forms
from .models import Product, Category, Supplier, StockRequest

class ProductForm(forms.ModelForm):
    """Form for adding/editing products"""
    class Meta:
        model = Product
        fields = ['name', 'sku', 'description', 'category', 'supplier', 
                  'price', 'quantity', 'threshold_quantity']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'threshold_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }
    
    def clean_sku(self):
        sku = self.cleaned_data.get('sku')
        
        # Check if SKU exists when creating new product
        if not self.instance.pk:
            if Product.objects.filter(sku=sku).exists():
                raise forms.ValidationError('A product with this SKU already exists.')
        # Check if SKU exists when updating, excluding current instance
        else:
            if Product.objects.filter(sku=sku).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError('A product with this SKU already exists.')
        
        return sku

class CategoryForm(forms.ModelForm):
    """Form for adding/editing categories"""
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        
        # Check if category name exists when creating new category
        if not self.instance.pk:
            if Category.objects.filter(name__iexact=name).exists():
                raise forms.ValidationError('A category with this name already exists.')
        # Check if category name exists when updating, excluding current instance
        else:
            if Category.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError('A category with this name already exists.')
        
        return name

class SupplierForm(forms.ModelForm):
    """Form for adding/editing suppliers"""
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'email', 'phone', 'address']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class StockRequestForm(forms.ModelForm):
    """Form for requesting stock"""
    class Meta:
        model = StockRequest
        fields = ['product', 'quantity', 'reason']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 
                                           'placeholder': 'Explain why you need this stock'}),
        }
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        
        if quantity < 1:
            raise forms.ValidationError('Quantity must be at least 1.')
        
        return quantity

class InventoryFilterForm(forms.Form):
    """Form for filtering inventory reports"""
    EXPORT_CHOICES = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
    ]
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    low_stock_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    export_format = forms.ChoiceField(
        choices=EXPORT_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
