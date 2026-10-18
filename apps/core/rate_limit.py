from django.core.cache import cache


def get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def is_rate_limited(request, scope, limit, window_seconds=3600):
    if limit <= 0:
        return False

    key = f"rate:{scope}:{get_client_ip(request)}"
    added = cache.add(key, 0, timeout=window_seconds)
    if added:
        count = 0
    else:
        count = cache.get(key, 0)

    count += 1
    cache.set(key, count, timeout=window_seconds)
    return count > limit
