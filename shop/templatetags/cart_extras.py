from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def cart_count(context):
    request = context['request']
    cart = request.session.get('cart', {})
    return sum(cart.values())
