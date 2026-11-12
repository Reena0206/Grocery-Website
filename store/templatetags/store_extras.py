from django import template

from store.currency import format_inr

register = template.Library()


@register.filter
def inr(value):
    """{{ product.price|inr }} -> ₹1,199"""
    return format_inr(value)
