import django_filters
from django import forms
from .models import Product, Category, Supplier

class ProductFilter(django_filters.FilterSet):
    """Filter for products list"""
    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by name'})
    )
    
    sku = django_filters.CharFilter(
        field_name='sku',
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by SKU'})
    )
    
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    supplier = django_filters.ModelChoiceFilter(
        queryset=Supplier.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    min_price = django_filters.NumberFilter(
        field_name='price',
        lookup_expr='gte',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Min price'})
    )
    
    max_price = django_filters.NumberFilter(
        field_name='price',
        lookup_expr='lte',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Max price'})
    )
    
    low_stock = django_filters.BooleanFilter(
        method='filter_low_stock',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def filter_low_stock(self, queryset, name, value):
        """Filter for products with quantity below threshold"""
        if value:
            return queryset.filter(quantity__lt=models.F('threshold_quantity'))
        return queryset
    
    class Meta:
        model = Product
        fields = ['name', 'sku', 'category', 'supplier', 'low_stock']
