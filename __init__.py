from .models import wizard

def uninstall_hook(cr, registry):
    from .models import uninstall_hook as hook
    return hook(cr, registry)