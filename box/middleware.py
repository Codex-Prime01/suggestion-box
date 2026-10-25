"""
Content-Security-Policy: tells the browser where scripts, styles, fonts and
images may come from. Everything is self-hosted now, so the policy is tight:
only this site. If someone ever sneaks bad HTML into a page, the browser
refuses to run it. Important because the oga's unlocked key lives in the tab.
"""

CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'wasm-unsafe-eval'",  # wasm = libsodium. No 'unsafe-eval', no inline scripts.
    "style-src 'self' 'unsafe-inline'",      # inline style="" attributes for the background picture
    "font-src 'self'",
    "img-src 'self' blob: data: https:",     # https: = oga's background picture link
    "media-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "manifest-src 'self'",
])


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("Content-Security-Policy", CSP)
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        return response
